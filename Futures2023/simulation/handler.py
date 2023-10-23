import asyncio
import websockets
import sys
import argparse
import json
import time

from agents import *

class SimulationHandler():

    def __init__(self, ws_host, ws_port, num_tubes_per_pillar, total_tubes, simulation_config):
        self.num_tubes_per_pillar = num_tubes_per_pillar
        self.num_tubes = total_tubes
        self.num_pillars = int(self.num_tubes // self.num_tubes_per_pillar)
        self.server_url = f"ws://{ws_host}:{ws_port}"

        self.websocket = None

        self.agents = []

    def start(self):
        asyncio.get_event_loop().run_until_complete(self.connect())
    
        # Start a task to read data in the background
        asyncio.get_event_loop().run_until_complete(self.read_data())

        # asyncio.get_event_loop().run_until_complete(self.close())
    
    def add_agent(self, agent_type:str, **kwargs):
        """Adds an agent to the list based on its name

        Args:
            agent_type (str): This is the name of the agent class, e.g. `RandomAgent`
            **kwargs: Other keyword arguments to be passed to an agent
        """
        cls = getattr(sys.modules[__name__], agent_type)
        if cls:
            agent = cls(self.num_tubes, **kwargs)
            if isinstance(agent, Agent):
                self.agents.append(agent)
                print(f"Agent {agent_type} added with kwargs {kwargs}")
                return
        print(f"Agent Type {agent_type} not recognised")

    async def connect(self):
        for _ in range(5):
            try:
                self.websocket = await websockets.connect(self.server_url)
                print("Connected to WebSocket server.")
            except Exception as e:
                print(f"Failed to connect: {e}")
                time.sleep(1)

    async def read_data(self):
        if self.websocket is None:
            print("WebSocket connection not established.")
            return

        try:
            while True:
                data = await self.websocket.recv()
                # print(f"Received data: {data}")

                # For reference
                # state_dicts = {
                #     "num_pillars": self.num_pillars,
                #     "pillars": {pid: p.to_dict() for pid, p in self.pillars.items()},
                #     "current_state": self.current_states,
                #     "bpm": self.sound_manager.get_bpm(),
                #     "mapping_id": self.mapping.mapping_id,
                #     "synths": self.sound_manager.get_synths(),
                #     "amp": self.sound_manager.get_amps(),
                #     "notes": self.sound_manager.get_all_notes()
                # }

                state_dict = json.loads(data)

                light_status = {
                    p_id: [False for _ in range(self.num_tubes_per_pillar)] 
                    for p_id in range(self.num_pillars)
                }
                active = False
                for agent in self.agents:
                    tube_num = agent.call(state_dict)

                    if tube_num > -1:
                        p_id = tube_num // self.num_tubes_per_pillar
                        light_status[p_id][tube_num] = True
                        active = True
                
                if active:
                    await self.send_data({"touch": light_status})
                    
        except websockets.ConnectionClosed:
            print("WebSocket connection closed.")

    async def send_data(self, data):
        if self.websocket is None:
            print("WebSocket connection not established.")
            return

        try:
            await self.websocket.send(data)
            print(f"Sent data: {data}")
        except websockets.ConnectionClosed:
            print("WebSocket connection closed.")

    async def close(self):
        if self.websocket is not None:
            await self.websocket.close()
            print("WebSocket connection closed.")


if __name__=="__main__":
    parser = argparse.ArgumentParser(description="A script to parse host, port, and config file path.")
    parser.add_argument("--host", default="127.0.0.1", help="The host to connect to.")
    parser.add_argument("--port", default="8080", type=int, help="The port to use.")
    parser.add_argument("--debug", default=False, action="store_true", help="Whether to run the Dash GUI")

    parser.add_argument("--ws-host", default="localhost", help="The internal websocket URI")
    parser.add_argument("--ws-port", default="8765", help="The internal websocket URI")

    parser.add_argument("--sim-config", default="config/sim_config.json", help="Path to the simulation configuration file")

    args = parser.parse_args()

        # Read the JSON config file
    with open(args.sim_config, 'r') as config_file:
        config = json.load(config_file)

    print("Running")

    s = SimulationHandler(args.ws_host, args.ws_port, 7, 14, config)

    for agent in config["agents"]:
        print(f"Adding agent {agent}")
        s.add_agent(agent["type"], **agent["kwargs"])
    
    s.start()



