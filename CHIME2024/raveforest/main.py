import time
import atexit
import asyncio
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from functools import partial
import argparse
import json
import copy
from datetime import datetime
import os

from pillar_hw_interface import Pillar
from MappingInterface import MappingInterface
from sound_manager import SoundManager

import csv


# Constants for parameter names
AMP = "amp"
NOTE_PITCH = "note-pitch"
SYNTH = "synth"
BPM = "bpm"
PAN = "pan"
ENVELOPE = "envelope"
PARAMS = [AMP, NOTE_PITCH, SYNTH, BPM, PAN, ENVELOPE]

class Controller():

    def __init__(self, hostname, config):

        if hostname not in config["pillars"]:
            raise RuntimeError(f"This hostname {hostname} not present in configuration")

        self.num_pillars = len(config["pillars"])        
        self.pillar_config = config["pillars"][hostname]
        self.pillar_manager = Pillar(**self.pillar_config)
        self.sound_manager = SoundManager(hostname)
        self.loop_idx = 0

        # self.running = True
        # atexit.register(self.stop)

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

    def loop(self):

        self.pillar_manager.read_from_serial()

        current_btn_press = self.pillar_manager.get_all_touch_status()
        print("current btn press:", current_btn_press)

        # Generate the lights and notes based on the current btn inputs
        lights, params = self.pillar_manager.mapping.generate_tubes(current_btn_press)
        print("lights:", lights)
        #print("params:", params)

        print(f"Sending Lights {self.pillar_manager.id}: {lights}")
        self.pillar_manager.send_all_light_change(lights)

        print("Setting params", params)
        for param_name, value in params.items():
            self.sound_manager.update_pillar_setting(self.pillar_manager.id, param_name, value) 

        self.loop_idx += 1

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="A script to parse host, port, and config file path.")
    parser.add_argument("--config", default="config/config.json", help="Path to the JSON config file.")
    parser.add_argument("--frequency", default=5, type=int, help="Frequency of the controller loop")
    parser.add_argument("--hostname", default=None, type=str, help="The hostname if different from the base computer")

    args = parser.parse_args()
    print(args)

    # Get Hostname
    hostname = args.hostname if args.hostname is None else os.getnev("HOSTNAME")
        

    # Read the JSON config file
    with open(args.config, 'r') as config_file:
        config = json.load(config_file)
        

    # Create a Controller instance and pass the parsed values
    print("Intiialise and run Controller")
    controller = Controller(hostname, config)
    controller.start(args.frequency)
    # asyncio.get_event_loop().run_until_complete(controller.run(args.frequency))
    # asyncio.get_event_loop().run_forever()
