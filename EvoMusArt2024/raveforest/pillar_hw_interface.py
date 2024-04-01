import serial
import atexit
import threading
import queue
import time
import copy

import argparse
import json
import os


from MappingInterface import  MappingInterface

path = os.getcwd()
config_path = os.path.abspath(os.path.join(path, os.pardir, "EvoMusArt2024/config/config.json")) #'/home/admin-amcs/Desktop/FUTURES FEST/TheForest/Futures2023/config/config.json'

# Read the JSON config file
with open(config_path, 'r') as config_file:
    config = json.load(config_file)

def clamp(val, b=0, c=255):
    return max(b, min(val, c))

def read_serial_data(serial_port, cap_queue, light_queue, kill_event):
    print(f"Serial Read Thread Started With {serial_port}")
    while True:
        try:

            if kill_event.is_set():
                break

            response = serial_port.readline().decode().strip()

            if "CAP" in response:
                status = response.split(",")[:-1]
                cap_queue.put([bool(int(i)) for i in status])
            elif "LED" in response:
                status = response.split(",")[:-1]
                light_queue.put([int(i) for i in status])

        except Exception as e:
            pass
            # print(f"Error reading data: {e}")

    print("Serial Read Thread Killed")


def write_serial_data(name, serial_port, write_queue):
    print(f"Serial Write Thread ({name}) Started With {serial_port}")
    while True:
        try:
            packet = write_queue.get()

            if "kill" in packet:
                # Method of killing the packet
                break

            print(f"Packet Sending to {name}", packet)
            serial_port.write(packet.encode())
        except Exception as e:
            print(f"Error writing data for {name}, {serial_port}: {e}")
        time.sleep(0.1)

    print("Serial Write Thread Killed")


class Pillar():

    def __init__(self, id, port_cap, port_led, baud_rate=9600, **kwargs):
        self.id = id

        self.mapping = MappingInterface(copy.deepcopy(kwargs))
        # Print all elements of the mapping object
        #print(f"Mapping Interface: {self.mapping.__dict__}")

        self.serial_read_rate = 10

        self.num_tubes = 6

        self.num_touch_sensors = 6
        self.touch_status = [0 for _ in range(self.num_touch_sensors)]
        self.previous_received_status = []

        self.light_status = [(0, 0, 0) for _ in range(self.num_tubes)]

        self.cap_queue = queue.Queue()
        self.light_queue = queue.Queue()
        self.write_cap_queue = queue.Queue()
        self.write_led_queue = queue.Queue()

        self.kill_read_thread = threading.Event()

        self.serial_read_threads = []
        self.serial_write_threads = []

        self.serial_status_cap = dict(connected=False, port=port_cap, baud_rate=baud_rate)
        # self.ser_cap, self.serial_status_cap = self.restart_serial(f"cap-{self.id}", None, self.serial_status_cap, self.write_cap_queue)
        
        self.serial_status_led = dict(connected=False, port=port_led, baud_rate=baud_rate)
        # self.ser_led, self.serial_status_led = self.restart_serial(f"led-{self.id}", None, self.serial_status_led, self.write_led_queue)

        # atexit.register(lambda: self.cleanup(self.ser_cap))
        atexit.register(lambda: self.cleanup(self.ser_led))


    def restart_serial(self, name, serial_conn, serial_status, write_queue):
        if serial_conn is not None:
            self.cleanup(serial_conn)
            write_queue.put("kill")
            self.kill_read_thread.set()

        port = serial_status["port"]
        baud_rate = serial_status["baud_rate"]

        try:
            serial_conn = serial.Serial(port, baud_rate)
            serial_status["connected"] = True
        except serial.SerialException:
            # Generate a virtual serial port for testing
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"... creating virtual serial port for testing")
            serial_conn = serial.serial_for_url(f"loop://{port}", baudrate=baud_rate)
            serial_status["connected"] = False

        self.kill_read_thread = threading.Event()
        serial_thread = threading.Thread(target=read_serial_data, args=(serial_conn, self.cap_queue, self.light_queue, self.kill_read_thread, ))
        serial_thread.daemon = True
        serial_thread.start()
        # self.serial_read_threads.append(serial_thread)

        serial_write_thread = threading.Thread(target=write_serial_data, args=(name, serial_conn, write_queue,))
        serial_write_thread.daemon = True
        serial_write_thread.start()
        # self.serial_write_threads.append(serial_write_thread)

        print(f"Restarted Serial Connection to {serial_status}")
        return serial_conn, serial_status

    def cleanup(self, ser):
        print(f"Cleaning up and closing the serial connection ({ser}) for pillar {self.id}")
        if ser is not None and ser.is_open:
            ser.close()

    def to_dict(self):
        return dict(
            id=self.id, num_tubes=self.num_tubes, num_sensors=self.num_touch_sensors,
            touch_status=self.touch_status, light_status=self.light_status, 
            serial_status=self.serial_status_led,
            serial_status_cap=self.serial_status_cap
        )

    def get_touch_status(self, tube_id):
        return self.touch_status[tube_id]

    def get_all_touch_status(self):
        return self.touch_status

    def get_light_status(self, tube_id):
        return self.light_status[tube_id]

    def get_all_light_status(self):
        return self.light_status

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
        use the `send_all_light_chanege` function.

        """
        assert tube_id < self.num_tubes
        assert 0 <= hue <= 255
        assert 0 <= brightness <= 255
        message = f"LED,{tube_id},{hue},{brightness};\n\r"
        #print("Pushing to queue", message)
        self.write_led_queue.put(message)

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
            light_list.extend([str(hue), str(bright)])
        message = f"ALLLED,{','.join(light_list)};"
        print(f'Message being sent: {message}')
        self.write_led_queue.empty()
        self.write_led_queue.put(message)

    def set_touch_status(self, touch_status):
        # Do the filter here
        
        self.touch_status = touch_status[:-1]
        print(f"UPDATING TOUCH STATUS to: {touch_status}")

    def set_touch_status_tube(self, tube_id, status):
        self.touch_status[tube_id] = bool(status)

    def read_from_serial(self):
        try:
            while True:
                recevied_status = self.cap_queue.get(block=False)
                if recevied_status != self.previous_received_status:
                    # Only update touch status if different
                    # This enables other sources of touch status
                    self.set_touch_status(recevied_status)
                self.previous_received_status = recevied_status
        except queue.Empty:
            pass

        try:
            while True:
                (tid, hue, sat) = self.light_queue.get(block=False)
                self.light_status[tid] = (tid, hue, sat)
        except queue.Empty:
            pass


    def reset_touch_status(self):
        self.touch_status = [0 for _ in range(self.num_touch_sensors)]

    def handle_end_of_touch(self, received_status):
        if all(status == 0 for status in received_status):  # All touch sensors are inactive
            self.reset_touch_status()
            # Function to send a WebSocket message to frontend
            self.notify_frontend_touch_reset()

    def notify_frontend_touch_reset(self):
        reset_message = json.dumps({"type": "touch_reset", "pillar_id": self.id})
        # Placeholder for actual WebSocket sending logic
        # send_to_all_clients(reset_message)  # You need to implement this based on your WebSocket setup