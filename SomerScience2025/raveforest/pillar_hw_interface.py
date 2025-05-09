import serial
import atexit
import threading
import queue
import time
import copy

import argparse
import json
import os


# from MappingInterface import  MappingInterface

def clamp(val, b=0, c=255):
    return max(b, min(val, c))

def read_serial_data(serial_port, cap_queue, light_queue, kill_event):
    print(f"Serial Read Thread Started With {serial_port}")
    
    # Increase serial timeout for better reliability
    serial_port.timeout = 0.1
    
    # Buffer management - only flush once at start
    try:
        serial_port.flushInput()
    except Exception as e:
        print(f"[WARNING] Initial buffer flush failed: {e}")
    
    while True:
        if kill_event.is_set():
            break
            
        try:
            # Read response without flushing buffer every time
            raw_response = serial_port.readline()
            if not raw_response:
                time.sleep(0.05)
                continue
                
            # Decode the response with error handling
            response_str = raw_response.decode('utf-8', errors='ignore').strip()
            if not response_str:
                continue
                
            # Only process valid message formats
            if response_str.startswith("CAP,"):
                parts = response_str.split(",")
                
                if len(parts) >= 7:  # "CAP" + 6 values
                    try:
                        touch_values = [bool(int(parts[i])) for i in range(1, 7)]
                        # Use a priority queue or set a flag for immediate processing
                        cap_queue.put(touch_values)
                        # Add timestamp to measure latency
                        touch_time = time.time()
                        print(f"[TOUCH] CAP event detected at {touch_time:.3f}: {touch_values}")
                    except (ValueError, IndexError) as e:
                        print(f"[ERROR] Failed to process CAP data: {e}")
                        
            elif response_str.startswith("LED,") and len(response_str) >= 10:
                parts = response_str.split(",")
                
                if len(parts) >= 7:  # "LED" + 6 values
                    try:
                        # Process all tubes at once
                        for i in range(6):
                            hue = int(parts[i+1])
                            light_queue.put((i, hue, 255))
                        print(f"[LED] Valid LED data received: {response_str[:20]}...")
                    except (ValueError, IndexError) as e:
                        print(f"[ERROR] Error processing LED data: {e}")
                        
        except Exception as e:
            print(f"[ERROR] Error in read_serial_data: {e}")
            time.sleep(0.1)  # Pause on error to avoid tight loop
            
    print(f"[INFO] Serial Read Thread Exiting")

def write_serial_data(serial_port, write_queue):
    print(f"Serial Write Thread Started With {serial_port}")
    while True:
        try:
            packet = write_queue.get()

            if "kill" in packet:
                # Method of killing the packet
                break

            # print("Packet Sending", packet)
            serial_port.write(packet.encode())
            # Add a small delay to avoid overwhelming the serial port
            time.sleep(0.01)
        except Exception as e:
            print(f"[ERROR] Error writing data: {e}")
        time.sleep(0.1)

    print("[INFO] Serial Write Thread Killed")


