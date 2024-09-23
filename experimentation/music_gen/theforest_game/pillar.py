import pygame
import math
import random
from enum import Enum

import music
from mingus.core import notes, scales
from mingus.containers import NoteContainer

pygame.font.init()
font = pygame.font.SysFont(None, 24)
font2 = pygame.font.SysFont(None, 19)

class NODE_FUNCTION(Enum):
    SCALE_TYPE=1
    SCALE_KEY=2
    INSTRUMENT=3
    TEMPO=4

SCALE_TYPES = {
    "blues": music.BluesScale,
    "mpentatonic": music.MinorPentatonic,
    "pentatonic": music.Pentatonic,
    "ionian": scales.Ionian,
    "minor": scales.HarmonicMinor
}

INSTRUMENTS = [
    "trumpet",
    "brass",
    "piano",
    "strings",
    "oboe"
]
  

class MusicPillar():

    def __init__(self, session):
        self.session = session

        self.instrument_name = None
        self.instrument = None
        self.scale = None

        self.note_numbers = []

    def set_pillar(self, pillar):
        self.pillar = pillar

        if pillar.scale != self.scale:
            self.scale = pillar.scale
            self.set_music_seq()

        if pillar.instrument != self.instrument_name:
            if self.instrument_name is not None:
                current_instruments = self.session.instruments
                idx = list(current_instruments).index(self.instrument_name)
                self.session.pop_instrument(idx)
            self.instrument = self.session.new_part(pillar.instrument)
            self.instrument_name = pillar.instrument        

    def set_music_seq(self):
        scale = SCALE_TYPES[self.scale](self.pillar.key)

        # Note containers 
        scale_asc = scale.ascending()
        note_container = NoteContainer()
        note_container.add_notes(scale_asc)
        self.note_numbers = [int(n) for n in note_container]
    
    def play_notes(self, instrument, volume):
        for n in self.note_numbers:
            instrument.play_note(n, random.random(), volume)

    def play(self, volume):
        # self.session.fork(self.play_notes, args=[self.instrument, 0.5])
        self.instrument.play_note(random.choice(self.note_numbers), random.random(), 0.5, blocking=False)


class Pillar:
    def __init__(self, id, x, y, size=50, **kwargs):
        self.id = id
        self.x = x
        self.y = y
        self.size = size  # Radius of the pillar
        self.nodes = []
        if 'nodes' in kwargs:
            self.nodes = kwargs['nodes']  # Allow loading nodes from kwargs
        else:
            self.generate_nodes()

        self.key = kwargs["key"] if "key" in kwargs else notes.int_to_note(random.randint(0, 11))
        self.instrument = kwargs["instrument"] if "instrument" in kwargs else random.choice(INSTRUMENTS)
        self.scale = kwargs["scale"] if "scale" in kwargs else random.choice(list(SCALE_TYPES.keys()))
        self.tempo = kwargs["tempo"] if "tempo" in kwargs else 60

    def generate_nodes(self):
        num_funcs = len(NODE_FUNCTION)
        for i in range(num_funcs):
            angle = math.radians(i * (360 / num_funcs))
            node_x = self.x + self.size * math.cos(angle)
            node_y = self.y + self.size * math.sin(angle)
            self.nodes.append({
                "x": node_x, "y": node_y,
                "active": False, "function": NODE_FUNCTION(i+1)
            })

    def draw(self, surface):
        pygame.draw.circle(surface, (0, 255, 0), (self.x, self.y), radius=self.size)
        # Render the player ID near the player sprite
        label = font.render(str(self.id), True, (255, 255, 255))  # White text
        surface.blit(label, (self.x, self.y))  # Adjust label position

        # Draw nodes
        for i, node in enumerate(self.nodes):
            # Change node color based on active state
            node_color = (0, 125, 125) if node['active'] else (255, 255, 255)
            pygame.draw.circle(surface, node_color, (int(node["x"]), int(node["y"])), 10)

            label = font.render(str(f"n{i}"), True, (0, 0, 255)) 
            surface.blit(label, (node["x"], node["y"]))  # Adjust label position

    def distance(self, player) -> float:
        return math.hypot(self.x - player.x, self.y - player.y)

    def activate_node(self, player):
        """
        Check if the player is close to the pillar and facing a node, then activate that node.
        """
        # Find the node the player is facing based on player angle
        for i, node in enumerate(self.nodes):
            
            # If Key is pressed check distances and find minimum
            if player.interacting:
                # Calculate the distance between the player and the pillar
                distance = math.hypot(node["x"] - player.x, node["y"]- player.y)
                # print(f"Distance to {self.id}-n{i} is {distance}")
                if distance < player.selection_radius+5:
                    if not node["active"]:
                        node["active"] = True
                    return i

            elif node["active"]:
                    node["active"] = False

        return -1  # No interaction if not facing a node

    @staticmethod
    def generate_pillars_grid(num_pillars, pillar_size, screen_width, screen_height):
        """
        Generate pillars in a grid formation, spaced 3*size apart.
        """
        # Calculate the number of pillars in each direction
        grid_size = math.ceil(math.sqrt(num_pillars))  # Approximate grid size (rows and columns)
        
        # Distance between pillars (at least 3 * pillar_size to maintain space between them)
        spacing = 4 * pillar_size
        
        # Calculate the center of the screen
        center_x = screen_width // 2
        center_y = screen_height // 2
        
        # Calculate the offset to position the grid around the center of the screen
        total_grid_width = (grid_size - 1) * spacing
        total_grid_height = (grid_size - 1) * spacing
        
        start_x = center_x - total_grid_width // 2
        start_y = center_y - total_grid_height // 2
        
        pillars = []
        
        # Generate the grid of pillars
        for i in range(grid_size):
            for j in range(grid_size):
                # Ensure we don't generate more pillars than needed
                if len(pillars) >= num_pillars:
                    break
                
                # Calculate pillar position
                x = start_x + j * spacing
                y = start_y + i * spacing
                
                # Create a new Pillar and add to the list
                pillar = Pillar(id=i*grid_size+j, x=x, y=y, size=pillar_size)
                pillars.append(pillar)
        
        return pillars

    @staticmethod
    def generate_pillars_random(num_pillars, size, screen_width, screen_height):
        """
        Generate pillars randomly, ensuring no pillars are closer than 3*size.
        """
        import random
        pillars = []
        min_distance = 3 * size

        while len(pillars) < num_pillars:
            x = random.randint(size, screen_width - size)
            y = random.randint(size, screen_height - size)
            too_close = False

            for pillar in pillars:
                distance = math.sqrt((x - pillar.x) ** 2 + (y - pillar.y) ** 2)
                if distance < min_distance:
                    too_close = True
                    break

            if not too_close:
                pillars.append(Pillar(len(pillars), x, y, size=size))

        return pillars
 