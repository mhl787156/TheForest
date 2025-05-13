import random
import sys
from typing import Tuple
import numpy as np
import time

from interfaces import DEFAULT_STATE, SCALE_TYPES, INSTRUMENTS, MELODIES, SCALES_TYPES_LIST, BASELINE_STYLE
import interfaces as ifc

import matplotlib.pyplot as plt
from matplotlib.colors import rgb_to_hsv


class SoundState(object):

    def __init__(self, initial_state, pillar_cfg):

        self.volume = initial_state["volume"]
        self.instruments = pillar_cfg["instruments"]
        self.bpm = pillar_cfg["bpm"]
        self.melody_scale = initial_state["melody_scale"]
        self.melody_number = initial_state["melody_number"]
        self.key = initial_state["key"]
        self.baseline_style = initial_state["baseline_style"]

        ### util state var
        self.change_instrument_next_layer = "melody"
        self.change_tempo_direction = 1
        self.tempo_max = 200
        self.tempo_min = 30
        self.key_center = 60

        self.reaction_notes = []

    def __repr__(self):
        return f"{self.to_json()}"

    def to_json(self):
        return {
            "volume": self.volume,
            "instruments": self.instruments,
            "key": self.key,
            "bpm": self.bpm,
            "melody_scale": self.melody_scale,
            "melody_number": self.melody_number,
            "baseline_style": self.baseline_style,
            "reaction_notes" : self.reaction_notes,
        }
    
    def items(self):
        return self.to_json().items()

    def change_instrument(self):
        # print("Changing Instrument")
        curr_instr = self.instruments[self.change_instrument_next_layer]
        curr_idx = INSTRUMENTS.index(curr_instr) 
        new_idx = (curr_idx + 1) % len(INSTRUMENTS)
        # print(f"Instrument Index from {curr_idx} -> {new_idx}, {len(INSTRUMENTS)}")
        self.instruments[self.change_instrument_next_layer] = INSTRUMENTS[new_idx]

        if self.change_instrument_next_layer == "melody":
            self.change_instrument_next_layer = "harmony"
        elif self.change_instrument_next_layer == "harmony":
            self.change_instrument_next_layer = "background"
        elif self.change_instrument_next_layer == "background":
            self.change_instrument_next_layer = "melody"
        
        return self.instruments

    def change_tempo(self, delta:int):
        tempo = self.bpm
        change = delta * self.change_tempo_direction

        if tempo + change > self.tempo_max:
            self.change_tempo_direction = -1
        elif tempo - change < self.tempo_min:
            self.change_tempo_direction = 1

        self.bpm = tempo + delta * self.change_tempo_direction
        return self.bpm

    def change_key(self, delta):
        self.key = self.key_center + ((self.key - self.key_center + delta) % 12)
        return self.key

    def change_melody(self):
        self.melody_number = (self.melody_number + 1) % len(MELODIES)
        return self.melody_number

    def change_scale(self):
        new_idx = (SCALES_TYPES_LIST.index(self.melody_scale) + 1) % len(SCALES_TYPES_LIST)
        self.melody_scale = SCALES_TYPES_LIST[new_idx]
        return self.melody_scale

    def change_baseline(self):
        new_idx = (BASELINE_STYLE.index(self.baseline_style) + 1) % len(BASELINE_STYLE)
        self.baseline_style = BASELINE_STYLE[new_idx]        
        return self.baseline_style
    
    def clear_reaction_notes(self):
        self.reaction_notes.clear()
        return self.reaction_notes

    def append_reaction_notes(self, note):
        self.reaction_notes.append(note)
        return self.reaction_notes


class LightState(object):
    def __init__(self, num_tubes, random_init=True, lights=None):
        if random_init:
            self.lights = [
                tuple(random.randint(0, 255) for _ in range(3))
                for _ in range(num_tubes)
            ]
        else:
            self.lights = lights

    def __repr__(self):
        return f"{self.lights}"

    def __getitem__(self, indices):
        if not isinstance(indices, list):
            indices = [indices]
        ret = [self.lights[i] for i in indices]
        if len(ret) == 1:
            return ret[0]
        return ret

    def __setitem__(self, key, newvalue):
        self.lights[key] = newvalue

class Pillar_Mapper_Base(object):

    def __init__(self, cfg, pillar_cfg):
        """Base Class for any mapping function for a single pillar

        Args:
            pillar_cfg (Dict): The configuration file for the pillar
        """

        self.num_tubes = pillar_cfg["num_tubes"]

        self.sound_state: SoundState = SoundState(cfg["default_state"], pillar_cfg)
        self.light_state: LightState = LightState(self.num_tubes, random_init=True)
        self.state_array = [False for _ in range(self.num_tubes)]

    def update_pillar(self, state_array) -> Tuple[SoundState, LightState]:

        # Update internal state
        self.interaction_update_sound_light(self.state_array, state_array)
        self.state_array = state_array

        return self.sound_state, self.light_state

    # This should be implemented in child classes
    def interaction_update_sound_light(self, old_state, new_state):
        # This function takes the tube_id and the current tube states (sound and light)
        # It changes the amplitude, synth and note and color for this pillar
        # Internally changes self.sound_state and self.light_state
        print("In Pillar Mapper Base")

