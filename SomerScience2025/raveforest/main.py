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
        self.led_process_interval = 2.0  # Reduce LED processing frequency
        
        # Store previous LED status to detect changes
        self.previous_led_status = [(0, 0, 0) for _ in range(self.pillar_manager.num_tubes)]

        self.data_queue = queue.Queue()  # Thread-safe queue for data exchange
            
        # Add rate limiting for loop processing
        self.min_loop_interval = 0.2  # Reduce update frequency to 5Hz max
        self.last_loop_time = 0
            
        # Avoid excessive debug printing
        self.debug_print = False  # Add a flag to control debug printing

        # Add special debug flags
        self.show_touch_debug = True
        self.show_led_debug = False  # Turn off LED debug since that's working

        # Disable automatic note playing
        self.use_fallback_mode = False  # Disable fallback mode

        print(f"Controller initialized for hostname: {hostname}")
        print(f"Using mapping: {self.pillar_config['map']}")

        # Remove or comment out these test calls:
        # self.sound_manager.play_direct_notes([60, 64, 67])
        # self.test_critical_systems()

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
        # Reduce print statements - only print occasionally
        should_print = (self.loop_idx % 10 == 0)  # Only print every 10th iteration
        
        current_time = time.time()
        touch_notes_sent_this_cycle = False # Flag to track if touch notes were sent
        
        try:
            # Read from serial to update touch status and LED status
            self.pillar_manager.read_from_serial()

            # Get current touch and LED status
            current_touch_status = self.pillar_manager.get_all_touch_status()
            current_led_status = self.pillar_manager.get_all_light_status()
            
            # Only print when needed
            if should_print:
                print(f"Touch status: {current_touch_status}")
            
            # Get previous touch status (or initialize if first run)
            previous_touch_status = getattr(self, 'previous_touch_status', [False] * self.pillar_manager.num_tubes)
            
            # Detect newly touched tubes (0→1 transitions)
            newly_touched_tubes = []
            for i, (prev, curr) in enumerate(zip(previous_touch_status, current_touch_status)):
                if not prev and curr:  # Rising edge detected
                    newly_touched_tubes.append(i)
            
            # Store current touch status for next iteration
            self.previous_touch_status = current_touch_status
            
            # Add clear debug output for touch detection
            for i, (prev, curr) in enumerate(zip(previous_touch_status, current_touch_status)):
                if not prev and curr:  # Rising edge detected
                    print(f"[TOUCH DETECTED] Tube {i} was just touched")
            
            # For LightSoundMapper, trigger notes based on LED colors when tubes are touched
            if isinstance(self.mapping_interface, LightSoundMapper) and newly_touched_tubes:
                reaction_notes = []
                for tube_id in newly_touched_tubes:
                    if tube_id < len(current_led_status):
                        # Get the hue value from the LED status
                        hue, brightness, _ = current_led_status[tube_id]
                        
                        # Skip if tube is not lit (brightness too low)
                        if brightness < 20:
                            continue
                        
                        # Convert hue to note using LightSoundMapper's conversion
                        # Fix for the missing get_note method
                        semitone = self.mapping_interface.hue_to_semitone(hue)
                        octave = self.mapping_interface.octave
                        note_to_play = semitone + (octave * 12)
                        
                        # Add the note to reaction notes
                        reaction_notes.append(note_to_play)
                        print(f"[MELODY] Touch-triggered note {note_to_play} from tube {tube_id} (hue={hue})")
                
                # Play the reaction notes
                if reaction_notes:
                    print(f"[MELODY] Sending notes to sound manager: {reaction_notes}")
                    self.sound_manager.update_pillar_setting("reaction_notes", reaction_notes)
                    touch_notes_sent_this_cycle = True # Set the flag
            
            # Periodically request LED status from the Teensy
            if current_time - self.last_led_request_time >= self.led_request_interval:
                self.pillar_manager.request_led_status()
                print("Requesting LED status")
                self.last_led_request_time = current_time
            
            # Process LED status changes or periodic updates
            led_status_changed = any(curr != prev for curr, prev in zip(current_led_status, self.previous_led_status))
            should_process = led_status_changed or (current_time - self.last_led_process_time >= self.led_process_interval)
            
            if should_process:
                # Generate the sound and light state based on button presses
                sound_state, light_state = self.mapping_interface.update_pillar(current_touch_status)
                
                # Only update light state if we're not using LightSoundMapper
                if not isinstance(self.mapping_interface, LightSoundMapper):
                    self.pillar_manager.send_all_light_change(light_state)
                    
                # Update sound parameters
                for param_name, value in sound_state.items():
                    # If touch notes were already sent this cycle, skip sending reaction_notes again
                    if param_name == "reaction_notes" and touch_notes_sent_this_cycle:
                        continue
                    self.sound_manager.update_pillar_setting(param_name, value)
                
                # Update tracking variables
                self.previous_led_status = current_led_status
                self.last_led_process_time = current_time
            
            # Always process sound system
            self.sound_manager.tick(time_delta=1/30.0)
            
            self.loop_idx += 1
            
        except Exception as e:
            print(f"[ERROR] Exception in controller loop: {e}")
            time.sleep(0.1)

    def play_direct_test_note(self, note_number=60):
        """Test function to directly trigger a note"""
        print(f"[DIRECT TEST] Playing note {note_number}")
        self.sound_manager.update_pillar_setting("reaction_notes", [note_number])

    # Either comment out or remove the entire test_critical_systems method
    '''
    def test_critical_systems(self):
        """Test critical systems to verify functionality"""
        print("\n=== 🧪 CRITICAL SYSTEM TEST ===")
        
        # 1. Test serial connection
        print("\n1. Testing serial connection...")
        if self.pillar_manager.serial_status["connected"]:
            print("✅ Serial connection OK")
        else:
            print("❌ Serial connection FAILED")
        
        # 2. Test touch detection
        print("\n2. Setting up touch detection test...")
        print("👉 Please touch any tube within 10 seconds...")
        
        # 3. Test emergency sound
        print("\n3. Testing emergency sound...")
        # self.sound_manager.play_emergency_note(60)
        
        print("=== 🏁 TEST COMPLETE ===\n")
    '''

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