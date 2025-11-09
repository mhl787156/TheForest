import random
import sys
from typing import Tuple
import numpy as np
import time
import math

from interfaces import DEFAULT_STATE, SCALE_TYPES, INSTRUMENTS, MELODIES, SCALES_TYPES_LIST, BASELINE_STYLE
import interfaces as ifc

import matplotlib.pyplot as plt
from matplotlib.colors import rgb_to_hsv


class SoundState(object):

    def __init__(self, initial_state, pillar_cfg):

        # Note need a better way of merginging states...
        self.volume = pillar_cfg["volume"]
        self.instruments = pillar_cfg["instruments"]
        self.bpm = pillar_cfg["bpm"]
        self.melody_scale = initial_state["melody_scale"]
        self.melody_number = initial_state["melody_number"]
        self.key = initial_state["key"]
        self.baseline_style = initial_state["baseline_style"]
        
        # Initialize active_synths from default state
        self.active_synths = initial_state.get("active_synths", {
            "background": False,
            "harmony": False,
            "melody1": False,
            "melody2": False
        })

        ### util state var
        self.change_instrument_next_layer = "melody"
        self.change_tempo_direction = 1
        self.tempo_max = 200
        self.tempo_min = 30
        self.key_center = 60

        self.generated_notes = []
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
            "generated_notes": self.generated_notes,
            "active_synths": self.active_synths,
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

    def has_reaction_notes(self):
        return len(self.reaction_notes) > 0
    
    def trigger_synth(self, synth_name):
        """Trigger a synth layer (harmony, melody1, melody2)"""
        if hasattr(self, 'active_synths') and synth_name in self.active_synths:
            self.active_synths[synth_name] = True
    
    def reset_triggers(self):
        """Reset all triggers except background"""
        if hasattr(self, 'active_synths'):
            self.active_synths = {
                "background": False,
                "harmony": False,
                "melody1": False,
                "melody2": False
            }


class Pillar_Mapper_Base(object):

    def __init__(self, cfg, pillar_cfg):
        """Base Class for any mapping function for a single pillar

        Args:
            pillar_cfg (Dict): The configuration file for the pillar
        """

        self.num_buttons = pillar_cfg.get("num_buttons", 4)

        self.sound_state: SoundState = SoundState(cfg["default_state"], pillar_cfg)
        self.state_array = [False for _ in range(self.num_buttons)]

    def update_pillar(self, state_array) -> SoundState:

        # Update internal state
        self.interaction_update_sound_light(self.state_array, state_array)
        self.state_array = state_array

        return self.sound_state

    # This should be implemented in child classes
    def interaction_update_sound_light(self, old_state, new_state):
        # This function takes the button states
        # It changes the sound state
        # Internally changes self.sound_state
        print("In Pillar Mapper Base")

class ButtonTriggerMapper(Pillar_Mapper_Base):
    """Maps button presses to synth triggers
    
    Button 0 → harmony
    Button 1 → melody1
    Button 2 → melody2
    Button 3 → melody1 (duplicate)
    """
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)

        self.octave = pillar_cfg.get("octave", 5)

    def _gen_burst_notes1(self): #TODO make more efficient
        # Random density: 3-12 grains per second (matches synth.scd)
        density = random.uniform(3, 12)
        grain_interval = 1.0 / density
        burst_duration = 2.0  # seconds
        
        elapsed = 0.0
        notes = []
        
        while elapsed < burst_duration:
            # Randomize frequency for each grain (matches synth.scd line 221)
            grain_freq =  random.uniform(400, 6000) * random.uniform(0.95, 1.05)
            # Convert Hz to MIDI pitch for SCAMP
            midi_pitch = 69 + 12 * math.log2(grain_freq / 1760.0)
            notes.append(midi_pitch)
            elapsed += grain_interval

        wait_time = [grain_interval]*len(notes)

        return notes, wait_time
                
    def _gen_burst_notes2(self):
        # Pick random frequency from pool
        # Frequency pool: D1, A1, D2, A2, D3 (36.71, 55, 73.42, 110, 146.83 Hz)
        bass_freqs = [36.71, 55, 73.42, 110, 146.83]
        # Syncopated 4-note pattern: t=0s, 0.4s, 1.0s, 1.6s (total 2s)
        wait_time = [0, 0.2, 0.5, 0.65]
        notes = []

        for i in range(len(wait_time)):
            freq_hz = random.choice(bass_freqs) * random.uniform(0.99, 1.01)
            midi_pitch = 69 + 12 * math.log2(freq_hz/ 440.0)
            notes.append(midi_pitch)

        return notes, wait_time
                
    def interaction_update_sound_light(self, old_state, new_state):
        # Reset active synths (triggers are one-shot)
        self.sound_state.active_synths = {
            "background": False,  # Always on
            "harmony": False,
            "melody1": False,
            "melody2": False
        }

        self.notes = []
        self.time = []

        # Detect button presses (rising edge: old=False, new=True)
        for button_id, (old_active, active) in enumerate(zip(old_state, new_state)):
            if not old_active and active:
                if button_id == 0:
                    self.sound_state.active_synths["harmony"] = True
                    # Fixed pattern: 2 voices across 8 seconds (4s each)
                    self.notes = [60, 60]
                    self.time = [0, 4.0]
                    print(f"[BUTTON {button_id}] Triggering harmony")
                elif button_id == 1:
                    self.sound_state.active_synths["melody1"] = True
                    self.notes, self.time = self._gen_burst_notes1()
                    print(f"[BUTTON {button_id}] Triggering melody1")
                elif button_id == 2:
                    self.sound_state.active_synths["melody2"] = True
                    self.notes, self.time = self._gen_burst_notes2()
                    print(f"[BUTTON {button_id}] Triggering melody2")
                elif button_id == 3:
                    self.sound_state.active_synths["melody1"] = True
                    self.notes, self.time = self._gen_burst_notes1()
                    print(f"[BUTTON {button_id}] Triggering melody1 (duplicate)")

        self.sound_state.generated_notes = {"notes":self.notes, "time":self.time} 
        # Clears the reaction note for the Composer 
        self.sound_state.clear_reaction_notes()
        
        # If we now detect as active, we add a reaction note
        for button_id, (old_active, active) in enumerate(zip(old_state, new_state)):
            if not old_active and active:
                for note in self.notes:
                    note_to_play = note + self.octave * 12
                    self.sound_state.append_reaction_notes(note_to_play)


