from pythonosc import osc_message_builder, udp_client
from nfc_controller import NFC
import json
import os

sounds = [
    "269570__vonora__cuckoo-the-nightingale-duet.wav",
    "469313__2hear__ambient-street-traffic-dublin.wav",
    "262947__dangasior__pigs-inside-the-pigsty.wav",
    "529535__straget__thunder-2.wav"
]

def main():
    sender = udp_client.SimpleUDPClient('127.0.0.1', 4560)
    nfc = NFC()
    nfc.addBoard("reader1", 8)  # GPIO pin for reader 1 reset

    ser = serial.Serial('/dev/ttyACM1', 115200, timeout=1)
    ser.reset_input_buffer()

    if not os.path.exists("samples"):
        return
    
    sounds = os.listdir()
    # for fname in os.listdir():
    #     fpath = "samples/%s"%fname
    #     sounds.append()

    count = 0
    sdict = {}
    try:
        for i, sound in enumerate(sounds):
            print("Linking sound: %s"%sound)
            print("%d out of %d"%(i, len(sounds)))
            while True:
                data = nfc.read("reader1")
                data = str(data)
                data = data[:12]
                if data != "None":
                    print("Tag read %s"%data)
                    sdict[sound] = data
                    continue
    except KeyboardInterrupt:
        print("Stopped by User")

    with open("sdict.txt", "w") as f:
        f.write(json.dumps(sdict))


if __name__ == "__main__":
    main()