class FixedMapper(Pillar_Mapper_Base):
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)
        
        self.num_tubes = pillar_cfg["num_tubes"]
        self.notes = pillar_cfg["notes"]
        self.octave = pillar_cfg["octave"]

        # Create a fixed color map from midi note (0-11) to hue (0-255)
        self.fixed_hue_map = ifc.FIXED_NOTE_HUE_MAP

    # This should be implemented in child classes
    def interaction_update_sound_light(self, old_state, new_state):
        
        # Clears the reaction note for the Composer 
        self.sound_state.clear_reaction_notes()

        # If we now detect as active, we add a reaction note and change the light state as specified
        for tube_id, (old_active, active) in enumerate(zip(old_state, new_state)):
            if not old_active and active:
                note = self.notes[tube_id]
                note_to_play = note + self.octave * 12
                self.sound_state.append_reaction_notes(note_to_play)
                self.light_state[tube_id] = (self.fixed_hue_map[note], 255, 255)

class RotationMapper(Pillar_Mapper_Base):
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)

        self.tube_allocation = pillar_cfg["tube_allocation"]

        # Create a colormap from red to blue scaled between 0 and 255
        self.cmap = plt.get_cmap('coolwarm')
        # self.hsv_values = rgb_to_hsv(self.colormap[:, :3])

    # This should be implemented in child classes
    def interaction_update_sound_light(self, old_state, new_state):
        # This function takes the tube_id and the current tube states (sound and light)
        # It changes the amplitude, synth and note and color for this pillar
        # Internally changes self.sound_state and self.light_state
        # print("In ROtation Mapper")
        for tube_id, (active, tube_allocation) in enumerate(zip(new_state, self.tube_allocation)):
            # ["a", "n", "t", "b", "p", "e"] == ["amp", "note-pitch", "synth", "bpm", "pan", "envelope"]
            # ["i", "t", "k", "m", "s", "b"]
            # print(f"Updating tube {tube_id}, {tube_allocation}, {active}")
            if active:
                delta = 1 
                if 'i' in tube_allocation:
                    value = self.sound_state.change_instrument()
                elif 't' in tube_allocation:
                    value = self.sound_state.change_tempo(delta=5)
                elif 'k+' in tube_allocation:
                    value = self.sound_state.change_key(delta=5)
                elif 'k-' in tube_allocation:
                    value = self.sound_state.change_key(delta=-4)
                elif 'm' in tube_allocation:
                    value = self.sound_state.change_melody()
                elif 's' in tube_allocation:
                    value = self.sound_state.change_scale()
                elif 'b' in tube_allocation:
                    value = self.sound_state.change_baseline()

                self.light_state[tube_id] = tuple(rgb_to_hsv(self.cmap(random.random())[:3]))

class EventRotationMapper(Pillar_Mapper_Base):
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)

        self.tube_allocation = pillar_cfg["tube_allocation"]

        # Create a colormap from red to blue scaled between 0 and 255
        self.cmap = plt.get_cmap('coolwarm')
        # self.hsv_values = rgb_to_hsv(self.colormap[:, :3])

    # This should be implemented in child classes
    def interaction_update_sound_light(self, old_state, new_state):
        # This function takes the tube_id and the current tube states (sound and light)
        # It changes the amplitude, synth and note and color for this pillar
        # Internally changes self.sound_state and self.light_state
        # print("In ROtation Mapper")
        for tube_id, (old_active, active, tube_allocation) in enumerate(zip(old_state, new_state, self.tube_allocation)):
            # ["i", "t", "k", "m", "s", "b"]
            # Only change on a switch
            if not old_active and active:
                delta = 1 
                if 'i' in tube_allocation:
                    value = self.sound_state.change_instrument()
                elif 't+' in tube_allocation:
                    value = self.sound_state.change_tempo(delta=10)
                elif 't-' in tube_allocation:
                    value = self.sound_state.change_tempo(delta=-10)
                elif 'k+' in tube_allocation:
                    value = self.sound_state.change_key(delta=5)
                elif 'k-' in tube_allocation:
                    value = self.sound_state.change_key(delta=-4)
                elif 'm' in tube_allocation:
                    value = self.sound_state.change_melody()
                elif 's' in tube_allocation:
                    value = self.sound_state.change_scale()
                elif 'b' in tube_allocation:
                    value = self.sound_state.change_baseline()

                self.light_state[tube_id] = tuple(rgb_to_hsv(self.cmap(random.random())[:3]))

class ColorSequencerMapper(Pillar_Mapper_Base):
    '''
    Implementation similar to EVOMUSART 2024 but using new sound library.

    The aim here is to use the pillars like a step sequencer and the colour they are currently lit at
    corresponds to the note that they play.
    '''
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)
        self.num_tubes = pillar_cfg["num_tubes"]
        self.octave = pillar_cfg["octave"]
        self.step_index = 0

        self.bpm = cfg["default_state"]["bpm"]
        self.step_interval = 60.0 / self.bpm
        self.last_step_time = time.time()
        self.last_step_index = None

    def get_note_from_hue(self, hue):
        """Map hue (0–255) to pitch class (0–11)"""
        note = int((hue % 256) / 256 * 12)  # gives 0–11
        return note

    def interaction_update_sound_light(self, old_state, new_state):
        # Note - state array is ignored for this implementation so old_state, new_state not used
        self.sound_state.clear_reaction_notes()

        # Only trigger on step change
        if self.step_index != self.last_step_index:
            hue, s, v = self.light_state[self.step_index]
            note = self.get_note_from_hue(hue)
            note_to_play = note + self.octave * 12
            self.sound_state.append_reaction_notes(note_to_play)

            self.last_step_index = self.step_index

            print(f"[STEP {self.step_index}] hue={hue}, s={s}, v={v} → note={note}, midi={note_to_play}")

        # Advance step
        now = time.time()
        if now - self.last_step_time >= self.step_interval:
            self.step_index = (self.step_index + 1) % self.num_tubes
            self.last_step_time = now

        return self.sound_state, self.light_state


def generate_mapping_interface(cfg, cfg_pillar) -> Pillar_Mapper_Base:
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
    return targetClass(cfg, cfg_pillar)

