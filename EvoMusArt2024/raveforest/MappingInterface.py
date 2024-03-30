import json
import random
import sys
from typing import Tuple
import numpy as np
from psonic import synthesizers
from inspect import getmembers
import json

import matplotlib.pyplot as plt
from matplotlib.colors import rgb_to_hsv

class SoundState(object):
    def __init__(self, random_init=True, amp=0, synth="saw", note=0):
        self.available_synths = [(a, d) for (a, d) in getmembers(synthesizers) if isinstance(d, synthesizers.Synth)]

        self.amp = random.randint(0, 255) if random_init else amp

        if random_init:
            self.synth_id = random.randint(0, len(self.available_synths))

        self.synth = self.available_synths[self.synth_id]

        self.note = random.randint(0, 255) if random_init else note

    def change_amp(self, delta:int) -> float:
        # Changes amp based on delta and returns the percentage between min and max
        self.amp = (self.amp + delta) % 256
        return self.amp / 256

    def change_note(self, delta:int) -> float:
        # Changes note based on delta and returns the percentage between min and max
        self.note = (self.note + delta) % 256
        return self.note / 256

    def change_synth(self, delta:int) -> float:
        # Changes synth based on delta and returns the percentage between min and max
        self.synth_id = (self.synth_id + delta) % len(self.available_synths)
        self.synth = self.available_synths[self.synth_id]
        return self.synth_id / len(self.available_synths)

    def __repr__(self) -> str:
        return f"SoundState[NOTE:{self.note},AMP:{self.amp},SYNTH:{self.synth[0]}]"
    
    def __json__(self):
        return dict(note=self.note, synth=f"{self.synth[0]}", amp=self.amp)

class LightState(object):
    def __init__(self, num_tubes, random_init=True, lights=None):
        if random_init:
            self.lights = [
                tuple(random.randint(0, 255) for _ in range(2))
                for _ in range(num_tubes)
            ]
        else:
            self.lights = lights

    def __getitem__(self, indices):
        if not isinstance(indices, tuple):
            indices = tuple(indices)
        return [self.lights[i] for i in indices]

    def __setitem__(self, key, newvalue):
        self.lights[key] = newvalue

    def __iter__(self):
        return self.lights.__iter__()

    def __next__(self):
        return self.lights.__next__()

    def __repr__(self) -> str:
        return f"LightState[{self.lights}]"

    def __json__(self) -> str:
        return self.lights

class Pillar_Mapper_Base(object):

    def __init__(self, pillar_cfg):
        """Base Class for any mapping function for a single pillar

        Args:
            pillar_cfg (Dict): The configuration file for the pillar
        """

        self.num_tubes = pillar_cfg["num_tubes"]

        self.sound_state: SoundState = SoundState(random_init=True)
        self.light_state: LightState = LightState(self.num_tubes, random_init=True)
        self.state_array = [False for _ in range(self.num_tubes)]

    def update_pillar(self, state_array) -> Tuple[SoundState, LightState]:

        # Update internal state
        self.__interaction_update_sound_light(self.state_array, state_array)

        self.state_array = state_array

        return self.sound_state, self.light_state

    # This should be implemented in child classes
    def __interaction_update_sound_light(self, old_state, new_state):
        # This function takes the tube_id and the current tube states (sound and light)
        # It changes the amplitude, synth and note and color for this pillar
        # Internally changes self.sound_state and self.light_state
        pass

# Implementation of Pillar Mapper Base to use
class RotationMapper(Pillar_Mapper_Base):
    def __init__(self, pillar_cfg):
        super().__init__(pillar_cfg)

        self.tube_allocation = pillar_cfg["tube_allocation"]

        # Create a colormap from red to blue scaled between 0 and 255
        self.cmap = plt.get_cmap('coolwarm')
        # self.hsv_values = rgb_to_hsv(self.colormap[:, :3])

    # This should be implemented in child classes
    def __interaction_update_sound_light(self, old_state, new_state):
        # This function takes the tube_id and the current tube states (sound and light)
        # It changes the amplitude, synth and note and color for this pillar
        # Internally changes self.sound_state and self.light_state

        for tube_id, (active, tube_allocation) in enumerate(zip(new_state, self.tube_allocation)):
            if active:
                delta = 1 if '+' in tube_allocation else -1
                if 't' in tube_allocation:
                    value = self.sound_state.change_synth(delta)
                elif 'a' in tube_allocation:
                    value = self.sound_state.change_synth(delta)
                elif 'p' in tube_allocation:
                    value = self.sound_state.change_note(delta)

                self.light_state[tube_id] = tuple(rgb_to_hsv(self.cmap(value)))


