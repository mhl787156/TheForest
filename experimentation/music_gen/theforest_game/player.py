import pygame
import pickle
from math import cos, sin, radians
import random

pygame.font.init()
font = pygame.font.SysFont(None, 24)

class Player:
    def __init__(self, player_id, x=0, y=0, angle=0, **kwargs):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 5
        self.size = 20
        self.player_id = player_id
        self.interacting = kwargs["interacting"] if "interacting" in kwargs else False

        self.selection_radius = 20

        if "colour" not in kwargs:
            self.colour = [random.randint(0, 255) for _ in range(3) ]
        else:
            self.colour = kwargs["colour"]

    def set_loc(self, x, y):
        self.x = x
        self.y = y

    def update(self, keys):
        # WASD movement
        if keys[pygame.K_w]:
            self.x += self.speed * cos(radians(self.angle))
            self.y += self.speed * sin(radians(self.angle))
        if keys[pygame.K_s]:
            self.x -= self.speed * cos(radians(self.angle))
            self.y -= self.speed * sin(radians(self.angle))

        if keys[pygame.K_d]:
            self.x -= self.speed * sin(radians(self.angle))
            self.y += self.speed * cos(radians(self.angle))
        if keys[pygame.K_a]:
            self.x += self.speed * sin(radians(self.angle))
            self.y -= self.speed * cos(radians(self.angle))

        # Rotate with A and D
        if keys[pygame.K_q]:
            self.angle = (self.angle - 5) % 360
        if keys[pygame.K_e]:
            self.angle = (self.angle + 5) % 360

        self.interacting = keys[pygame.K_SPACE]

    def draw(self, surface):
        # Draw the player as a simple rectangle
        # pygame.draw.rect(surface, self.colour, (self.x, self.y, 20, 20))

        # Calculate the three points of the triangle based on the player's angle
        point1 = (
            self.x + self.size * cos(radians(self.angle)),
            self.y + self.size * sin(radians(self.angle))
        )
        point2 = (
            self.x + self.size/2.0 * cos(radians(self.angle + 120)),
            self.y + self.size/2.0 * sin(radians(self.angle + 120))
        )
        point3 = (
            self.x + self.size/2.0 * cos(radians(self.angle + 240)),
            self.y + self.size/2.0 * sin(radians(self.angle + 240))
        )
        
        # Draw the triangle using the calculated points
        pygame.draw.polygon(surface, self.colour, [point1, point2, point3])

        pygame.draw.circle(surface, (50, 50, 50), (self.x, self.y), radius=self.selection_radius, width=1)

        # Render the player ID near the player sprite
        label = font.render(str(self.player_id)[:4], True, (255, 255, 255))  # White text
        surface.blit(label, (self.x - self.size, self.y - self.size - 20))  # Adjust label position

