<<<<<<< HEAD
import argparse
import json
import socket
import threading
import queue
import time
import os
import traceback  # For improved error reporting

from pillar_hw_interface import Pillar
from mapping_interface import RotationMapper, EventRotationMapper, LightSoundMapper, generate_mapping_interface
from sound_manager import SoundManager

class Controller():

    def __init__(self, hostname, config):
        # Add better error handling for critical initialization
        try:
            self.config = config
            self.num_pillars = len(config["pillars"])        
            self.pillar_config = config["pillars"][hostname]
            
            # Verify required config keys
            required_keys = ["id", "port", "num_tubes", "map"]
            for key in required_keys:
                if key not in self.pillar_config:
                    raise ValueError(f"Missing required config key: {key} for hostname {hostname}")
            
            # Initialize pillar manager with error handling
            try:
                self.pillar_manager = Pillar(**self.pillar_config)
                print(f"[INFO] Pillar manager initialized with {self.pillar_config['num_tubes']} tubes")
            except Exception as e:
                print(f"[CRITICAL] Failed to initialize pillar manager: {e}")
                raise
            
            # Initialize mapping interface
            try:
                self.mapping_interface = generate_mapping_interface(config, self.pillar_config)
                print(f"[INFO] Mapping interface initialized: {type(self.mapping_interface).__name__}")
            except Exception as e:
                print(f"[CRITICAL] Failed to initialize mapping interface: {e}")
                raise
            
            # Initialize sound manager
            try:
                self.sound_manager = SoundManager(hostname)
                print(f"[INFO] Sound manager initialized for host: {hostname}")
            except Exception as e:
                print(f"[CRITICAL] Failed to initialize sound manager: {e}")
                raise
                
            self.loop_idx = 0
            self.running = True

            # Track the last time we requested LED status
            self.last_led_request_time = 0
            self.led_request_interval = 1.0  # 1 second between requests
            
            # Track the last time we processed LED status regardless of changes
            self.last_led_process_time = 0
            self.led_process_interval = 1.0  # Process LED status every 200ms
            
            # Store previous LED status to detect changes
            self.previous_led_status = [(0, 0, 0) for _ in range(self.pillar_manager.num_tubes)]
            
            # OPTIMIZATION: More responsive touch with lower loop interval
            self.min_loop_interval = 1.0  # 100Hz max (10ms) for better responsiveness - increased from 50Hz
            self.last_loop_time = 0
            
            # Fast-path for touch events to improve responsiveness
            self.touch_event_time = 0
            self.touch_processing_interval = 0.1  # 1ms - Process touch events at near-realtime (improved from 2ms)
            
            # OPTIMIZATION: Preallocate arrays for touch status
            # FIX: Use num_touch_sensors instead of num_tubes for correct array size
            self.previous_touch_status = [False] * self.pillar_manager.num_touch_sensors
            self.current_touch_status = [False] * self.pillar_manager.num_touch_sensors 
            self.last_touch_time = [0] * self.pillar_manager.num_touch_sensors
            # Remove debounce to respond to all touch events immediately
            self.touch_debounce = 0.05  # No debounce - respond to every touch instantly
            
            # NEW: Latency monitoring
            self.latency_history = []  # Store recent latency measurements
            self.max_latency_history = 100  # Keep last 100 measurements
            self.latency_report_interval = 5.0  # Report every 5 seconds
            self.last_latency_report_time = time.time()
            
            # Avoid excessive debug printing
            self.debug_print = False  # Add a flag to control debug printing

            # Add special debug flags
            self.show_touch_debug = True
            self.show_led_debug = False  # Turn off LED debug since that's working
            self.show_latency_stats = True  # Show detailed latency statistics

            # Disable automatic note playing
            self.use_fallback_mode = False  # Disable fallback mode

            print(f"[INFO] Controller initialized for hostname: {hostname}")
            print(f"[INFO] Using mapping: {self.pillar_config['map']}")
            
            # CRITICAL: Test the sound system at startup to ensure it's working
            self.test_sound_system()
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"[CRITICAL] Failed to initialize controller: {e}")
            print(f"[DEBUG] Traceback: {error_traceback}")
            raise RuntimeError(f"Controller initialization failed: {e}")

    def test_sound_system(self):
        """Test the sound system to ensure it's working correctly"""
        print("\n==== TESTING SOUND SYSTEM ====")
        print("Playing test notes... (this confirms the sound system is working)")
        
        # Try playing a simple C major chord
        test_notes = [60, 64, 67]  # C E G
        
        # Add timeout to prevent hanging if sound system is not responsive
        try:
            # Check if the method exists before calling it
            if hasattr(self.sound_manager, 'play_direct_notes'):
                success = self.sound_manager.play_direct_notes(test_notes)
            else:
                print("❌ Method 'play_direct_notes' not found in sound manager")
                success = False
        except Exception as e:
            print(f"❌ Exception during sound test: {e}")
            success = False
        
        if success:
            print("✓ SOUND TEST PASSED - Notes played successfully")
        else:
            print("❌ SOUND TEST FAILED - Could not play test notes")
            print("Attempting emergency repair...")
            
            # Try to repair the sound system
            try:
                # Force-recreate direct instrument
                if hasattr(self.sound_manager, 'session') and self.sound_manager.session is not None:
                    # Check if session has new_part method
                    if hasattr(self.sound_manager.session, 'new_part'):
                        self.sound_manager._direct_instrument = self.sound_manager.session.new_part("piano")
                        print("Recreated direct instrument")
                        
                        # Try again
                        success = self.sound_manager.play_direct_notes([60])
                        if success:
                            print("✓ REPAIR SUCCESSFUL - Sound system now working")
                        else:
                            print("❌ REPAIR FAILED - Sound system still not working")
                    else:
                        print("❌ REPAIR FAILED - Session does not have new_part method")
                else:
                    print("❌ REPAIR FAILED - No valid session available")
            except Exception as e:
                print(f"❌ REPAIR FAILED - Error: {e}")
                
        print("===============================\n")
        
        # Sleep briefly to let the test notes play
        time.sleep(0.5)

    def start(self, frequency):
        """Starts the main control loop

        Args:
            frequency (int): Target frequency for the control loop in Hz
        """
        print(f"[INFO] Starting controller loop with target frequency: {frequency} Hz")
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
            print("[INFO] Keyboard interrupt detected, stopping controller")
            self.stop()
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"[ERROR] Exception in controller main loop: {e}")
            print(f"[DEBUG] Traceback: {error_traceback}")
            self.stop()
            raise

    def stop(self):
        """Stops the controller safely"""
        print("[INFO] Stopping controller...")
        self.running = False
        
        # Clean up resources if needed
        if hasattr(self, 'sound_manager') and self.sound_manager is not None:
            # Call any cleanup methods if they exist
            if hasattr(self.sound_manager, 'cleanup'):
                try:
                    self.sound_manager.cleanup()
                except Exception as e:
                    print(f"[WARNING] Error during sound manager cleanup: {e}")
        
        print("[INFO] Controller stopped")

    def process_touch_events(self, current_touch_status, current_led_status):
        """
        ULTRA-OPTIMIZED fast-path handler specifically for touch events
        Critical path for minimal latency sound triggering
        
        Args:
            current_touch_status (list): List of boolean touch status for each tube
            current_led_status (list): List of tuples (hue, brightness, effect) for each tube
            
        Returns:
            bool: True if notes were sent, False otherwise
        """
        now = time.time()
        
        # Guard against invalid input
        if not current_touch_status or not current_led_status:
            return False
            
        # Ensure arrays are the right size
        if len(current_touch_status) != len(self.previous_touch_status):
            print(f"[WARNING] Touch status size mismatch: current={len(current_touch_status)}, previous={len(self.previous_touch_status)}")
            # Resize previous_touch_status to match
            self.previous_touch_status = [False] * len(current_touch_status)
            # Also update last_touch_time
            self.last_touch_time = [0] * len(current_touch_status)
        
        # OPTIMIZATION: Initialize tubes lists
        newly_touched_tubes = []
        released_tubes = []
        
        # OPTIMIZATION: Detect rising edges (0→1) and falling edges (1→0)
        for tube_id, (prev, curr) in enumerate(zip(self.previous_touch_status, current_touch_status)):
            if not prev and curr:  # Rising edge detected (0→1)
                newly_touched_tubes.append(tube_id)
                self.last_touch_time[tube_id] = now
                # Only print if debugging enabled to avoid print latency
                if self.show_touch_debug:
                    print(f"[⚡TOUCH] Tube {tube_id} touched")
            elif prev and not curr:  # Falling edge detected (1→0)
                released_tubes.append(tube_id)
                if self.show_touch_debug:
                    print(f"[⚡RELEASE] Tube {tube_id} released")
        
        # Store current touch status for next iteration
        self.previous_touch_status = current_touch_status.copy()
        
        # Track if any notes were played or stopped
        notes_triggered = False
        
        # OPTIMIZATION: Fast path for immediate sound triggering when using LightSoundMapper
        if (newly_touched_tubes or released_tubes) and isinstance(self.mapping_interface, LightSoundMapper):
            # Pre-allocate reaction_notes to avoid resizing
            reaction_notes = []
            # Track which tube each note comes from for stopping previous notes
            tube_note_mapping = {}
            
            # OPTIMIZATION: Direct processing of touched tubes
            for tube_id in newly_touched_tubes:
                if tube_id < len(current_led_status):
                    # Get the hue value from the LED status
                    hue, brightness, _ = current_led_status[tube_id]
                    
                    # Skip if tube is not lit (brightness too low)
                    if brightness < 20:
                        continue
                    
                    # OPTIMIZATION: Direct conversion without function calls
                    # Convert hue to note using LightSoundMapper's conversion
                    try:
                        semitone = self.mapping_interface.hue_to_semitone(hue)
                        octave = getattr(self.mapping_interface, 'octave', 3)  # Default to 4 if not set
                        note_to_play = semitone + (octave * 12)
                        
                        # OPTIMIZATION: Directly append without checking
                        reaction_notes.append(note_to_play)
                        # Record which tube this note came from
                        tube_note_mapping[tube_id] = note_to_play
                    except Exception as e:
                        print(f"[ERROR] Failed to convert hue to note: {e}")
            
            """
            # OPTIMIZATION: Only print and trigger sound if we have notes to play
            if reaction_notes:
                if self.show_touch_debug:
                    print(f"[⚡MELODY] Touch-triggered notes: {reaction_notes}")
                
                # CRITICAL OPTIMIZATION: Direct, non-blocking sound triggering
                # This is the FAST PATH - absolute minimum latency
                start_time = time.time()
                try:
                    # Send the tube mapping to properly stop previous notes on the same tube
                    success = self.sound_manager.play_direct_notes(reaction_notes, tube_note_mapping)
                    
                    # Measure and store latency
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Track latency for statistics only if successful
                    if success:
                        self.latency_history.append(latency_ms)
                        if len(self.latency_history) > self.max_latency_history:
                            self.latency_history.pop(0)  # Remove oldest measurement
                    
                    # Measure and report latency (but don't wait for it)
                    if self.show_touch_debug:
                        print(f"[⚡PERF] Touch→Sound latency: {latency_ms:.1f}ms")
                    
                    # Periodically report latency statistics
                    if self.show_latency_stats:
                        self.report_latency_stats()
                        
                    notes_triggered = success
                except Exception as e:
                    print(f"[ERROR] Failed to play direct notes: {e}")
            
            # Handle released tubes - stop their notes
            if released_tubes:
                if self.show_touch_debug:
                    print(f"[⚡RELEASE] Stopping notes for tubes: {released_tubes}")
                
                try:
                    # Call stop_notes method to stop notes for the released tubes
                    success = self.sound_manager.stop_notes(released_tubes)
                    if success and self.show_touch_debug:
                        print(f"[⚡RELEASE] Successfully stopped notes for {len(released_tubes)} tubes")
                    notes_triggered = notes_triggered or success
                except Exception as e:
                    print(f"[ERROR] Failed to stop notes: {e}")
            """    
        return notes_triggered  # Return true if any notes were triggered or stopped

    def loop(self):
        # Reduce print statements - only print occasionally
        should_print = (self.loop_idx % 50 == 0)  # OPTIMIZATION: Print less frequently
        
        current_time = time.time()
        touch_notes_sent_this_cycle = False # Flag to track if touch notes were sent

        try:
            # OPTIMIZATION: Read from serial - prioritize touch status first
            self.pillar_manager.read_from_serial()

            # CRITICAL PATH: Get current touch status for immediate processing
            current_touch_status = self.pillar_manager.get_all_touch_status()
            
            # OPTIMIZATION: Immediately process touch before anything else
            current_led_status = self.pillar_manager.get_all_light_status()
            touch_notes_sent_this_cycle = self.process_touch_events(current_touch_status, current_led_status)
            
            # Only print touch status when needed and not too frequently
            if should_print and self.show_touch_debug:
                print(f"[TOUCH] Status: {current_touch_status}")
            
            # The rest of the loop can continue at lower priority...
            # Periodically request LED status from the Teensy
            if current_time - self.last_led_request_time >= self.led_request_interval:
                self.pillar_manager.request_led_status()
                if should_print:
                    print("[LED] Requesting LED status")
                self.last_led_request_time = current_time
            
            # Optimize change detection by identifying specific changes
            changed_tubes = []
            for i, (curr, prev) in enumerate(zip(current_led_status, self.previous_led_status)):
                if curr != prev:
                    changed_tubes.append(i)
            
            led_status_changed = len(changed_tubes) > 0
            if led_status_changed and should_print and self.show_led_debug:
                print(f"[LED] Changes detected in tubes: {changed_tubes}")
            
            # Process LED status changes or periodic updates
            should_process = led_status_changed or (current_time - self.last_led_process_time >= self.led_process_interval)
            
            if should_process:
                # Generate the sound and light state based on button presses
                sound_state, light_state = self.mapping_interface.update_pillar(current_touch_status)
                
                # Only update light state if we're not using LightSoundMapper
                if not isinstance(self.mapping_interface, LightSoundMapper):
                    self.pillar_manager.send_all_light_change(light_state)
                    
                # Process all sound parameters except reaction_notes if they were already handled
                for param_name, value in sound_state.items():
                    # Skip reaction_notes if we already sent them through the fast path
                    if param_name == "reaction_notes" and touch_notes_sent_this_cycle:
                        print(f"[DEBUG] Skipping reaction_notes {value} since they were already played in fast path")
                        continue
                    
                    try:
                        self.sound_manager.update_pillar_setting(param_name, value) 
                    except Exception as e:
                        print(f"[ERROR] Failed to update sound parameter {param_name}: {e}")
                
                # Update tracking variables
                self.previous_led_status = current_led_status.copy()  # Make a copy to avoid reference issues
                self.last_led_process_time = current_time
            
            # Always process sound system with minimal time step
            try:
                self.sound_manager.tick(time_delta=1/60.0)  # 60Hz sound system update
            except Exception as e:
                print(f"[ERROR] Error in sound manager tick: {e}")

            self.loop_idx += 1
            
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"[ERROR] Exception in controller loop: {e}")
            print(f"[DEBUG] Traceback: {error_traceback}")
            time.sleep(0.01)  # Very short sleep on error

    def play_direct_test_note(self, note_number=60):
        """Test function to directly trigger a note"""
        print(f"[DIRECT TEST] Playing note {note_number}")
        try:
            self.sound_manager.update_pillar_setting("reaction_notes", [note_number])
        except Exception as e:
            print(f"[ERROR] Failed to play test note {note_number}: {e}")

    def report_latency_stats(self):
        """Report statistics on touch-to-sound latency"""
        if not self.latency_history:
            return
            
        now = time.time()
        if now - self.last_latency_report_time < self.latency_report_interval:
            return
            
        try:
            latencies = self.latency_history
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            
            # Calculate 95th percentile
            sorted_latencies = sorted(latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            p95_latency = sorted_latencies[p95_index]
            
            print("\n🔊 TOUCH-TO-SOUND LATENCY REPORT 🔊")
            print(f"Sample size: {len(latencies)} touches")
            print(f"Average latency: {avg_latency:.1f}ms")
            print(f"95th percentile: {p95_latency:.1f}ms")
            print(f"Min latency: {min_latency:.1f}ms")
            print(f"Max latency: {max_latency:.1f}ms")
            print("---------------------------------------")
            
            self.last_latency_report_time = now
        except Exception as e:
            print(f"[ERROR] Failed to report latency stats: {e}")

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="A script to parse host, port, and config file path.")
    parser.add_argument("--config", default="config/config.json", help="Path to the JSON config file.")
    parser.add_argument("--serial_port", default=None, help="Overrides the serial in the configuration")
    parser.add_argument("--frequency", default=5, type=int, help="Frequency of the controller loop")
    parser.add_argument("--hostname", default=None, type=str, help="The hostname if different from the base computer")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")

    args = parser.parse_args()
    print(args)

    # Get Hostname
    hostname = args.hostname if args.hostname is not None else socket.gethostname()
    print(f"[INFO] HOSTNAME is {hostname}")
    
    # Verify config file exists
    config_path = args.config
    if not os.path.exists(config_path):
        # Try looking in the current directory and parent directories
        base_name = os.path.basename(config_path)
        for dir_path in [".", "..", "../.."]:
            test_path = os.path.join(dir_path, base_name)
            if os.path.exists(test_path):
                config_path = test_path
                print(f"[INFO] Found config at {config_path}")
                break
        else:
            raise FileNotFoundError(f"Config file not found: {args.config}")

    # Read the JSON config file
    try:
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in config file: {e}")
        raise
    except Exception as e:
        print(f"[ERROR] Failed to read config file: {e}")
        raise

    # Check if the hostname is in the config, if not, use the first pillar or create a fallback
    if hostname not in config["pillars"]:
        print(f"[WARNING] Hostname '{hostname}' not found in configuration")
        if config["pillars"]:
            # Use the first pillar in the config as a fallback
            fallback_hostname = next(iter(config["pillars"]))
            print(f"[INFO] Using '{fallback_hostname}' as fallback configuration")
            hostname = fallback_hostname
        else:
            # If no pillars, create a basic fallback config
            print("[WARNING] No pillars defined in config, creating a basic fallback")
            config["pillars"]["fallback"] = {
                "id": 0,
                "port": "/dev/ttyACM0",
                "num_tubes": 6,
                "map": "FixedMapper",
                "notes": [0, 2, 4, 5, 7, 9],
                "octave": 4
            }
            hostname = "fallback"

    if args.serial_port is not None:
        print(f"[INFO] Reconfigured serial port to: {args.serial_port}")
        config["pillars"][hostname]["port"] = args.serial_port

    # Create a Controller instance and pass the parsed values
    print("[INFO] Initializing and running Controller")
    try:
        controller = Controller(hostname, config)
        controller.start(args.frequency)
    except KeyboardInterrupt:
        print("[INFO] Keyboard interrupt detected, exiting")
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        traceback.print_exc()
        exit(1)
