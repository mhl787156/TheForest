import serial
import threading
import queue
import time
def write(conn, q):
    while True:
        value = q.get()
        print(f"Sending {value}")
        conn.write(value.encode())

q = queue.Queue()

ser = serial.Serial("/dev/ttyACM1", 9600)
packet="LED,4,250,255;"

thr = threading.Thread(target=write, args=(ser,q,))
thr.daemon=True
thr.start()

for i in range(7):
    q.put(f"LED,{i},0,0")
    time.sleep(0.1)

print("ALL OFF")
time.sleep(5)
for i in range(5):
    packet=f"LED,{i},{50*i},255;"
    q.put(packet)
    #time.sleep(0.2)
time.sleep(3)