class FixedMapper(Pillar_Mapper_Base):
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)
        
        self.notes = pillar_cfg.get("notes", [60, 62, 64, 67])
        self.octave = pillar_cfg.get("octave", 5)

        # Create a fixed color map from midi note (0-11) to hue (0-255)
        self.fixed_hue_map = ifc.FIXED_NOTE_HUE_MAP

    # This should be implemented in child classes
    def interaction_update_sound_light(self, old_state, new_state):
        
        # Clears the reaction note for the Composer 
        self.sound_state.clear_reaction_notes()

        # If we now detect as active, we add a reaction note
        for button_id, (old_active, active) in enumerate(zip(old_state, new_state)):
            if not old_active and active and button_id < len(self.notes):
                note = self.notes[button_id]
                note_to_play = note + self.octave * 12
                self.sound_state.append_reaction_notes(note_to_play)

class RotationMapper(Pillar_Mapper_Base):
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)

        self.tube_allocation = pillar_cfg.get("tube_allocation", ["i", "t", "k+", "m"])

    # This should be implemented in child classes
    def interaction_update_sound_light(self, old_state, new_state):
        # This function processes button presses to change sound parameters
        for button_id, (active, button_allocation) in enumerate(zip(new_state, self.tube_allocation)):
            # ["i", "t", "k", "m", "s", "b"]
            if active and button_id < len(self.tube_allocation):
                delta = 1 
                if 'i' in button_allocation:
                    value = self.sound_state.change_instrument()
                elif 't' in button_allocation:
                    value = self.sound_state.change_tempo(delta=5)
                elif 'k+' in button_allocation:
                    value = self.sound_state.change_key(delta=5)
                elif 'k-' in button_allocation:
                    value = self.sound_state.change_key(delta=-4)
                elif 'm' in button_allocation:
                    value = self.sound_state.change_melody()
                elif 's' in button_allocation:
                    value = self.sound_state.change_scale()
                elif 'b' in button_allocation:
                    value = self.sound_state.change_baseline()

class EventRotationMapper(Pillar_Mapper_Base):
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)

        self.tube_allocation = pillar_cfg.get("tube_allocation", ["i", "t", "k+", "m"])

    # This should be implemented in child classes
    def interaction_update_sound_light(self, old_state, new_state):
        # This function processes button presses to change sound parameters
        # Only change on a rising edge (button press)
        for button_id, (old_active, active, button_allocation) in enumerate(zip(old_state, new_state, self.tube_allocation)):
            # ["i", "t", "k", "m", "s", "b"]
            # Only change on a switch
            if not old_active and active and button_id < len(self.tube_allocation):
                delta = 1 
                if 'i' in button_allocation:
                    value = self.sound_state.change_instrument()
                elif 't+' in button_allocation:
                    value = self.sound_state.change_tempo(delta=10)
                elif 't-' in button_allocation:
                    value = self.sound_state.change_tempo(delta=-10)
                elif 'k+' in button_allocation:
                    value = self.sound_state.change_key(delta=5)
                elif 'k-' in button_allocation:
                    value = self.sound_state.change_key(delta=-4)
                elif 'm' in button_allocation:
                    value = self.sound_state.change_melody()
                elif 's' in button_allocation:
                    value = self.sound_state.change_scale()
                elif 'b' in button_allocation:
                    value = self.sound_state.change_baseline()

class ColorSequencerMapper(Pillar_Mapper_Base):
    '''
    Implementation similar to EVOMUSART 2024 but using new sound library.

    The aim here is to use the buttons like a step sequencer.
    '''
    def __init__(self, cfg, pillar_cfg):
        super().__init__(cfg, pillar_cfg)
        self.num_buttons = pillar_cfg.get("num_buttons", 4)
        self.octave = pillar_cfg.get("octave", 5)
        self.step_index = 0

        self.bpm = cfg["default_state"]["bpm"]
        self.step_interval = 60.0 / self.bpm
        self.last_step_time = time.time()
        self.last_step_index = None

    def interaction_update_sound_light(self, old_state, new_state):
        # Note - state array is ignored for this implementation so old_state, new_state not used
        self.sound_state.clear_reaction_notes()

        # Only trigger on step change
        if self.step_index != self.last_step_index:
            note_to_play = 60 + self.step_index * 2  # Simple note progression
            self.sound_state.append_reaction_notes(note_to_play)

            self.last_step_index = self.step_index

            print(f"[STEP {self.step_index}] → note={note_to_play}")

        # Advance step
        now = time.time()
        if now - self.last_step_time >= self.step_interval:
            self.step_index = (self.step_index + 1) % self.num_buttons
            self.last_step_time = now


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

