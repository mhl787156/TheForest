import serial
import atexit
import threading
import queue
import time

import config

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
                status = response.split(",")[1:]
                cap_queue.put([bool(int(i)) for i in status])
            elif "LED" in response:
                status = response.split(",")[1:]
                light_queue.put([int(i) for i in status])
            
        except Exception as e:
            pass
            # print(f"Error reading data: {e}")
            
    print("Serial Read Thread Killed")
            

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
        except Exception as e:
            print(f"Error writing data: {e}")
        time.sleep(0.1)

    print("Serial Write Thread Killed")
            

class Pillar():

    def __init__(self, id, port, pan, baud_rate=9600):
        self.id = id
        self.pan = pan

        self.serial_read_rate = 10

        self.num_tubes = 7

        self.num_touch_sensors = 6
        self.touch_status = [0 for _ in range(self.num_touch_sensors)]
        self.previous_received_status = []

        self.light_status = [(0, 0, 0) for _ in range(self.num_tubes)]

        self.cap_queue =  queue.Queue()
        self.light_queue = queue.Queue()
        self.write_queue = queue.Queue()

        self.kill_read_thread = threading.Event()

        self.ser = None
        self.serial_status = dict(connected=False, port=port, baud_rate=baud_rate)
        self.ser = self.restart_serial(port, baud_rate)

        atexit.register(self.cleanup)

    
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
            id=self.id, pan=self.pan, num_tubes=self.num_tubes, num_sensors=self.num_touch_sensors,
            touch_status=self.touch_status, light_status=self.light_status, serial_status=self.serial_status
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
        # print("Pushing to queue", message)
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
            light_list.extend([str(hue), str(bright)])
        message = f"ALLLED,{','.join(light_list)};"
        self.write_queue.put(message)
    
    def set_touch_status(self, touch_status):
        self.touch_status = touch_status
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


    