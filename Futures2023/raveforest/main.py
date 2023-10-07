import time
import atexit
import asyncio
import websockets
from functools import partial
import argparse
import json
import copy

from psonic import *

from pillar_hw_interface import Pillar
from MappingInterface import MappingInterface

class Controller():

    def __init__(self, config, ws_host, ws_port):
        self.websocket_url = (ws_host, ws_port)

        self.num_pillars = len(config["pillars"])
        self.pillars = {p["id"]: Pillar(p["id"], p["port"]) for p in config["pillars"]}

        self.mapping = MappingInterface(copy.deepcopy(config))

        self.state = 0

        self.websocket_server = websockets.serve(self.websocket_server_callback, *self.websocket_url)
        self.websocket_clients = set()

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
                if frontend_data == "Command to control StateMachine":
                    # Implement your command handling logic here
                    pass
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

        while self.running:

            start_time = time.time()
            
            # Your state machine logic here
            self.loop()

            self.state += 1

            # Update websocket clients
            await self.send_to_clients(f"State Data {self.state}")

            elapsed_time = time.time() - start_time
            sleep_interval = 1 / frequency - elapsed_time
            print(sleep_interval)
            if sleep_interval > 0:
                await asyncio.sleep(sleep_interval)

    def stop(self):
        self.running = False
        # if self.websocket_server:
        #     self.websocket_server.close()
        
    def loop(self):
        
        # Update status of pillars
        for p_id, p in self.pillars.items():
            p.read_from_serial()
        
            # Check if a button has been pressed
            current_btn_press = p.get_all_touch_status()
            print("current btn press:", current_btn_press)

            # Generate the lights and notes based on the current btn inputs
            lights, notes = self.mapping.generate_tubes(current_btn_press)

            print("lights", lights)
            
            # Send Lights
            p.send_all_light_change(lights)

            # Send Notes
            # sonicpi send notes
        
if __name__=="__main__":
    parser = argparse.ArgumentParser(description="A script to parse host, port, and config file path.")
    parser.add_argument("--host", default="127.0.0.1", help="The host to connect to.")
    parser.add_argument("--port", default="8080", type=int, help="The port to use.")
    parser.add_argument("--config", default="config/config.json", help="Path to the JSON config file.")
    parser.add_argument("--frequency", default=5, help="Frequency of the controller loop")
    parser.add_argument("--ws-host", default="localhost", help="The internal websocket URI")
    parser.add_argument("--ws-port", default="8765", help="The internal websocket URI")
    parser.add_argument("--gui", default=False, action="store_true", help="Whether to run the Dash GUI")

    args = parser.parse_args()
    print(args)

    # Read the JSON config file
    with open(args.config, 'r') as config_file:
        config = json.load(config_file)

    # Create a Controller instance and pass the parsed values
    print("Intiialise and run Controller")
    controller = Controller(config, args.ws_host, args.ws_port)
    asyncio.get_event_loop().run_until_complete(controller.run(args.frequency))
    asyncio.get_event_loop().run_forever()

