import json
import random
import sys
from typing import Tuple
import numpy as np
from psonic import synthesizers
from inspect import getmembers

import matplotlib.pyplot as plt
from matplotlib.colors import rgb_to_hsv

class SoundState(object):
    def __init__(self, random_init=True, amp=0, bpm=50, synth="saw", note=0, pan=-1, envelope=0):
        self.available_synths = [(a, d) for (a, d) in getmembers(synthesizers) if isinstance(d, synthesizers.Synth)] # Available synths, there are 42

        self.amp = random.randint(0, 255) if random_init else amp # Amplitude
        
        self.bpm = random.randint(50, 150) if random_init else bpm # Beats per minute
        
        self.pan = random.randint(-1, 1) if random_init else pan # Pan 

        if random_init:
            self.synth_id = random.randint(0, len(self.available_synths)) # Synth ID len(self.available_synths) = 42

        self.synth = self.available_synths[self.synth_id]

        self.note = random.randint(0, 255) if random_init else note # Note pitch
        
        self.envelope = random.randint(0, 1) if random_init else envelope # Envelope TODO

    def change_amp(self, delta:int) -> float:
        # Changes amp based on delta and returns the percentage between min and max
        self.amp = (self.amp + delta) % 256
        return self.amp / 256

    def change_note(self, delta:int) -> float:
        # Changes note based on delta and returns the percentage between min and max
        self.note = (self.note + delta) % 256#
        
        # We want random note values between 50 and 150
        #self.note = 50 + (self.note % 50)
        # TO TEST LATER
        return self.note / 256
    
    def change_bpm(self, delta:int) -> float:
        # Changes bpm based on delta and returns the percentage between min and max
        self.bpm = (self.bpm + delta) % 256
        return self.bpm / 256
    
    def change_pan(self, delta:int) -> float:
        # Changes pan based on delta and returns the percentage between min and max
        # Values are -1, 0, 1
        self.pan = (self.pan + delta) % 256
        return self.pan / 256

    def change_envelope(self, delta:int) -> float:
        # Changes envelope based on delta and returns the percentage between min and max
        self.envelope = (self.envelope + delta) % 256
        return self.envelope / 256

    def change_synth(self, delta:int) -> float:
        # Changes synth based on delta and returns the percentage between min and max
        self.synth_id = (self.synth_id + delta) % len(self.available_synths)
        self.synth = self.available_synths[self.synth_id]
        return self.synth_id / len(self.available_synths)