def generate_mapping_interface(cfg_pillar) -> Pillar_Mapper_Base:
    """Generator Function which you can call which reads the config
    And assigns the correct mapping class based on the configuration file "map"

    Args:
        pillar_id (int): The Pillar Number
        cfg (Dict): The configuration file for the pillars

    Returns:
        Pillar_Mapper_Base: A Child class of Pillar_Mappper_Base which is specified in the 'map' parameter of the configuration file if it exists.
    """
    # Map the name of the mapping method to the Class
    targetClass = getattr(sys.modules[__name__], cfg_pillar['map'])
    return targetClass(cfg_pillar)

###################################################################################

# Deprecated v1
class MappingInterface(object):
    Active_Tubes = [0,0,0,0,0,0,0]
    Init_Tubes_Notes = []
    Init_Tubes_Colors = [[]]  # first item in hue , second item is the value
    Tubes_Notes = []
    Tubes_Colors = [[]] # first item in hue , second item is the value
    notes_to_color = True
    mapping_id =1

    def __init__(self, cfg):
        self.Init_Tubes_Notes= [47, 49, 51, 52, 54, 56, 58] #cfg['notes']
        self.Init_Tubes_Colors = [
                                    [0, 0],
                                    [0, 200],
                                    [0, 200],
                                    [0, 200],
                                    [0, 200],
                                    [0, 200],
                                    [0, 200]
                                ] #cfg['colors']
        self.Tubes_Notes = self.Init_Tubes_Notes #['notes']
        self.Tubes_Colors = self.Init_Tubes_Colors #cfg['colors']
        self.mapping_id=cfg['mapping_id']
        self.notes_to_color = cfg['notes_to_color']

        self.notes_to_light_mappings = [
            self.notes_to_light1,
            self.notes_to_light2,
            self.notes_to_light3
        ]

        self.light_to_notes_mappings = [
            self.light_to_notes1,
            self.light_to_notes2,
            self.light_to_notes3
        ]

    def generate_tubes(self,active):
        # A tube is active if its cap sensor is being touched
        # 'active' is a list of boolean touch sensor results where 1=cap sensor active
        self.Active_Tubes=active
        if self.notes_to_color:
            self.update_lights_notes() # Changed this to update lights and notes at the same time as they are related
            #self.update_notes() # Updates notes
            #self.notes_to_light_mappings[self.mapping_id]() # Uses mapping to update colours based on chosen notes
        else:
            self.update_light()
            self.light_to_notes_mappings[self.mapping_id]()
        return self.send_light(), self.send_notes()

    def update_lights_notes(self):
        # Notes chosen based on perceptable MIDI notes with our current speaker setup (oct 2023)
        # Notes are mapped to colours
        # lower note: 50
        # higher note: 100
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Colors[t][0] = int((self.Tubes_Colors[t][0] + 5.1) % 255)  # [0,255]
                self.Tubes_Notes[t] = int(51 + self.Tubes_Colors[t][0] / 5)
                #self.Tubes_Notes[t] = 50 + ((self.Tubes_Notes[t] + 1) % 51)
                '''if (self.Tubes_Notes[t] % 100) <= 50:
                    self.Tubes_Notes[t] = 50 + (self.Tubes_Notes[t] + 1) % 50  # [50,100]
                else:
                    self.Tubes_Notes[t] = (self.Tubes_Notes[t] + 1) % 50'''

    def update_notes (self):
        for t in range(len(self.Active_Tubes)):
            for t in range(len(self.Active_Tubes)):
                # if self.Active_Tubes[t]==1:
                # if self.Active_Tubes[t]==1:
                self.Tubes_Notes[t] = self.Init_Tubes_Notes[t]
                # else:
                # else:
                #     self.Tubes_Notes[t]=255

    def update_light (self):
        for t in range(len(self.Active_Tubes)):
            # if self.Active_Tubes[t]==1:
            self.Tubes_Colors[t][0]= self.Init_Tubes_Colors[t][0]
            self.Tubes_Colors[t][1] = self.Init_Tubes_Colors[t][1]
            # else:
            #     self.Tubes_Colors[t][0] = 255
            #     self.Tubes_Colors[t][1] = 255

    def notes_to_light1 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0]= random.randrange(0,255)

    def notes_to_light2 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0]= self.Tubes_Notes[t]

    def notes_to_light3 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0] = (self.Tubes_Colors[t][0] + 5) % 255


    def light_to_notes1 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = random.randrange(20,100)

    def light_to_notes2 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = self.Tubes_Colors[t]

    def light_to_notes3 (self):
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = max(20, (self.Tubes_Notes[t] + 5) % 100)

    def send_notes (self):
        return self.Tubes_Notes

    def send_light (self):
        return self.Tubes_Colors
