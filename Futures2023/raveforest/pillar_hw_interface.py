import serial
import atexit
import threading
import queue
import time

import config

def clamp(val, b=0, c=255):
    return max(b, min(val, c))

def read_serial_data(serial_port, cap_queue, light_queue):
    while True:
        time.sleep(0.2)
        try:
            response = serial_port.readline().decode().strip()

            if "CAP" in response:
                status = response.split(",")[1:]
                cap_queue.put([bool(int(i)) for i in status])
            elif "LED" in response:
                status = response.split(",")[1:]
                # tnum = status[0]
                # hue = status[1]
                # brightness = status[2]
                light_queue.put([int(i) for i in status])
            
        except Exception as e:
            print(f"Error reading data: {e}")
            break


class Pillar():

    def __init__(self, id, port, baud_rate=9600):
        self.id = id

        self.serial_read_rate = 10

        self.num_tubes = 7

        self.num_touch_sensors = 6
        self.touch_status = [0 for _ in range(self.num_touch_sensors)]

        self.light_status = [(0, 0, 0) for _ in range(self.num_tubes)]

        self.cap_queue =  queue.Queue()
        self.light_queue = queue.Queue()

        if config.SERIAL_ENABLED:
            self.ser = serial.Serial(port, baud_rate)
            atexit.register(self.cleanup)

            serial_thread = threading.Thread(target=read_serial_data, args=(self.ser, self.cap_queue, self.light_queue,))
            serial_thread.daemon = True
            serial_thread.start()
    
    def cleanup(self):
        print(f"Cleaning up and closing the serial connection for pillar {self.id}")
        if config.SERIAL_ENABLED and self.ser.is_open:
            self.ser.close()

    def get_touch_status(self, tube_id):
        return self.touch_status[tube_id]
    
    def get_all_touch_status(self):
        return self.touch_status
    
    def get_light_status(self, tube_id):
        return self.light_status[tube_id]

    def get_all_light_status(self):
        return self.light_status
    
    def send_light_change(self, tube_id, hue, brightness):
        assert tube_id < self.num_tubes
        assert 0 <= hue <= 255
        assert 0 <= brightness <= 255
        message = f"LED, {tube_id}, {hue}, {brightness}"
        if config.SERIAL_ENABLED:
            self.ser.write(message.encode())
        else:
            pass
            # print(f"[Serial Disabled] Sending {message}")
    
    def send_all_light_change(self, lights):
        for i, l in enumerate(lights):
            self.send_light_change(i, clamp(l[0]), clamp(l[1]))
    
    def read_from_serial(self):
        try:
            self.touch_status = self.cap_queue.get(block=False)
        except queue.Empty:
            pass
    
        try:
            self.light_status = self.light_queue.get(block=False)
        except queue.Empty:
            pass


    