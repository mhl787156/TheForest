import pygame
import math

pygame.font.init()
font = pygame.font.SysFont(None, 24)
font2 = pygame.font.SysFont(None, 19)

class Pillar:
    def __init__(self, id, x, y, num_nodes=6, size=50, **kwargs):
        self.id = id
        self.x = x
        self.y = y
        self.size = size  # Radius of the pillar
        self.nodes = []
        if 'nodes' in kwargs:
            self.nodes = kwargs['nodes']  # Allow loading nodes from kwargs
        else:
            self.generate_nodes(num_nodes)

    def generate_nodes(self, num_nodes):
        for i in range(num_nodes):
            angle = math.radians(i * (360 / num_nodes))
            node_x = self.x + self.size * math.cos(angle)
            node_y = self.y + self.size * math.sin(angle)
            self.nodes.append({
                "x": node_x, "y": node_y,
                "active": False
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