import socket
import pygame
import pickle
from math import cos, sin, radians
import argparse
import uuid
import numpy as np

import multiprocessing as mp

from scamp import Session

from player import Player
from pillar import MusicPillar, Pillar, MusicPillarManager

# Screen settings
WIDTH, HEIGHT = 800, 600

def scamp_session_manager(shared_state):
    man = MusicPillarManager()
    print("Started SCAMP Music Manager")
    while man.is_alive():
        man.update_pillar_state(shared_state["pillars"])
        man.update_player_state(shared_state["player"])
        man.play()

class GameClient:
    def __init__(self, ip="localhost", port=6000, name=None):
        print(f"Connecting to {ip}:{port}")
        self.server_address = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(0.1)

        self.id = uuid.uuid4() if name==None else name
        self.player = Player(self.id)
        
        self.game_state = None
        # self.music_pillars = None
        self.screen = None

        # self.session = Session()
        # self.session.tempo=60 # beats per minute
        # self.bps = self.session.tempo / 60

        self.manager = mp.Manager()
        self.shared_state = self.manager.dict({
            "player": self.player,
            "pillars": []
        })

        self.sound_proc = mp.Process(target=scamp_session_manager,
                                     args=(self.shared_state,))
        self.sound_proc.start()

        print("Waiting for game state...")

    def init(self):
        print("Game state received, initialising player", self.id)
        self.resize_window(*self.game_state["screen"])
        pygame.display.set_caption(f"Forest Client [{self.player.player_id}]")   
        w, h = self.screen.get_size()
        self.player.set_loc(w/2, h/2)
    
    def send_player_data(self):
        self.sock.sendto(pickle.dumps(self.player.__dict__), self.server_address)

    def receive_game_state(self):
        try:
            data, _ = self.sock.recvfrom(4096)
            self.game_state = pickle.loads(data)
            self.game_state["players"] = [Player(**d) for d in self.game_state["players"]]
            self.game_state["pillars"] = [Pillar(**d) for d in self.game_state["pillars"]]

            self.shared_state["player"] = self.player
            self.shared_state["pillars"] = self.game_state["pillars"]

            # if self.music_pillars is None:
            #     self.music_pillars = [MusicPillar(self.session)for p in self.game_state["pillars"]]

            # for mp, pillar in zip(self.music_pillars, self.game_state["pillars"]):
            #     mp.set_pillar(pillar)

        except socket.timeout as e:
            print("Socket timeout", e)
            pass
        
    def resize_window(self, width, height):
        if self.screen is None or self.screen.get_size() != (width, height):
            self.screen = pygame.display.set_mode((width, height))

    def draw_game_state(self):
        self.screen.fill((128, 128, 128))

        # Draw pillars
        for pillar in self.game_state["pillars"]:
            pillar.draw(self.screen)

        for player in self.game_state["players"]:
            player.draw(self.screen)

    def stop(self):
        self.sock.sendto(pickle.dumps("stop"), self.server_address)
        self.sock.close()

    def run(self):
        # Pygame initialization
        pygame.init()
        clock = pygame.time.Clock()

        while True:
            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

            # Update player movement
            self.player.update(keys)

            # Send player data to server
            self.send_player_data()

            # Receive game state from server
            prev_game_state = self.game_state
            self.receive_game_state()
            if prev_game_state is None and self.game_state is not None:
                self.init()

            if self.game_state and self.screen:
                # Render everything
                self.draw_game_state()

                pygame.display.flip()

            clock.tick(30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forest Game Client")
    parser.add_argument('--ip', default='localhost', help="Server IP address")
    parser.add_argument('--port', type=int, default=6000, help="Server port")
    args = parser.parse_args()

    client = GameClient(args.ip, args.port)
    try:
        client.run()
    except KeyboardInterrupt:
        client.stop()
