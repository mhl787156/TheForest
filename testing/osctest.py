from pythonosc import osc_message_builder
from pythonosc import udp_client
import time


s1_birds = "269570__vonora__cuckoo-the-nightingale-duet.wav"
s2_urban = "469313__2hear__ambient-street-traffic-dublin.wav"

sender = udp_client.SimpleUDPClient('127.0.0.1', 4560)

sender.send_message('/start', s1_birds)

time.sleep(1)

sender.send_message('/start', s2_urban)

time.sleep(10)

sender.send_message('/stop', s1_birds)

time.sleep(1)

sender.send_message('/stop', s2_urban)