class LightState(object):
    def __init__(self, num_tubes, random_init=True, lights=None):
        if random_init:
            self.lights = [
                tuple(random.randint(0, 255) for _ in range(3))
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
            # ["a", "n", "t", "b", "p", "e"] == ["amp", "note-pitch", "synth", "bpm", "pan", "envelope"]
            if active:
                delta = 1 
                if 't' in tube_allocation:
                    value = self.sound_state.change_synth(delta)
                elif 'a' in tube_allocation:
                    value = self.sound_state.change_amp(delta)
                elif 'n' in tube_allocation:
                    value = self.sound_state.change_note(delta)
                elif 'b' in tube_allocation:
                    value = self.sound_state.change_bpm(delta)
                elif 'p' in tube_allocation:
                    value = self.sound_state.change_pan(delta)
                elif 'e' in tube_allocation:
                    value = self.sound_state.change_envelope(delta)

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
    Init_Tubes_Param = []
    Init_Tubes_Colors = [[]]  # first item in hue , second item is the value
    Tubes_Param = [] # Tubes_Param
    Tubes_Colors = [[]] # first item in hue , second item is the value
    notes_to_color = True


    def __init__(self, cfg):
        self.Init_Tubes_Param= [10, 60, "dsaw", 50, -1, 1] # ["amp", "note-pitch", "synth", "bpm", "pan", "envelope"],
        self.Init_Tubes_Colors = [
                                    [0, 0], 
                                    [0, 200], # [hue, value]
                                    [0, 200],
                                    [0, 200],
                                    [0, 200],
                                    [0, 200],
                                    [0, 200]
                                ] #cfg['colors']  # Init Tube Colors [hue, value]
        self.Tubes_Param = self.Init_Tubes_Param#['notes']
        self.Tubes_Colors = self.Init_Tubes_Colors #cfg['colors']
        #self.mapping_id=cfg['mapping_id']  # not used to delete
        self.notes_to_color = True #cfg['notes_to_color']  # what?
        #self.param_range = list(cfg['param_range'].items())  # paraneters domain
        
        self.param_range = {
                            "a":[20,50],
                            "n": [50,100],
                            "t":[0,42],
                            "b":[50,140],
                            "p":[-1,1],
                            "e":[0,1]
                        }   # should get from config file ----  
        
        self.param_range = list(self.param_range.items())

    def generate_tubes(self,active):
        # A tube is active if its cap sensor is being touched
        # 'active' is a list of boolean touch sensor results where 1=cap sensor active
        self.Active_Tubes=active
        print("Active Tubes: ", self.Active_Tubes)
        print("Notes to Color: ", self.notes_to_color)
        if self.notes_to_color:
            self.update_lights_param() # Changed this to update lights and notes at the same time as they are related
            
            #self.update_notes() # Updates notes
            #self.notes_to_light_mappings[self.mapping_id]() # Uses mapping to update colours based on chosen notes
        else:
            self.update_light()
            self.update_params()
            #self.light_to_notes_mappings[self.mapping_id]()
        return self.send_light(), self.send_params()

            
    def get_param_range(self, tube):
        # Gives the minimum value and the number of elements
        param_range = self.param_range[tube][1] # param range ex: [0, 42]
        return param_range[0], param_range[1] - param_range[0] + 1 
    
    def update_lights_param(self):
        # Notes chosen based on perceptable MIDI notes with our current speaker setup (oct 2023)
        # Notes are mapped to colours
        # lower note: 50
        # higher note: 100
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Colors[t][0] = int((self.Tubes_Colors[t][0] + 5.1) % 255)  # [0,255]
                #-----------------------------------------------------------------------------------------------------------------------------------------------------------------
                # Here er have to make sure that the value we give to the parameter is on the parameter's value space
                # for example pan is between -1 and 1
                # and note-pitch is between 50 and 100
                #-------------------------------------------------------------------------------------------------------------------------------------------------------------------
                min_val, num_elements = self.get_param_range(t)
                self.Tubes_Param[t] = int(min_val + self.Tubes_Colors[t][0] / (256/num_elements))
                # if synth is being changed, update the synth
                if t==2:
                    self.Tubes_Param[t] = self.available_synths[self.Tubes_Param[t]]
                #self.Tubes_Notes[t] = 50 + ((self.Tubes_Notes[t] + 1) % 51)
                '''if (self.Tubes_Notes[t] % 100) <= 50:
                    self.Tubes_Notes[t] = 50 + (self.Tubes_Notes[t] + 1) % 50  # [50,100]
                else:
                    self.Tubes_Notes[t] = (self.Tubes_Notes[t] + 1) % 50'''
    def send_params(self):
        # Create param dictionary
        param_dict = {}
        names = ["amp", "pitch", "synth", "bpm", "pan", "envelope"]
        #for t in range(len(self.Active_Tubes)):
        #    if self.Active_Tubes[t] == 1:
        #        param_dict[t] = {names[i]: self.Tubes_Param[i] for i in range(len(names))}
        
        for t in range(len(self.Active_Tubes)):
            param_dict[names[t]] = self.Tubes_Param[t]
        return param_dict

    def send_light (self):
        return self.Tubes_Colors

    def update_params(self):
        for t in range(len(self.Active_Tubes)):
            for t in range(len(self.Active_Tubes)):
                # if self.Active_Tubes[t]==1:
                # if self.Active_Tubes[t]==1:
                self.Tubes_Param[t] = self.Init_Tubes_Param[t]
                # else:
                # else:
                #     self.Tubes_Notes[t]=255

    def update_light(self):
        for t in range(len(self.Active_Tubes)):
            # if self.Active_Tubes[t]==1:
            self.Tubes_Colors[t][0]= self.Init_Tubes_Colors[t][0]
            self.Tubes_Colors[t][1] = self.Init_Tubes_Colors[t][1]
            # else:
            #     self.Tubes_Colors[t][0] = 255
            #     self.Tubes_Colors[t][1] = 255


    
    # I think the following functions are not used
    def notes_to_light1 (self):  # do we need this?
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t]==1:
               self.Tubes_Colors[t][0]= random.randrange(0,255)

    def light_to_notes1 (self): # do we need this?
        for t in range(len(self.Active_Tubes)):
            if self.Active_Tubes[t] == 1:
                self.Tubes_Notes[t] = random.randrange(20,100)

    