=======
import argparse
import json
import socket
import threading
import queue
import time

from pillar_hw_interface import Pillar
from mapping_interface import RotationMapper, EventRotationMapper, LightSoundMapper, generate_mapping_interface
from sound_manager import SoundManager

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
        self.led_process_interval = 0.2  # Reduce LED processing frequency
        
        # Store previous LED status to detect changes
        self.previous_led_status = [(0, 0, 0) for _ in range(self.pillar_manager.num_tubes)]
            
        # Add rate limiting for loop processing
        self.min_loop_interval = 0.05  # INCREASED RESPONSIVENESS: 20Hz max instead of 5Hz
        self.last_loop_time = 0
        
        # Fast-path for touch events to improve responsiveness
        self.touch_event_time = 0
        self.touch_processing_interval = 0.01  # Process touch events at 100Hz for responsiveness
            
        # Avoid excessive debug printing
        self.debug_print = False  # Add a flag to control debug printing

        # Add special debug flags
        self.show_touch_debug = True
        self.show_led_debug = False  # Turn off LED debug since that's working

        # Disable automatic note playing
        self.use_fallback_mode = False  # Disable fallback mode

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

    def process_touch_events(self, current_touch_status, current_led_status):
        """
        Fast-path handler specifically for touch events to improve responsiveness.
        This is separated from the main loop to prioritize sound triggering.
        """
        # Get previous touch status (or initialize if first run)
        previous_touch_status = getattr(self, 'previous_touch_status', [False] * self.pillar_manager.num_tubes)
        
        # Detect newly touched tubes (0→1 transitions)
        newly_touched_tubes = []
        for i, (prev, curr) in enumerate(zip(previous_touch_status, current_touch_status)):
            if not prev and curr:  # Rising edge detected
                newly_touched_tubes.append(i)
                print(f"[TOUCH DETECTED] Tube {i} was just touched")
        
        # Store current touch status for next iteration
        self.previous_touch_status = current_touch_status
        
        # Fast path for LightSoundMapper - trigger notes immediately based on LED colors
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
                    semitone = self.mapping_interface.hue_to_semitone(hue)
                    octave = self.mapping_interface.octave
                    note_to_play = semitone + (octave * 12)
                    
                    # Add the note to reaction notes
                    reaction_notes.append(note_to_play)
                    print(f"[MELODY] Touch-triggered note {note_to_play} from tube {tube_id} (hue={hue})")
            
            # OPTIMIZATION: Directly play notes for immediate response
            if reaction_notes:
                print(f"[MELODY] Sending notes to sound manager: {reaction_notes}")
                # Use a direct, non-blocking method to play sounds immediately
                self.sound_manager.play_direct_notes(reaction_notes)
                return True  # Flag that we sent notes
                
        return False  # No notes sent

    def loop(self):
        # Reduce print statements - only print occasionally
        should_print = (self.loop_idx % 10 == 0)  # Only print every 10th iteration
        
        current_time = time.time()
        touch_notes_sent_this_cycle = False # Flag to track if touch notes were sent
        
        try:
            # Read from serial to update touch status and LED status
            self.pillar_manager.read_from_serial()

            # Get current touch and LED status - retrieve both at once for synchronization
            current_touch_status = self.pillar_manager.get_all_touch_status()
            current_led_status = self.pillar_manager.get_all_light_status()
            
            # Only print touch status when needed
            if should_print:
                print(f"Touch status: {current_touch_status}")
            
            # OPTIMIZED: Fast-path processing for touch events to improve responsiveness
            touch_notes_sent_this_cycle = self.process_touch_events(current_touch_status, current_led_status)
            
            # Periodically request LED status from the Teensy
            if current_time - self.last_led_request_time >= self.led_request_interval:
                self.pillar_manager.request_led_status()
                if should_print:
                    print("Requesting LED status")
                self.last_led_request_time = current_time
            
            # Optimize change detection by identifying specific changes
            changed_tubes = []
            for i, (curr, prev) in enumerate(zip(current_led_status, self.previous_led_status)):
                if curr != prev:
                    changed_tubes.append(i)
            
            led_status_changed = len(changed_tubes) > 0
            if led_status_changed and should_print:
                print(f"[LED] Changes detected in tubes: {changed_tubes}")
            
            # Process LED status changes or periodic updates - only if we haven't already sent notes
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
                self.previous_led_status = current_led_status.copy()  # Make a copy to avoid reference issues
                self.last_led_process_time = current_time
            
            # Always process sound system, but with minimal time step for better responsiveness
            self.sound_manager.tick(time_delta=1/60.0)  # Increased from 30Hz to 60Hz
            
            self.loop_idx += 1
            
        except Exception as e:
            print(f"[ERROR] Exception in controller loop: {e}")
            time.sleep(0.1)

    def play_direct_test_note(self, note_number=60):
        """Test function to directly trigger a note"""
        print(f"[DIRECT TEST] Playing note {note_number}")
        self.sound_manager.update_pillar_setting("reaction_notes", [note_number])

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
>>>>>>> 27afb2d9e6fa57fe7a9fec4c470bfcf962d034c8