class Pillar():

    def __init__(self, id, port, baud_rate=9600, **kwargs):
        self.id = id

        # self.mapping = MappingInterface(copy.deepcopy(kwargs))
        # Print all elements of the mapping object
        #print(f"Mapping Interface: {self.mapping.__dict__}")

        self.serial_read_rate = 10

        self.num_tubes = 7

        self.num_touch_sensors = 6
        self.touch_status = [False for _ in range(self.num_touch_sensors)]
        self.previous_received_status = []

        self.light_status = [(0, 0, 0) for _ in range(self.num_tubes)]

        self.cap_queue = queue.Queue()
        self.light_queue = queue.Queue()  # Using light_queue for all LED status
        self.write_queue = queue.Queue()

        # Add lock for thread safety
        self.status_lock = threading.Lock()

        self.kill_read_thread = threading.Event()

        self.ser = None
        self.serial_status = dict(connected=False, port=port, baud_rate=baud_rate)
        self.ser = self.restart_serial(port, baud_rate)

        # Clear any leftover data
        try:
            self.ser.flushInput()
            self.ser.flushOutput()
        except Exception as e:
            print(f"[WARNING] Failed to flush serial buffers: {e}")

        atexit.register(self.cleanup)


    def restart_serial(self, port, baud_rate=None):
        if self.ser:
            # Signal threads to terminate
            self.write_queue.put("kill")
            self.kill_read_thread.set()
            
            # Wait for threads to terminate before cleanup
            time.sleep(0.2)
            self.cleanup()

        if baud_rate is None:
            baud_rate = self.serial_status["baud_rate"]

        self.serial_status["port"] = port
        self.serial_status["baud_rate"] = baud_rate

        try:
            self.ser = serial.Serial(port, baud_rate)
            self.serial_status["connected"] = True
        except serial.SerialException:
            # Generate a virtual serial port for testing
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"... creating virtual serial port for testing")
            self.ser = serial.serial_for_url(f"loop://{port}", baudrate=baud_rate)
            self.serial_status["connected"] = False

        # Reset the kill event before starting new threads
        self.kill_read_thread = threading.Event()
        
        # Start the read thread
        self.serial_thread = threading.Thread(target=read_serial_data, args=(self.ser, self.cap_queue, self.light_queue, self.kill_read_thread))
        self.serial_thread.daemon = True
        self.serial_thread.start()

        # Start the write thread
        self.serial_write_thread = threading.Thread(target=write_serial_data, args=(self.ser, self.write_queue))
        self.serial_write_thread.daemon = True
        self.serial_write_thread.start()

        print(f"[INFO] Restarted Serial Connection to {port}, {baud_rate}")
        return self.ser

    def cleanup(self):
        print(f"[INFO] Cleaning up and closing the serial connection for pillar {self.id}")
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception as e:
            print(f"[ERROR] Error during cleanup: {e}")

    def to_dict(self):
        with self.status_lock:
            return dict(
                id=self.id, 
                num_tubes=self.num_tubes, 
                num_sensors=self.num_touch_sensors,
                touch_status=self.touch_status.copy(), 
                light_status=self.light_status.copy(), 
                serial_status=self.serial_status.copy()
            )

    def get_touch_status(self, tube_id):
        with self.status_lock:
            return self.touch_status[tube_id]

    def get_all_touch_status(self):
        with self.status_lock:
            return self.touch_status.copy()

    def get_light_status(self, tube_id):
        with self.status_lock:
            return self.light_status[tube_id]

    def get_all_light_status(self):
        with self.status_lock:
            return self.light_status.copy()

    def send_light_change(self, tube_id, hue, brightness):
        """Sends a LED message to change the hue and brightness of an individual tube

        Args:
            tube_id (int): The tube id of the tube to change
            hue (int): [0, 255] the value of the hue
            brightness (int): [0, 255] the value of the brightness

        This sends a LED,{tube_id},{hue},{brightness}; message to the serial port
        for a connected arduino to deal with.

        *HOWEVER* note that this message cannot be sent in quick succession without
        delays in between sends. The serial/message read seems to struggle to pick
        out all of the individual messages. In a case where you need to send all please
        use the `send_all_light_change` function.

        """
        assert tube_id < self.num_tubes
        assert 0 <= hue <= 255
        assert 0 <= brightness <= 255
        message = f"LED,{tube_id},{hue},{brightness};\n\r"
        #print("Pushing to queue", message)
        self.write_queue.put(message)

    def send_all_light_change(self, lights):
        """Send all the lights in one go

        This uses the ALLLED message
        ALLLED,h1,b1,...,hn,bn;

        Argument lights assumed to be a list of tuples (hue, brightness)
        """
        light_list = []
        for i, l in enumerate(lights):
            hue = clamp(l[0])
            bright = clamp(l[1])
            light_list.extend([str(hue), str(bright), str(0)])
        message = f"ALLLED,{','.join(light_list)};"
        # print(f'Message being sent: {message}')
        
        # FIXED: Don't use empty() - it only checks if empty, doesn't clear the queue
        # Instead, use a new approach that's thread-safe
        try:
            # Clear pending light changes by emptying the queue
            while not self.write_queue.empty():
                try:
                    self.write_queue.get_nowait()
                except queue.Empty:
                    break
        except Exception as e:
            print(f"[ERROR] Error clearing write queue: {e}")
            
        # Now put the new message
        self.write_queue.put(message)

    def set_touch_status(self, touch_status):
        # Thread-safe update of touch status
        with self.status_lock:
            self.touch_status = touch_status.copy()  # Make a copy to avoid reference issues
            # print(f"UPDATING TOUCH STATUS to: {touch_status}")

    def set_touch_status_tube(self, tube_id, status):
        with self.status_lock:
            self.touch_status[tube_id] = bool(status)  # Ensure it's a boolean

    def reset_touch_status(self):
        with self.status_lock:
            # FIXED: Use False instead of 0 for consistency
            self.touch_status = [False for _ in range(self.num_touch_sensors)]

    def read_from_serial(self):
        # Handle touch sensor data
        try:
            while not self.cap_queue.empty():
                received_status = self.cap_queue.get_nowait()
                
                # Ensure received_status has the correct length
                if len(received_status) != self.num_touch_sensors:
                    print(f"[WARNING] Received touch status has {len(received_status)} sensors, expected {self.num_touch_sensors}")
                    # Pad with False if too short
                    if len(received_status) < self.num_touch_sensors:
                        received_status.extend([False] * (self.num_touch_sensors - len(received_status)))
                    # Truncate if too long
                    if len(received_status) > self.num_touch_sensors:
                        received_status = received_status[:self.num_touch_sensors]
                
                # Get a thread-safe copy of the previous status
                with self.status_lock:
                    previous_status = self.previous_received_status.copy() if self.previous_received_status else []
                
                # Only update and print if status changed
                if received_status != previous_status:
                    print(f"[TOUCH] Processing touch status: {received_status}")
                    self.set_touch_status(received_status)
                    # Thread-safe update of previous status
                    with self.status_lock:
                        self.previous_received_status = received_status.copy()
                    # Handle end of touch event
                    self.handle_end_of_touch(received_status)
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[ERROR] Error processing touch data: {e}")

        # Handle LED status data
        try:
            while not self.light_queue.empty():
                led_data = self.light_queue.get_nowait()
                
                # Format from the queue should be (tube_id, hue, brightness)
                tube_id, hue, brightness = led_data
                
                # Validate tube_id is in range
                if 0 <= tube_id < self.num_tubes:
                    # Thread-safe update of light status
                    with self.status_lock:
                        # Store as (hue, brightness, effect) - THIS IS THE IMPORTANT FORMAT
                        self.light_status[tube_id] = (hue, brightness, 0)
                    print(f"[LED] Updated light status for tube {tube_id}: hue={hue}, brightness={brightness}")
                else:
                    print(f"[WARNING] LED tube_id {tube_id} out of range (0-{self.num_tubes-1})")
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[ERROR] Error processing light queue: {e}")

    def handle_end_of_touch(self, received_status):
        if all(not status for status in received_status):  # All touch sensors are inactive - Boolean check
            self.reset_touch_status()
            # Function to send a WebSocket message to frontend
            self.notify_frontend_touch_reset()

    def notify_frontend_touch_reset(self):
        reset_message = json.dumps({"type": "touch_reset", "pillar_id": self.id})
        print(f"[INFO] Touch reset for pillar {self.id}")
        # Placeholder for actual WebSocket sending logic
        # send_to_all_clients(reset_message)  # You need to implement this based on your WebSocket setup
        
    # Add a method to request LED status from the Teensy
    def request_led_status(self):
        """Send a command to the Teensy to request current LED status for all tubes."""
        try:
            message = "GETLED;\n\r"
            print(f"[DEBUG] Requesting LED status from Teensy: {message.strip()}")
            self.write_queue.put(message)
            # Short sleep to avoid overwhelming the serial buffer
            time.sleep(0.1)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to request LED status: {e}")
            return False

    def process_serial_data(self, line):
        """Process data received from the serial port."""
        try:
            # Process touch data
            if line.startswith("CAP"):
                parts = line.split(",")
                if len(parts) >= 7:  # "CAP" + 6 values
                    touch_status = [bool(int(parts[i])) for i in range(1, 7)]
                    with self.status_lock:
                        self.touch_status = touch_status
            
            # Process LED data - NEW FORMAT: LED,hue1,hue2,hue3,hue4,hue5,hue6
            elif line.startswith("LED"):
                parts = line.split(",")
                if len(parts) >= 7:  # "LED" + 6 hue values
                    for i in range(6):
                        try:
                            hue = int(parts[i+1])
                            # Fixed brightness
                            brightness = 255
                            effect = 0
                            with self.status_lock:
                                self.light_status[i] = (hue, brightness, effect)
                        except ValueError:
                            print(f"[ERROR] Error parsing LED value for tube {i}")
        
        except Exception as e:
            print(f"[ERROR] Error processing serial data: {e}")
        