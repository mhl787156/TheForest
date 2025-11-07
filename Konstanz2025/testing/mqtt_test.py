import socket
from mqtt_manager import MqttPillarClient, MqttPillarClientMock


def _on_other_pillar_receive(their_sound_state):
    # On receive of a different pillar do something
    # E.g. play a sound, change a light or something. 

    sound_state = json.loads(their_sound_state)
    print("Received: ")
    print(sound_state)
    # if "reaction_notes" in sound_state:
    #     # Currently telling composer to play all the reaction notes
    #     notes = sound_state["reaction_notes"]
    #     if len(notes) > 0:
    #         sound_manager.update_pillar_setting("broadcast_notes", notes) 

def _broadcast_notes_to_other_pillars(hostname, sound_state):
    data = json.dumps(sound_state.to_json())
    self.mqtt_client.publish(f"sound_state/{hostname}", data)
    print("Sending Notes via MQTT Client")

    # Send Reaction Notes (or other sound state) to other pillars

    # Currently only send if there is a reaction note
    # if sound_state.has_reaction_notes():
    #     data = json.dumps(sound_state.to_json())
    #     self.mqtt_client.publish(f"sound_state/{hostname}", data)
    #     print("Sending Notes via MQTT Client")


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
            broker_host=config["mqtt"]["mqtt_broker_ip"],
            pillar_id=hostname
        )
    
    mqtt_client.announce_online()
    # mqtt_client.on("sound_state/*", _on_other_pillar_receive)

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

        echo_state = "echo-o-o-o"

        # Send any sound state "reaction notes" to other pillars
        _broadcast_notes_to_other_pillars(hostname, echo_state)
        
        # data = {
        #     "btn_press": current_btn_press,
        #     "sound_state": sound_state.to_json()
        # }
