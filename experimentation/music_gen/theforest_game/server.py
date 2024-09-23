import socket
import pickle
import time
import argparse
from threading import Thread

from pillar import Pillar
from player import Player

class GameServer:
    def __init__(self, ip="localhost", port=6000, num_pillars=10, pillar_generation_method='grid', screen_width=800, screen_height=600):
        self.server_address = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.server_address)
        self.players = {}
        self.pillars = []  # Pillar states
        self.running = True
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.num_pillars = num_pillars
        self.pillar_generation_method = pillar_generation_method
        self.init_pillars()

        self.loop_num = 0

    def init_pillars(self):
        """
        Initialize the pillars based on the generation method.
        """
        size = 40  # Size of each pillar

        if self.pillar_generation_method == 'grid':
            self.pillars = Pillar.generate_pillars_grid(self.num_pillars, size, self.screen_width, self.screen_height)
        elif self.pillar_generation_method == 'random':
            self.pillars = Pillar.generate_pillars_random(self.num_pillars, size, self.screen_width, self.screen_height)
        else:
            raise ValueError("Unknown pillar generation method: Use 'grid' or 'random'")
        
    def check_pillar_interactions(self, player):
        for pillar in self.pillars:
            pillar.activate_node(player)

    def handle_client(self, data, addr):
        """
        Handle incoming player data (position and interaction) and update state.
        """
        
        player_data = pickle.loads(data)

        if player_data == "stop":
            print(f"Removing Connection to {addr}: {self.players[addr].player_id}")
            del self.players[addr]
        else:
            player = Player(**player_data)
            if addr not in self.players:
                print(f"Received New Connection from {addr}: {player.player_id}")
            self.players[addr] = player
            self.check_pillar_interactions(player)
        
        self.loop_num+=1

    def broadcast_state(self):
        """
        Send the current game state (players and pillars) to all clients.
        """
        while self.running:
            game_state = {
                'players': [p.__dict__ for _, p in self.players.items()],
                'pillars': [q.__dict__ for q in self.pillars], #[(pillar.x, pillar.y, pillar.size) for pillar in self.pillars],
                'screen': [self.screen_width, self.screen_height]
            }
            for addr in self.players.keys():
                self.sock.sendto(pickle.dumps(game_state), addr)
            time.sleep(0.05)  # Broadcast every 50 ms (20 FPS)

    def run(self):
        """
        Main loop to listen for incoming player data and broadcast game state.
        """
        print(f"Server started on {self.server_address}")
        broadcast_thread = Thread(target=self.broadcast_state)
        broadcast_thread.start()

        while self.running:
            data, addr = self.sock.recvfrom(1024)
            self.handle_client(data, addr)

    def stop(self):
        self.running = False
        self.sock.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Forest Game Server")
    parser.add_argument('-n', '--num_pillars', type=int, default=10, help="Number of pillars to generate")
    parser.add_argument('-m', '--pillar_method', choices=['grid', 'random'], default='grid', help="Pillar generation method: 'grid' or 'random'")
    parser.add_argument('--ip', default='localhost', help="Server IP address")
    parser.add_argument('--port', type=int, default=6000, help="Server port")
    parser.add_argument('--screen_width', type=int, default=800, help="Game world width")
    parser.add_argument('--screen_height', type=int, default=600, help="Game world height")

    args = parser.parse_args()

    server = GameServer(
        ip=args.ip,
        port=args.port,
        num_pillars=args.num_pillars,
        pillar_generation_method=args.pillar_method,
        screen_width=args.screen_width,
        screen_height=args.screen_height
    )

    try:
        server.run()
    except KeyboardInterrupt:
        print("Server shutting down...")
        server.stop()
