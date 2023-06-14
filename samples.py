import json

class Samples:

    def __init__(self):
        wavs = {}
        try:
            wavs = json.load("sdict.txt")
        except Exception:
            print("Error loading sample dictionary")

    def fetch(self, tag_id):
        return self.wavs[tag_id]

