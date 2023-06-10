from pythonosc import osc_message_builder, udp_client
import datetime
import logging

from nfc_controller import NFC

def main():
    sender = udp_client.SimpleUDPClient('127.0.0.1', 4560)

    nfc = NFC()
    nfc.addBoard("reader1", 8)  # GPIO pin for reader 1 reset
    nfc.addBoard("reader2", 16)  # GPIO pin for reader 2 reset
    nfc.addBoard("reader3", 18)  # GPIO pin for reader 3 reset
    nfc.addBoard("reader4", 10)  # GPIO pin for reader 4 reset

    is_pressed = [False for _ in range(4)]
    datas = [None for _ in range(4)]

    wavs = [
        "269570__vonora__cuckoo-the-nightingale-duet.wav",
        "469313__2hear__ambient-street-traffic-dublin.wav",
        "262947__dangasior__pigs-inside-the-pigsty.wav",
        "529535__straget__thunder-2.wav"
    ]

    # leds = LEDS(21, 120, [0, 30, 60, 90], 255)
    # colours = [
    #     (0, 255, 0),
    #     (125, 80, 200),
    #     (39, 178, 244),
    #     (255, 0, 0)
    # ]

    # leds.fill(0, 0, 255)

    count = 0
    try:
        while True:
            new_datas = [None for _ in range(4)]
            for i in range(4):
                data = nfc.read(f"reader{i+1}")
                data = str(data)
                data = data[:12]
                if data != "None":
                    new_datas[i] = data
            
            for i, (d1, d2) in enumerate(zip(datas, new_datas)):
                if d1 != d2:
                    if d1 is None:
                        sender.send_message('/start', wavs[i])
                        print(f"Sending start message for reader{i+1}: {wavs[i]}")
                        # leds.fill_group(i, *colours[i])

                    if d2 is None:
                        sender.send_message('/stop', wavs[i])
                        print(f"Sending stop message for reader{i+1}: {wavs[i]}")
                        # leds.clear_group()

            datas = new_datas

            string = [f"R{i}: {data}" for i, data in enumerate(new_datas)]
            print(count, " ".join(string))
            count += 1
    except KeyboardInterrupt:
        print("Stopped by User")

if __name__ == "__main__":
    main()