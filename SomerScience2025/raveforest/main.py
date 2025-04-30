import argparse
import json
import socket
import threading
import queue
import time

from pillar_hw_interface import Pillar
from mapping_interface import RotationMapper, EventRotationMapper, LightSoundMapper, generate_mapping_interface
from sound_manager import SoundManager

import requests

import csv

class APISender(threading.Thread):
    def __init__(self, endpoint, data_queue, interval=0.2):
        """
        A thread that sends data packets to an API at a specified interval.

        :param endpoint: The API endpoint URL.
        :param data_queue: A queue for receiving data from the main loop.
        :param interval: Time between requests in seconds (5Hz = 0.2s).
        """
        super().__init__()
        self.endpoint = endpoint
        self.data_queue = data_queue
        self.interval = interval
        self.running = True

    def run(self):
        while self.running:
            try:
                # Get the latest data, or wait for it (timeout to prevent hanging on stop)
                data = self.data_queue.get(timeout=1)  
                response = requests.post(self.endpoint, json=data, timeout=2)
                # print(f"Sent data: {data}, Response: {response.status_code}")
            except queue.Empty:
                # If no data is available, continue waiting
                pass
            except requests.RequestException as e:
                print(f"Request failed: {e}")

            time.sleep(self.interval)

    def stop(self):
        self.running = False

class Controller():

    def __init__(self, hostname, config):
        self.config = config
        self.num_pillars = len(config["pillars"])        
        self.pillar_config = config["pillars"][hostname]
        self.pillar_manager = Pillar(**self.pillar_config)
        self.mapping_interface = generate_mapping_interface(config, self.pillar_config)
        self.sound_manager = SoundManager(hostname)
        self.loop_idx = 0
        self.running = True
        
        # Track the last time we requested LED status
        self.last_led_request_time = 0
        self.led_request_interval = 2.0  # Request LED status every 2 seconds
        
        # Track the last time we processed LED status regardless of changes
        self.last_led_process_time = 0
        self.led_process_interval = 1.0  # Process LED status every 1 second
        
        # Store previous LED status to detect changes
        self.previous_led_status = [(0, 0, 0) for _ in range(self.pillar_manager.num_tubes)]

        self.data_queue = queue.Queue()  # Thread-safe queue for data exchange
        
        print(f"[DEBUG] Controller initialized for hostname: {hostname}")
        print(f"[DEBUG] Using mapping: {self.pillar_config['map']}")


    def start(self, frequency):
        """Starts the main control loop

        Args:
            frequency (_type_): _description_
        """
        index = 0

        while self.running:
            self.loop()

    def stop(self):
        self.running = False

    def loop(self):
        current_time = time.time()
        
        # Read from serial to update touch status and LED status
        self.pillar_manager.read_from_serial()

        current_btn_press = self.pillar_manager.get_all_touch_status()
        
        # Periodically request LED status from the Teensy
        if current_time - self.last_led_request_time >= self.led_request_interval:
            print("[DEBUG] Requesting LED status from Teensy")
            self.pillar_manager.request_led_status()
            self.last_led_request_time = current_time
        
        # Get current LED status from the Teensy
        current_led_status = self.pillar_manager.get_all_light_status()
        
        # Detect if LED status has changed
        led_status_changed = (current_led_status != self.previous_led_status)
        
        # Either process when LED status changes OR at regular intervals
        if led_status_changed or (current_time - self.last_led_process_time >= self.led_process_interval):
            if led_status_changed:
                print("[DEBUG] LED status changed:", current_led_status)
            else:
                print("[DEBUG] Regular LED status processing:", current_led_status)
            
            # Use LightSoundMapper to convert light values to sound
            sound_state = self.mapping_interface.update_from_light_status(current_led_status)
            
            # Update the previous LED status and processing time
            self.previous_led_status = current_led_status
            self.last_led_process_time = current_time
            
            # Update sound parameters based on the LED status change
            for param_name, value in sound_state.items():
                self.sound_manager.update_pillar_setting(param_name, value)
            
            # Process sound changes
            self.sound_manager.tick(time_delta=1/30.0)
            
            # Package data for logging
            data = {
                "btn_press": current_btn_press,
                "sound_state": sound_state.to_json(),
                "light_state": list([(h, b) for h, b, _ in current_led_status])
            }
            self.data_queue.put(data)
        else:
            # Still process sound system regularly even if no changes
            self.sound_manager.tick(time_delta=1/30.0)
            
            if self.loop_idx % 30 == 0:  # Only print occasionally to avoid log spam
                print(f"Regular tick with no LED changes (loop {self.loop_idx})")

        self.loop_idx += 1

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="A script to parse host, port, and config file path.")
    parser.add_argument("--config", default="config/config.json", help="Path to the JSON config file.")
    parser.add_argument("--serial_port", default=None, help="Overrides the serial in the configuration")
    parser.add_argument("--frequency", default=5, type=int, help="Frequency of the controller loop")
    parser.add_argument("--hostname", default=None, type=str, help="The hostname if different from the base computer")

    args = parser.parse_args()
    print(args)

    # Get Hostname
    hostname = args.hostname if args.hostname is not None else socket.gethostname()
    print("HOSTNAME is ", hostname)
        

    # Read the JSON config file
    with open(args.config, 'r') as config_file:
        config = json.load(config_file)

    if hostname not in config["pillars"]:
        raise RuntimeError(f"This hostname {hostname} not present in configuration")

    if args.serial_port is not None:
        print("Reconfigured serial port to: ", args.serial_port)
        config["pillars"][hostname]["port"] = args.serial_port

    # Create a Controller instance and pass the parsed values
    print("Intiialise and run Controller")
    controller = Controller(hostname, config)
    controller.start(args.frequency)
    # asyncio.get_event_loop().run_until_complete(controller.run(args.frequency))
    # asyncio.get_event_loop().run_forever()
