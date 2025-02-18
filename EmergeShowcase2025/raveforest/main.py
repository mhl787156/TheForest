import argparse
import json
import socket
import threading
import queue
import time

from pillar_hw_interface import Pillar
from mapping_interface import RotationMapper, EventRotationMapper, generate_mapping_interface
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
        self.mapping_interface = generate_mapping_interface(self.pillar_config)
        self.sound_manager = SoundManager(hostname)
        self.loop_idx = 0
        self.running = True

        self.data_queue = queue.Queue()  # Thread-safe queue for data exchange
        sender = APISender(config["tonnetz_server_api_endpoint"], self.data_queue)
        sender.start()

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

        self.pillar_manager.read_from_serial()

        current_btn_press = self.pillar_manager.get_all_touch_status()
        # print("current btn press:", current_btn_press)

        # Generate the lights and notes based on the current btn inputs
        sound_state, light_state = self.mapping_interface.update_pillar(current_btn_press)
        # print("lights:", light_state)
        # print("sounds:", sound_state)

        # print(f"Sending Lights {self.pillar_manager.id}: {light_state}")
        self.pillar_manager.send_all_light_change(light_state)

        # print("Setting params", sound_state)
        for param_name, value in sound_state.items():
            self.sound_manager.update_pillar_setting(param_name, value) 

        self.sound_manager.tick(time_delta=1/30.0)
        
        data = {
            "btn_press": current_btn_press,
            "sound_state": sound_state.to_json(),
            "light_state": list(light_state)
        }
        self.data_queue.put(data)

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
