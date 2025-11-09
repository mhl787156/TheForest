import os 
import sys
from pathlib import Path

dir_path = Path(os.path.dirname(os.path.realpath(__file__))).parent
sys.path.append(os.path.join(dir_path, "src"))

import socket
import json
import time
from mqtt_manager import MqttPillarClient, MqttPillarClientMock
from mapping_interface import SoundState

def _on_other_pillar_receive(topic, their_sound_state, props):
    # On receive of a different pillar do something
    # E.g. play a sound, change a light or something. 

    print("Received topic: %s"%topic)
    # If received from yourself, ignore... 
    _hostname = topic.split("/")[1]
    if _hostname == hostname:
        print("Ignore...")
        return

    try:
        sound_state = json.loads(their_sound_state)
    except Exception as e:
        print("[Message received error] %s"%e)
        sound_state = their_sound_state
        # if "reaction_notes" in sound_state:
        #     # Currently telling composer to play all the reaction notes
        #     notes = sound_state["reaction_notes"]
        #     if len(notes) > 0:
        #         sound_manager.update_pillar_setting("broadcast_notes", notes) 

    print("Received data: ")
    print(sound_state)

def _broadcast_notes_to_other_pillars(hostname, sound_state, mqtt_client):
    data = json.dumps(sound_state.to_json())
    mqtt_client.publish(f"sound_state/{hostname}", data)
    print("Sending Notes via MQTT Client")

    # Send Reaction Notes (or other sound state) to other pillars

    # Currently only send if there is a reaction note
    # if sound_state.has_reaction_notes():
    #     data = json.dumps(sound_state.to_json())
    #     self.mqtt_client.publish(f"sound_state/{hostname}", data)
    #     print("Sending Notes via MQTT Client")

class SoundStateStub(SoundState):

    def __init__(self):
        self.volume = 99#pillar_cfg["volume"]
        self.instruments = 99#pillar_cfg["instruments"]
        self.bpm = 99#pillar_cfg["bpm"]
        self.melody_scale = 99#initial_state["melody_scale"]
        self.melody_number = 99#initial_state["melody_number"]
        self.key = 99#initial_state["key"]
        self.baseline_style = 99#initial_state["baseline_style"]

        ### util state var
        self.change_instrument_next_layer = "melody"
        self.change_tempo_direction = 1
        self.tempo_max = 200
        self.tempo_min = 30
        self.key_center = 60

        self.generated_notes = []
        self.reaction_notes = [1,2,3,4]
        self.active_synths = []

if __name__=="__main__":
    # Get Hostname
    try:
        hostname = socket.gethostname()
        print("HOSTNAME is ", hostname)
    except:
        hostname = "hostname00"

    # Read the JSON config file
    config_file_path = "config/config.json"
    with open(config_file_path, 'r') as config_file:
        config = json.load(config_file)

    if hostname not in config["pillars"]:
        raise RuntimeError(f"This hostname {hostname} not present in configuration")

    print("Run mqtt test")
    print("Initialize mqtt client")
    mqtt_client = MqttPillarClient(
            broker_host=config["mqtt"]["broker_ip"],
            pillar_id=hostname
        )
    
    mqtt_client.connect_and_loop()
    mqtt_client.announce_online()
    mqtt_client.subscribe("sound_state/+")
    mqtt_client.on("sound_state/+", _on_other_pillar_receive)

    while True:
        # Get button state from the Arduino through Serial read
        # self.pillar_manager.read_from_serial()

        # Get button press status
        # current_btn_press = self.pillar_manager.get_all_touch_status()

        # Generate sound state based on button inputs
        # sound_state = self.mapping_interface.update_pillar(current_btn_press)

        # Pass the sound state to the sound manager to activate anything
        # for param_name, value in sound_state.items():
        #     self.sound_manager.update_pillar_setting(param_name, value) 

        sound_state = SoundStateStub()

        # Send any sound state "reaction notes" to other pillars
        print("Broadcasting sound state...")
        _broadcast_notes_to_other_pillars(hostname, sound_state, mqtt_client)
        time.sleep(2)
        # data = {
        #     "btn_press": current_btn_press,
        #     "sound_state": sound_state.to_json()
        # }
