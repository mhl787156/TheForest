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
        self.led_request_interval = 5.0  # Increase to 5 seconds - less frequent requests
        
        # Track the last time we processed LED status regardless of changes
        self.last_led_process_time = 0
        self.led_process_interval = 1.0  # Process LED status every 1 second
        
        # Store previous LED status to detect changes
        self.previous_led_status = [(0, 0, 0) for _ in range(self.pillar_manager.num_tubes)]

        self.data_queue = queue.Queue()  # Thread-safe queue for data exchange
            
        # Add rate limiting for loop processing
        self.min_loop_interval = 0.1  # Minimum time between loop iterations (10Hz max)
        self.last_loop_time = 0
            
        print(f"Controller initialized for hostname: {hostname}")
        print(f"Using mapping: {self.pillar_config['map']}")


    def start(self, frequency):
        """Starts the main control loop

        Args:
            frequency (_type_): _description_
        """
        print(f"Starting controller loop with target frequency: {frequency} Hz")
        self.running = True
        
        try:
            while self.running:
                # Add rate limiting
                current_time = time.time()
                elapsed = current_time - self.last_loop_time
                
                if elapsed < self.min_loop_interval:
                    # Sleep to maintain the desired loop rate
                    time.sleep(self.min_loop_interval - elapsed)
                
                self.last_loop_time = time.time()
                self.loop()
        except KeyboardInterrupt:
            print("Keyboard interrupt detected, stopping controller")
            self.stop()
        except Exception as e:
            print(f"[ERROR] Exception in controller main loop: {e}")
            self.stop()
            raise

    def stop(self):
        self.running = False
        # Stop API sender if it exists
        if hasattr(self, 'api_sender'):
            self.api_sender.stop()
            print("API sender stopped")

    def loop(self):
        current_time = time.time()
        
        try:
            # Read from serial to update touch status and LED status
            self.pillar_manager.read_from_serial()
    
            # Get current touch status
            current_touch_status = self.pillar_manager.get_all_touch_status()
            
            # Get previous touch status (or initialize if first run)
            previous_touch_status = getattr(self, 'previous_touch_status', [False] * self.pillar_manager.num_tubes)
            
            # Detect newly touched tubes (0→1 transitions)
            newly_touched_tubes = []
            for i, (prev, curr) in enumerate(zip(previous_touch_status, current_touch_status)):
                if not prev and curr:  # Rising edge detected
                    newly_touched_tubes.append(i)
            
            # Store current touch status for next iteration
            self.previous_touch_status = current_touch_status
            
            # For LightSoundMapper, directly trigger notes based on LED colors when tubes are touched
            if isinstance(self.mapping_interface, LightSoundMapper) and newly_touched_tubes:
                # Get current LED status
                current_led_status = self.pillar_manager.get_all_light_status()
                
                # Prepare reaction notes based on LED colors of touched tubes
                reaction_notes = []
                for tube_id in newly_touched_tubes:
                    if tube_id < len(current_led_status):
                        # Get the hue value from the LED status
                        hue, brightness, _ = current_led_status[tube_id]
                        
                        # Skip if tube is not lit (brightness too low)
                        if brightness < 20:
                            continue
                        
                        # Convert hue to note using LightSoundMapper's conversion
                        semitone = self.mapping_interface.hue_to_semitone(hue)
                        octave = self.mapping_interface.octave
                        note_to_play = semitone + (octave * 12)
                        
                        # Add the note to reaction notes
                        reaction_notes.append(note_to_play)
                        print(f"[DEBUG] Touch-triggered note {note_to_play} from tube {tube_id} (hue={hue})")
                
                # Play the reaction notes
                if reaction_notes:
                    self.sound_manager.update_pillar_setting("reaction_notes", reaction_notes)
            
            # Periodically request LED status from the Teensy (less frequently)
            if current_time - self.last_led_request_time >= self.led_request_interval:
                print(f"Requesting LED status from Teensy (interval: {self.led_request_interval}s)")
                self.pillar_manager.request_led_status()
                self.last_led_request_time = current_time
            
            # Get current LED status from the Teensy
            current_led_status = self.pillar_manager.get_all_light_status()
            
            # Detect if LED status has changed
            led_status_changed = False
            for i, (curr, prev) in enumerate(zip(current_led_status, self.previous_led_status)):
                if curr != prev:
                    led_status_changed = True
                    print(f"LED status changed for tube {i}: {prev} -> {curr}")
                    break
            
            # Only log every 30 iterations unless there's a change
            should_log = led_status_changed or (self.loop_idx % 30 == 0)
            
            # Either process when LED status changes OR at regular intervals
            if led_status_changed or (current_time - self.last_led_process_time >= self.led_process_interval):
                if should_log:
                    if led_status_changed:
                        print("Processing LED status - status changed")
                    else:
                        print("Processing LED status - regular interval")
                
                try:
                    # Generate the sound and light state based on button presses
                    sound_state, light_state = self.mapping_interface.update_pillar(current_touch_status)
                    
                    # Only update light state if we have a mapper that doesn't rely on LEDs for sound
                    # Otherwise we're in a feedback loop
                    if not isinstance(self.mapping_interface, LightSoundMapper):
                        # Send light changes to the Teensy
                        self.pillar_manager.send_all_light_change(light_state)
                        
                    # Add extra debug for sound state
                    if should_log:
                        print(f"Sound state: {sound_state}")
                
                    # Update sound parameters
                    for param_name, value in sound_state.items():
                        self.sound_manager.update_pillar_setting(param_name, value)
                    
                    # Process sound changes
                    self.sound_manager.tick(time_delta=1/30.0)
                    
                    # Update the previous LED status
                    self.previous_led_status = current_led_status
                    self.last_led_process_time = current_time
                    
                    # Package data for logging
                    try:
                        data = {
                            "btn_press": current_touch_status,
                            "sound_state": sound_state.to_json(),
                            "light_state": list([(h, b) for h, b, _ in current_led_status])
                        }
                        self.data_queue.put(data)
                    except Exception as e:
                        print(f"[ERROR] Error packaging data for API: {e}")
                        
                except Exception as e:
                    print(f"[ERROR] Error processing LED status: {e}")
                    # Still try to tick the sound manager
                    self.sound_manager.tick(time_delta=1/30.0)
            else:
                # Still process sound system regularly even if no changes
                self.sound_manager.tick(time_delta=1/30.0)
                
                if should_log:
                    print(f"Regular tick with no LED changes (loop {self.loop_idx})")
    
            self.loop_idx += 1
            
            # Add this at the top of your loop() method
            def debug_serial_communication(self):
                # Log incoming data
                print("\n=== COMMUNICATION DEBUG ===")
                print(f"Touch status: {self.pillar_manager.get_all_touch_status()}")
                print(f"LED status: {self.pillar_manager.get_all_light_status()}")
                print("==========================\n")
            
        except Exception as e:
            print(f"[ERROR] Exception in controller loop: {e}")
            # Keep the loop going despite errors
            time.sleep(0.1)

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