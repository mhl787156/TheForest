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
    while True:
        try:

            if kill_event.is_set():
                break

            response = serial_port.readline().decode().strip()
            # Parse button state from Arduino: "BUTTONS:0,1,0,0"
            if response.startswith("BUTTONS:"):
                status_str = response.split(":")[1]
                status = status_str.split(",")
                # Convert to boolean list
                cap_queue.put([bool(int(i)) for i in status])

        except Exception as e:
            pass
            print(f"Error reading data: {e}")

    print("Serial Read Thread Killed")

def write_serial_data(serial_port, write_queue):
    print(f"Serial Write Thread Started With {serial_port}")
    while True:
        try:
            packet = write_queue.get()

            if "kill" in packet:
                # Method of killing the packet
                break

            # Arduino doesn't accept LED commands, but keep thread for future use
            # print("Packet Sending", packet)
            # serial_port.write(packet.encode())
        except Exception as e:
            print(f"Error writing data: {e}")
        time.sleep(0.1)

    print("Serial Write Thread Killed")

class Pillar():

    def __init__(self, id, port, baud_rate=9600, **kwargs):
        self.id = id

        # self.mapping = MappingInterface(copy.deepcopy(kwargs))
        # Print all elements of the mapping object
        #print(f"Mapping Interface: {self.mapping.__dict__}")

        self.serial_read_rate = 10

        self.num_buttons = kwargs.get('num_buttons', 4)

        self.num_touch_sensors = self.num_buttons
        self.touch_status = [False for _ in range(self.num_touch_sensors)]
        self.previous_received_status = []

        self.cap_queue = queue.Queue()
        self.light_queue = queue.Queue()
        self.write_queue = queue.Queue()

        self.kill_read_thread = threading.Event()

        self.ser = None
        self.serial_status = dict(connected=False, port=port, baud_rate=baud_rate)
        self.ser = self.restart_serial(port, baud_rate)

        atexit.register(self.cleanup)

        # Add lock for thread safety
        self.status_lock = threading.Lock()

    def restart_serial(self, port, baud_rate=None):
        if self.ser:
            self.cleanup()
            self.write_queue.put("kill")
            self.kill_read_thread.set()

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

        self.kill_read_thread = threading.Event()
        self.serial_thread = threading.Thread(target=read_serial_data, args=(self.ser, self.cap_queue, self.light_queue, self.kill_read_thread, ))
        self.serial_thread.daemon = True
        self.serial_thread.start()

        self.serial_write_thread = threading.Thread(target=write_serial_data, args=(self.ser, self.write_queue,))
        self.serial_write_thread.daemon = True
        self.serial_write_thread.start()

        print(f"Restarted Serial Connection to {port}, {baud_rate}")
        return self.ser

    def cleanup(self):
        print(f"Cleaning up and closing the serial connection for pillar {self.id}")
        if self.ser.is_open:
            self.ser.close()

    def to_dict(self):
        return dict(
            id=self.id, num_buttons=self.num_buttons, num_sensors=self.num_touch_sensors,
            touch_status=self.touch_status, serial_status=self.serial_status
        )

    def get_touch_status(self, tube_id):
        return self.touch_status[tube_id]

    def get_all_touch_status(self):
        return self.touch_status


    def set_touch_status(self, touch_status):
        # Do the filter here
        
        self.touch_status = touch_status #[:-1]
        # print(f"UPDATING TOUCH STATUS to: {touch_status}")

    def set_touch_status_tube(self, tube_id, status):
        self.touch_status[tube_id] = bool(status)

    def read_from_serial(self):
        # Handle button state data
        try:
            while not self.cap_queue.empty():
                received_status = self.cap_queue.get_nowait()

                # Ensure received_status has the correct length
                if len(received_status) != self.num_touch_sensors:
                    print(
                        f"[WARNING] Received button status has {len(received_status)} buttons, expected {self.num_touch_sensors}")
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
                    print(f"[BUTTON] Processing button status: {received_status}")
                    self.set_touch_status(received_status)
                    # Thread-safe update of previous status
                    with self.status_lock:
                        self.previous_received_status = received_status.copy()
                    # Handle end of touch event
                    self.handle_end_of_touch(received_status)
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[ERROR] Error processing button data: {e}")

    def reset_touch_status(self):
        self.touch_status = [0 for _ in range(self.num_touch_sensors)]

    def read_from_serial_old(self):
        # Existing implementation...
        # print("Reading from serial")
        try:
            while not self.cap_queue.empty():
                # print("HELLLOOOOOO")
                received_status = self.cap_queue.get_nowait()
                # print("Receiving", received_status)
                if received_status != self.previous_received_status:
                    self.set_touch_status(received_status)
                    # Assuming a function to handle end of touch event
                    self.handle_end_of_touch(received_status)
                self.previous_received_status = received_status
        except queue.Empty:
            # print("Queue Empty")
            pass

    def handle_end_of_touch(self, received_status):
        if all(status == 0 for status in received_status):  # All touch sensors are inactive
            self.reset_touch_status()
            # Function to send a WebSocket message to frontend
            self.notify_frontend_touch_reset()

    def notify_frontend_touch_reset(self):
        reset_message = json.dumps({"type": "touch_reset", "pillar_id": self.id})
        # Placeholder for actual WebSocket sending logic
        # send_to_all_clients(reset_message)  # You need to implement this based on your WebSocket setup
        
