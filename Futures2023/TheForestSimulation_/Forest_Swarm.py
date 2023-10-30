
from Forest_Agent import *
import matplotlib
from matplotlib.colors import hsv_to_rgb
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
from matplotlib.patches import Circle
from matplotlib.collections import PatchCollection

import copy



class Forest_Swarm:

    def __init__(self,num_agents,num_tubes,num_pillars):
        self.num_agents=num_agents
        self.num_tubes = num_tubes
        self.num_pillars = num_pillars
        self.agents = []
        self.points =[]
        self.lights_history=[]
        self.current_lights=[]
        for i in range(self.num_pillars):
            pillar=[]
            for j in range(self.num_tubes):
                pillar.append(random.choice([40,90,160,255]))
            self.current_lights.append(pillar)

    def simulate(self,time_steps):
        self.lights_history.append(copy.deepcopy(self.current_lights))
        for i in range(time_steps):
            for j in range(self.num_agents):
                action = self.agents[j].call(self.current_lights)
                if len(action)>0:
                    self.current_lights=action
            self.lights_history.append(copy.deepcopy(self.current_lights))
            print(self.current_lights)


    def generate_coords_tubes(self, radius):

        # Calculate the angles at which the points should be placed
        angles = np.linspace(0, 2 * np.pi, self.num_tubes, endpoint=False)

        # Calculate the x and y coordinates of the points on the circle
        x = radius * np.cos(angles)
        y = radius * np.sin(angles)

        self.points = [[x[i], y[i]] for i in range(self.num_tubes)]

        # Move (0,0) to front if central tube is first in array


    def animation(self):
        fig = plt.figure(figsize=(10, 10), dpi=100, facecolor='w', edgecolor='k')
        ax1 = fig.add_subplot(121)
        ax1.set_title('Pillar1')

        ax2 = fig.add_subplot(122)
        ax2.set_title('Pillar2')
        label1 = ax1.text(-3.5, 3.9, " ", ha='center', va='center', fontsize=12, color="black")

        dim = 4
        ax1.set_xlim((-dim, dim))
        ax1.set_ylim((-dim, dim))
        ax2.set_xlim((-dim, dim))
        ax2.set_ylim((-dim, dim))
        patches = []

        for i in(range(self.num_tubes)):
            circle = Circle((self.points[i][0], self.points[i][1]), 1)
            ax1.text(self.points[i][0], self.points[i][1], str(i), ha='center', va='center', fontsize=12, color="gray")
            ax2.text(self.points[i][0], self.points[i][1], str(i), ha='center', va='center', fontsize=12, color="gray")
            patches.append(circle)

        # add these circles to a collection
        pillar1_tubes = PatchCollection(patches, cmap=matplotlib.colormaps.get_cmap('hsv'), alpha=0.4)
        ax1.add_collection(pillar1_tubes)
        pillar2_tubes = PatchCollection(patches, cmap=matplotlib.colormaps.get_cmap('hsv'), alpha=0.4)
        ax2.add_collection(pillar2_tubes)
        ax1.axis("off")
        ax2.axis("off")


        def animate(i):
              label1.set_text('Time: (%d)' % (i))
              colors = 100 * np.random.rand(len(patches))  # random index to color map
              colors1=[]
              colors2 = []
              for c in(range(self.num_tubes)):
                  colors1.append(hsv_to_rgb([((self.lights_history[i][0][c]) / 255), 1,0.8 ]))
                  colors2.append(hsv_to_rgb([((self.lights_history[i][1][c]) / 255), 1,0.8 ]))

              pillar1_tubes.set_color(colors1)
              pillar2_tubes.set_color(colors2)


        anim = animation.FuncAnimation(fig, animate,frames=50, interval=1500, blit=False)
        anim
        plt.show()

    def save_data(self):
        lights_hist = np.array(self.lights_history).reshape(np.array(self.lights_history).shape[0], -1)
        np.savetxt('data.csv', lights_hist, delimiter=',')


