import time
import atexit
import asyncio
import websockets
from functools import partial
import argparse
import json
import copy
from datetime import datetime

from pillar_hw_interface import Pillar
from MappingInterface import MappingInterface
from sonic import SoundManager, setup_psonic

import csv

class Controller():

    def __init__(self, config, ws_host, ws_port):
        self.websocket_url = (ws_host, ws_port)

        self.pillar = Pillar(**config) 
        print(f"Pillar:", vars(self.pillar))
        


        self.mapping = MappingInterface(copy.deepcopy(config))
        #self.savefolder_name = f"raveforest_data_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.csv"

        print(f"Mapping Interface: {self.mapping.__dict__}")
        print(f"Pillar Interface: {self.pillar.__dict__}")
        self.sound_manager = SoundManager(self.mapping)

        self.current_states = self.pillar

        self.websocket_server = websockets.serve(self.websocket_server_callback, *self.websocket_url)
        self.websocket_clients = set()

        self.loop_idx = 0

        self.running = True
        atexit.register(self.stop)

    async def run(self, frequency):
        print(f"Starting Websocket server on ws://{self.websocket_url[0]}:{self.websocket_url[1]}")
        async with self.websocket_server:
            await self.start(frequency)  

    async def websocket_server_callback(self, websocket, path):
        # Handle WebSocket connections and messages from Dash clients
        self.websocket_clients.add(websocket)
        try:
            while True:
                frontend_data = await websocket.recv()
                print("Received data from frontend:", frontend_data)

                # Process commands received from Dash and control the state machine
                data = json.loads(frontend_data)
                if "serial_port" in data:
                    #for p_id, serial_port in data["serial_port"].items():
                    self.pillar.restart_serial(data["pillar"]["serial_port"])
                
                if "touch" in data:
                    #for p_id, touch in data["touch"].items():
                    self.pillar.set_touch_status(data["touch"])
                        
                # Set parameters for the sound manager
                #  ["amp", "note-pitch", "synth", "bpm", "pan", "envelope"]
                for name, value in data.items():
                    if name in ["amp", "note-pitch", "synth", "bpm", "pan", "envelope"]:
                        #for p_id, v in value.items():
                        self.sound_manager.update_pillar_setting(name, value)
                
                        
                #if "bpm" in data:
                #    self.sound_manager.set_bpm(data["bpm"])
                #if "mapping_id" in data:
                #    for p_id,p in self.pillars.items():
                #        p.mapping.mapping_id = data["mapping_id"]
                #if "amp" in data:
                #    for p_id, amp in data["amp"].items():
                #        self.sound_manager.set_amp(int(p_id), float(amp))

                #if "synth" in data:
                #    for p_id, synth in data["synth"].items():
                #        self.sound_manager.set_synth(int(p_id), synth)
                

        except websockets.exceptions.ConnectionClosedOK:
            pass
        except websockets.exceptions.ConnectionClosedError:
            pass
        finally:
            # Remove WebSocket client when the connection is closed
            self.websocket_clients.remove(websocket)

    async def send_to_clients(self, message):
        # Send data to all connected Dash clients
        for websocket in self.websocket_clients:
            await websocket.send(message)

    async def start(self, frequency):
        """Starts the main control loop

        Args:
            frequency (_type_): _description_
        """
        index = 0

        while self.running:

            start_time = time.perf_counter()

            # Your state machine logic here
            self.loop()
            print(self.pillar)

            # Update websocket clients
            # Get pillar data -- this has to be change, it was the easy solution for me
            pillar_data = {
                            'serial_read_rate': self.pillar.serial_read_rate,
                            'num_tubes': self.pillar.num_tubes,
                            'num_touch_sensors': self.pillar.num_touch_sensors,
                            'touch_status': self.pillar.touch_status,
                            'previous_received_status': self.pillar.previous_received_status,
                            'light_status': self.pillar.light_status,
                            'serial_status': self.pillar.serial_status,
                            'current_state': self.current_states
                            }
            state_dicts = {
                "time": datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
                "pillar": pillar_data,
                "current_state": self.current_states,
                #"bpm": self.sound_manager.get_bpm(),
                #"mapping_id": 1,
                #"synths": self.sound_manager.get_synths(),
                #"amp": self.sound_manager.get_amps(),
                #"notes": self.sound_manager.get_all_notes()
            }
            print("state_dicts:", state_dicts)
            await self.send_to_clients(json.dumps(state_dicts))

            elapsed_time = time.perf_counter() - start_time
            sleep_interval = 1 / frequency - elapsed_time
            if sleep_interval > 0:
                await asyncio.sleep(sleep_interval)
            index += 1
            if index % 5 == 0:
                pass
                #with open(self.savefolder_name, mode='a') as csv_file:
                #    fields =["time", "num_pillars","pillars","current_state","bpm","synths","amp","notes"] #'mapping_id',
                #    writer = csv.DictWriter(csv_file,fieldnames=fields)
                #    writer.writerow(state_dicts)

    def stop(self):
        self.running = False

    def loop(self):
    # Update status of the pillar

        p = self.pillar
        
        print(f"------read pillar-------")
        p.read_from_serial()

        # Check if a button has been pressed
        current_btn_press = p.get_all_touch_status()
        print("current btn press:", current_btn_press)

        # Generate the lights and notes based on the current btn inputs
        lights, params = self.mapping.generate_tubes(current_btn_press)
        print("lights:", lights)
        print("params:", params)
        

        # Send Lights On The Beat
        # def temp_func():
        # print(f"Current Lights {p.get_all_light_status()}")
        print(f"Sending Lights {lights}")
        p.send_all_light_change(lights)
        # self.sound_manager.run_on_next_beat(temp_func, force_unique_id=(5678 + self.loop_idx))

        # Send Notes, sound manager manages on the beat
        #print("Setting params", params)
        for param_name, value in params.items():
            #print(f"Setting {param_name} to {value}")
            self.sound_manager.update_pillar_setting(param_name, value) 

            # Set current state for sending
            self.current_states = dict(lights=lights, params=params)
            print("current states:", self.current_states)

        self.loop_idx += 1

if __name__=="__main__":
    parser = argparse.ArgumentParser(description="A script to parse host, port, and config file path.")
    parser.add_argument("--host", default="127.0.0.1", help="The host to connect to.")
    parser.add_argument("--port", default="8080", type=int, help="The port to use.")
    parser.add_argument("--config", default="config/config.json", help="Path to the JSON config file.")
    parser.add_argument("--frequency", default=5, type=int, help="Frequency of the controller loop")
    parser.add_argument("--ws-host", default="localhost", help="The internal websocket URI")
    parser.add_argument("--ws-port", default="8765", help="The internal websocket URI")
    parser.add_argument("--gui", default=True, action="store_true", help="Whether to run the Dash GUI")

    args = parser.parse_args()
    print(args)

    # Read the JSON config file
    with open(args.config, 'r') as config_file:
        config = json.load(config_file)
        


    # Setup Python-Sonic connection
    setup_psonic(config["sonic-pi-ip"], config["sonic-pi-config-file"])

    # Create a Controller instance and pass the parsed values
    print("Intiialise and run Controller")
    controller = Controller(config, args.ws_host, args.ws_port)
    # controller.start(args.frequency)
    asyncio.get_event_loop().run_until_complete(controller.run(args.frequency))
    # asyncio.get_event_loop().run_forever()
