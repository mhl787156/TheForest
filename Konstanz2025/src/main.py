import argparse
import json
import socket
import threading
import queue
import time

from pillar_hw_interface import Pillar
from mapping_interface import RotationMapper, EventRotationMapper, generate_mapping_interface
from sound_manager import SoundManager
from mqtt_manager import MqttPillarClient, MqttPillarClientMock

import requests

import csv

class APISender(threading.Thread):
    def __init__(self, endpoint, data_queue, interval=0.2):
        """
        A thread that sends data packets to an API at a specified interval.

        :param endpoint: The API endpoint URL.
        :param data_queue: A queue for receiving data from the main loop.
        :param interval: Time between requests in seconds (5Hz = 0.2s).
        """
        super().__init__()
        self.endpoint = endpoint
        self.data_queue = data_queue
        self.interval = interval
        self.running = True

    def run(self):
        while self.running:
            try:
                # Get the latest data, or wait for it (timeout to prevent hanging on stop)
                data = self.data_queue.get(timeout=1)  
                response = requests.post(self.endpoint, json=data, timeout=2)
                # print(f"Sent data: {data}, Response: {response.status_code}")
            except queue.Empty:
                # If no data is available, continue waiting
                pass
            except requests.RequestException as e:
                print(f"Request failed: {e}")

            time.sleep(self.interval)

    def stop(self):
        self.running = False

class Controller():

    def __init__(self, hostname, config):
        self.config = config
        self.num_pillars = len(config["pillars"])        
        self.pillar_config = config["pillars"][hostname]
        self.pillar_manager = Pillar(**self.pillar_config)
        self.mapping_interface = generate_mapping_interface(config, self.pillar_config)
        self.sound_manager = SoundManager(hostname, self.pillar_config)
        self.loop_idx = 0
        self.running = True

        self.data_queue = queue.Queue()  # Thread-safe queue for data exchange

        self.mqtt_enabled = config["mqtt"]["enable"]
        # MQTT to finish
        if self.mqtt_enabled:
            print("[MQTT] Enabled")
            mqttObject = MqttPillarClientMock if config["mqtt"]["mock"] else MqttPillarClient
            self.mqtt_client = mqttObject(
                broker_host=config["mqtt"]["broker_ip"],
                pillar_id=hostname
            )

            print("[MQTT] Connecting to broker host: %s"%config["mqtt"]["broker_ip"])
            self.mqtt_client.connect_and_loop()
            self.mqtt_client.announce_online()
            self.mqtt_client.subscribe("sound_state/+")
            self.mqtt_client.on("sound_state/+", self.on_other_pillar_receive)

    def start(self, frequency):
        """Starts the main control loop

        Args:
            frequency (_type_): _description_
        """
        index = 0

        while self.running:
            self.loop()

    def stop(self):
        self.running = False

    def on_other_pillar_receive(self, topic, their_sound_state, props):
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
        
        print("Received data: ")
        print(sound_state)

        if "reaction_notes" in sound_state:
            # Currently telling composer to play all the reaction notes
            notes = sound_state["reaction_notes"]
            if len(notes) > 0:
                self.sound_manager.update_pillar_setting("broadcast_notes", notes) 

    def broadcast_notes_to_other_pillars(self, sound_state):
        # Send Reaction Notes (or other sound state) to other pillars

        # Currently only send if there is a reaction note
        if sound_state.has_reaction_notes():
            data = json.dumps(sound_state.to_json())
            self.mqtt_client.publish(f"sound_state/{hostname}", data)
            print("Sending Notes via MQTT Client")
    
    def loop(self):

        # Get button state from the Arduino through Serial read
        self.pillar_manager.read_from_serial()

        # Get button press status
        current_btn_press = self.pillar_manager.get_all_touch_status()

        # Generate sound state based on button inputs
        sound_state = self.mapping_interface.update_pillar(current_btn_press)

        # Debug: print active_synths if any are triggered
        if hasattr(sound_state, 'active_synths') and any(v for k, v in sound_state.active_synths.items() if k != 'background'):
            print(f"[MAIN LOOP] active_synths: {sound_state.active_synths}")

        # Pass the sound state to the sound manager to activate anything
        for param_name, value in sound_state.items():
            self.sound_manager.update_pillar_setting(param_name, value) 

        # Send any sound state "reaction notes" to other pillars
        if self.mqtt_enabled:
            self.broadcast_notes_to_other_pillars(sound_state)

        # Tick at 15Hz instead of 30Hz to reduce overhead
        self.sound_manager.tick(time_delta=1/15.0)
        
        data = {
            "btn_press": current_btn_press,
            "sound_state": sound_state.to_json()
        }
        self.data_queue.put(data)

        self.loop_idx += 1

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="A script to parse host, port, and config file path.")
    parser.add_argument("--config", default="config/config.json", help="Path to the JSON config file.")
    parser.add_argument("--serial_port", default=None, help="Overrides the serial in the configuration")
    parser.add_argument("--frequency", default=5, type=int, help="Frequency of the controller loop")
    parser.add_argument("--hostname", default=None, type=str, help="The hostname if different from the base computer")
    parser.add_argument("--mqtt_broker_ip", default=None, type=str, help="The IP address of the MQTT Broker which every pillar connects to")
    parser.add_argument("--mqtt_mock", default=False, type=bool, help="Set this argument to mock the mqtt connection")
    args = parser.parse_args()
    print(args)

    # Get Hostname
    hostname = args.hostname if args.hostname is not None else socket.gethostname()
    print("HOSTNAME is ", hostname)

    # Read the JSON config file
    with open(args.config, 'r') as config_file:
        config = json.load(config_file)

    if hostname not in config["pillars"]:
        raise RuntimeError(f"This hostname {hostname} not present in configuration")

    if args.serial_port is not None:
        print("Reconfigured serial port to: ", args.serial_port)
        config["pillars"][hostname]["port"] = args.serial_port

    if args.serial_port is not None:
        config["mqtt"]["broker_ip"] = args.mqtt_broker_ip

    config["mqtt"]["mock"] = args.mqtt_mock

    # Create a Controller instance and pass the parsed values
    print("Intiialise and run Controller")
    controller = Controller(hostname, config)
    controller.start(args.frequency)
    # asyncio.get_event_loop().run_until_complete(controller.run(args.frequency))
    # asyncio.get_event_loop().run_forever()
