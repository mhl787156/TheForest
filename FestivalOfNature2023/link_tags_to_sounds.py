"""
Use this file to map tags to sounds. It iterates through the folder of Samples
and asks a user to tap an object to each one. A file "sdict.json" is saved with the mapping
of tag id to sample. 

python link_tags_to_sounds.py

Note you may want to change the GPIO pin based on the intended reader
"""
from nfc_controller import NFC
import json
import os
import serial

def main():
    nfc = NFC()
    nfc.addBoard("reader1", 8)  # GPIO pin for reader 1 reset
    nfc.addBoard("reader2", 16)  # GPIO pin for reader 2 reset
    nfc.addBoard("reader3", 18)  # GPIO pin for reader 3 reset
    nfc.addBoard("reader4", 10)  # GPIO pin for reader 4 reset


    with open("sdict.json", "r") as f:
        sdict = json.load(f)

    if not os.path.exists("Samples"):
        return

    sounds = os.listdir("Samples")
    # for fname in os.listdir():
    #     fpath = "samples/%s"%fname
    #     sounds.append()

    read_tags = set(sdict.keys())

    count = 0
    
    try:
        for i, sound in enumerate(sounds):
            if sound in sdict.values():
                print(f"{sound} already in sdict skipping")
                continue

            print("Linking sound: %s"%sound)
            print("%d out of %d"%(i, len(sounds)))
            j = 0
            while True:
                tag_id, text = nfc.read_id(f"reader{(j%4) + 1}")
                if tag_id is not None and tag_id not in read_tags:
                    print(f"Tag read {tag_id}")
                    sdict[tag_id] = sound
                    read_tags.add(tag_id)
                    break
                j+=1
    except KeyboardInterrupt:
        print("Stopped by User")

    with open("sdict.json", "w") as f:
        json.dump(sdict, f)
        print("Written to file")


if __name__ == "__main__":
    main()
