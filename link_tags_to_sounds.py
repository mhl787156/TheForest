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

sounds = [
    "269570__vonora__cuckoo-the-nightingale-duet.wav",
    "469313__2hear__ambient-street-traffic-dublin.wav",
    "262947__dangasior__pigs-inside-the-pigsty.wav",
    "529535__straget__thunder-2.wav"
]

def main():
    nfc = NFC()
    nfc.addBoard("reader1", 16)  # GPIO pin for reader 2 reset

    if not os.path.exists("Samples"):
        return
    
    sounds = os.listdir("Samples")
    # for fname in os.listdir():
    #     fpath = "samples/%s"%fname
    #     sounds.append()

    read_tags = set()

    count = 0
    sdict = {}
    try:
        for i, sound in enumerate(sounds):
            print("Linking sound: %s"%sound)
            print("%d out of %d"%(i, len(sounds)))
            while True:
                tag_id, text = nfc.read_id("reader1")
                if tag_id is not None and tag_id not in read_tags:
                    print(f"Tag read {tag_id}")
                    sdict[tag_id] = sound
                    read_tags.add(tag_id)
                    break
    except KeyboardInterrupt:
        print("Stopped by User")

    with open("sdict.json", "w") as f:
        json.dump(sdict, f)
        print("Written to file")


if __name__ == "__main__":
    main()