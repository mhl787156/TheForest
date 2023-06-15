from pythonosc import osc_message_builder, udp_client
import datetime
import logging
import serial
import json

from nfc_controller import NFC

def main():
    sender = udp_client.SimpleUDPClient('127.0.0.1', 4560)

    nfc = NFC()
    nfc.addBoard("reader1", 8)  # GPIO pin for reader 1 reset
    nfc.addBoard("reader2", 16)  # GPIO pin for reader 2 reset
    nfc.addBoard("reader3", 18)  # GPIO pin for reader 3 reset
    nfc.addBoard("reader4", 10)  # GPIO pin for reader 4 reset

    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    ser.reset_input_buffer()

    # map from reader to led segment
    reader_led_map = {
        0:0,
        1:1,
        2:2,
        3:3
    }

    is_pressed = [False for _ in range(4)]
    datas = [None for _ in range(4)]
    new_datas = []

    # Wavs is mapping between tag_id and sample
    with open("sdict.json", 'rb') as sdict:
        wavs = json.load(sdict)

    print(f"Loaded {len(wavs)} samples from sdict: {wavs}")

    count = 0
    try:
        while True:
            new_datas = [None for _ in range(4)]
            for i in range(4):
                tag_id, _ = nfc.read_id(f"reader{i+1}")
                if tag_id is not None:
                    tag_id = str(tag_id)
                    if tag_id in wavs:
                        new_datas[i] = (tag_id, wavs[tag_id])
                    else:
                        print(f"Tag id {tag_id} read but not in wavs")

            for i, (d1, d2) in enumerate(zip(datas, new_datas)):
                if d1 != d2:
                    if d1 is None:
                        sender.send_message('/start', d2[1])
                        print(f"Sending start message for reader{i+1}: {d2[1]}")
                        
                        # Trigger LED change
                        ser.write(f"{reader_led_map[i]},1;\n".encode())
                        print("Triggering LED change")

                    if d2 is None:
                        sender.send_message('/stop', d1[1])
                        print(f"Sending stop message for reader{i+1}: {d1[1]}")

                        # Trigger LED change back to ambient
                        ser.write(f"{reader_led_map[i]},7;\n".encode())

            datas = new_datas

            string = [f"R{i}: {data}" for i, data in enumerate(new_datas)]
            print(count, " ".join(string))
            count += 1
    except KeyboardInterrupt:
        print("Stopped by User")
        for i, d in enumerate(new_datas):
            if d is not None:
                sender.send_message('/stop', d[1])
                print(f"Sending stop message for reader{i+1}: {d[1]}")


if __name__ == "__main__":
    main()