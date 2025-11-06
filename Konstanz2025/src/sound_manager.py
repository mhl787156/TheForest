from scamp import Session, wait, current_clock
import scamp_extensions.process as seprocess
from scamp_extensions.playback.supercollider import add_sc_extensions

import expenvelope as expe
 
import multiprocessing as mp
from queue import Queue
import random
import numpy as np
import copy
from functools import reduce

from interfaces import *
from sc_synths import * 

add_sc_extensions()

class InstrumentManager:

    def __init__(self, session):
        self.session = session

        self.instrument_names= {
            "melody1": None,
            "melody2": None,
            "harmony": None,
            "background": None
        }

        self.instruments = {
            "melody1": None,
            "melody2": None,
            "harmony": None,
            "background": None
        }

        self.all_scamp_instruments = INSTRUMENTS
        self.all_sc_instruments = SC_PARTS

    def update_instrument(self, instrument_name, function="melody"):
        print("Sound Manager Update Instrument Called")
        if self.instrument_names[function] == instrument_name:
            return
        
        if instrument_name == "disable":
            return
        
        if self.instrument_names[function] is not None:
            # Remove Existing Instrument
            current_instruments = [i.name for i in self.session.instruments]
            idx = list(current_instruments).index(self.instrument_names[function])
            self.session.pop_instrument(idx)
            # print(f"Previous Instrument Removed {self.instrument_names[function]}")

        if instrument_name in self.all_sc_instruments:
            self.instruments[function] = create_supercollider_synth(self.session, instrument_name)
        else:
            self.instruments[function] = self.session.new_part(instrument_name)
        self.instrument_names[function] = instrument_name
        # print(f"New Instrument Added {self.instrument_names[function]}")

    def melody1_instrument(self):
        return self.instruments["melody1"]

    def melody2_instrument(self):
        return self.instruments["melody2"]

    def harmony_instrument(self):
        return self.instruments["harmony"]

    def background_instrument(self):
        return self.instruments["background"]

class Composer:

    def __init__(self, session, initial_state):
        self.session = session

        self.state = copy.deepcopy(initial_state)

        self.mp_manager = mp.Manager()

        # Instruments
        self.instrument_manager = InstrumentManager(self.session)
        self.update_instruments(self.state["instruments"])

        # Note pitch-wise "60" = Middle C
        # Harmony (key - random shuffle of circle of fifths)
        self.all_keys = [60 + i for i in range(11)]
        self.key_generator = self.generate_key_generator()
        self.melody_generator = self.generate_melody_generator(next(self.key_generator))

        self.shared_state = {
            "key": self.mp_manager.Value('s', next(self.key_generator)),
            "chord_levels": self.mp_manager.Value('d', 0),
            "melody_speed_multipler": 8.0
        }

        self.active_forks = {
            "background": None
        }
        
        # Start background immediately - runs continuously
        print("[COMPOSER] Starting background pad")
        self.active_forks["background"] = self.session.fork(self.fork_background, args=(self.shared_state,))

    def update(self, setting_name, value):

        # print("Sound State Updating", setting_name, self.state[setting_name],  value)
        if self.state[setting_name] != value:
            # Interaction
            if self.shared_state["chord_levels"].value < 4:
                self.shared_state["chord_levels"].value += 1

            value = copy.deepcopy(value)
            # The copy is important here
            self.state[setting_name] = value
            if setting_name == "volume":
                self.state["volume"] = value
            if setting_name == "instruments":
                self.update_instruments(value)
            if setting_name == "key":
                self.update_key(value)
            if setting_name == "bpm":
                # self.session.bpm = value
                self.session.set_tempo_target(value, 0.2)
            if setting_name == "reaction_notes":
                for i, note in enumerate(value):
                    self.session.fork(self.fork_melody_single_note, args=(note,))
            if setting_name == "broadcast_notes":
                delay = self.state.get("broadcast", {}).get("echo_delay_duration", 0)
                for i, note in enumerate(value):
                    self.session.fork(self.fork_melody_single_note, args=(note,delay,))
            if setting_name == "active_synths":
                # Trigger synth bursts based on button presses
                self.handle_synth_triggers(value)
            
    def update_instruments(self, instruments):
        for k,v in instruments.items():
            self.instrument_manager.update_instrument(v, function=k)

    def update_key(self, key):
        self.shared_state["key"].value = key

    def update_chord_leve(self, level):
        self.shared_state["chord_levels"].value += level

    def generate_key_generator(self):
        # return seprocess.generators.random_walk(self.all_keys[0], clamp_min=min(self.all_keys), clamp_max=max(self.all_keys))
        circle_fifths = [48 + (i*5) % 12 for i in range(11)]
        return seprocess.generators.non_repeating_shuffle(list(circle_fifths))
    
    def generate_melody_generator(self, key):
        notes = SCALE_TYPES[self.state["melody_scale"]](key)
        return seprocess.generators.non_repeating_shuffle(list(notes))

    def play(self):
        # Background runs continuously (started in __init__)
        # Other synths triggered by buttons
        pass
    
    def handle_synth_triggers(self, active_synths):
        """Handle direct triggers from button presses"""
        if active_synths.get("harmony", False):
            print("[TRIGGER] Harmony burst")
            self.session.fork(self.trigger_harmony_burst)
        
        if active_synths.get("melody1", False):
            print("[TRIGGER] Melody1 burst")
            self.session.fork(self.trigger_melody1_burst)
        
        if active_synths.get("melody2", False):
            print("[TRIGGER] Melody2 burst")
            self.session.fork(self.trigger_melody2_burst)
    
    def fork_melody_single_note(self, note, delay=0.0):
        volume = self.state["volume"]["melody1"]
        instrument = self.instrument_manager.melody1_instrument()
        # envelope = expe.envelope.Envelope.from_levels_and_durations(
        #     [0.1, volume, 1.0], [0.5, 3.0]
        # )
        # envelope = expe.envelope.Envelope.adsr(0.5, volume, 1.0, 0.2, 0.15, 0.5)
        print("Single Note Being Played", note, volume)
        # duration_multiplier = self.shared_state["melody_speed_multipler"]
        if delay > 0:
            wait(delay) # If received a delay before playing note
        instrument.play_note(note, volume, 0.25, blocking=True)

    def trigger_melody1_burst(self):
        """Trigger a single spectral swarm burst"""
        instrument = self.instrument_manager.melody1_instrument()
        volume = self.state["volume"]["melody1"]
        # Spectral swarm burst (5-10 grains internally, ~1s duration)
        instrument.play_note(60, volume, 1.0, blocking=False)
    
    def trigger_melody2_burst(self):
        """Trigger a single formant voice"""
        instrument = self.instrument_manager.melody2_instrument()
        volume = self.state["volume"]["melody2"]
        # Formant voice (7-second envelope)
        instrument.play_note(60, volume, 7.0, blocking=False)

    def trigger_harmony_burst(self):
        """Trigger a single FM metallic throb"""
        instrument = self.instrument_manager.harmony_instrument()
        volume = self.state["volume"]["harmony"]
        # FM throb (6-second envelope)
        instrument.play_note(60, volume, 7.0, blocking=False)

    # def fork_harmony(self, shared_state):
    #     # current_clock().tempo = self.state["bpm"]["harmony"]
    #     instrument = self.instrument_manager.harmony_instrument()
    #     key = next(self.key_generator)
    #     # print("harmony", key)
    #     scale = list(SCALE_TYPES[self.state["melody_scale"]](key))

    #     # Add 7/9/11/13 etc depending on chord_levels
    #     chord_levels = shared_state["chord_levels"].value

    #     chord = []
    #     gen_chords = [0, 2, 4] + [6 + 2*chord_levels*i for i in range(chord_levels)]
    #     for offset in gen_chords:
    #         if offset >= len(scale):
    #             new_offset = offset % len(scale)
    #             number_up = offset // len(scale)
    #             # print(offset, new_offset, number_up)
    #             note = scale[new_offset] + number_up * 12
    #         else:
    #             note = scale[offset]
    #         chord.append(int(note))

    #     # Adjust voicings
    #     # print(chord)
    #     random.shuffle(chord)
    #     key_idx = chord.index(key)
    #     chord = np.array(chord)
    #     chord[key_idx:] += 12 # If some of the chords are below tonic, shift down octave
    #     # print(chord)

        
    #     volume = self.state["volume"]["harmony"]
    #     envelope = expe.envelope.Envelope.from_levels_and_durations(
    #         [0.1, volume, 1.0], [0.5, 3.0]
    #     )
    #     envelope = expe.envelope.Envelope.adsr(0.5, volume, 1.0, 0.2, 0.15, 0.5)
    #     # instrument.play_chord(chord, envelope, 4.0, blocking=True)

    #     if chord_levels > 0:
    #         shared_state["chord_levels"].value -= 1

    #     shared_state["key"].value = key

    def fork_background(self, shared_state):
        # Mystic ambient pad cloud - continuous background (matches background.scd)
        print("[BACKGROUND] Fork started")
        try:
            # D2, A2, D3, A3, D4 harmonics
            pad_freqs = [73.42, 110, 146.83, 220, 293.66]
            iteration = 0
            while True:
                iteration += 1
                # Get fresh instrument reference each time to ensure it's valid
                instrument = self.instrument_manager.background_instrument()
                volume = self.state["volume"]["background"]
                
                # Pick random frequency with slight detune
                freq = random.choice(pad_freqs) * random.uniform(0.98, 1.02)
                
                # Spawn single pad: 8s attack + 20s sustain + 12s release = 40s total
                print(f"[BACKGROUND #{iteration}] Spawning pad: freq={freq:.2f}Hz, vol={volume:.2f}, instrument={instrument.name if hasattr(instrument, 'name') else 'unknown'}")
                
                # Fork a separate thread for this note so it doesn't block
                self.session.fork(self._play_background_note, args=(instrument, freq, volume, iteration))
                
                # Irregular spawning timing (1.5-3 bars at 80 BPM = 4.5-9 seconds)
                wait_time = random.uniform(4.5, 9.0)
                print(f"[BACKGROUND #{iteration}] Waiting {wait_time:.1f}s before next spawn")
                wait(wait_time, units="time")
                print(f"[BACKGROUND #{iteration}] Wait complete, looping...")
        except Exception as e:
            print(f"[BACKGROUND] ERROR: Fork crashed with exception: {e}")
            import traceback
            traceback.print_exc()
    
    def _play_background_note(self, instrument, freq, volume, iteration):
        """Play a single background pad note in its own fork"""
        try:
            print(f"[BACKGROUND #{iteration}] Note fork started, calling play_note")
            instrument.play_note(freq, volume, 20.0, blocking=False)
            print(f"[BACKGROUND #{iteration}] Note triggered successfully")
        except Exception as e:
            print(f"[BACKGROUND #{iteration}] ERROR playing note: {e}")
            import traceback
            traceback.print_exc()

class SoundManager:
    """Manages and schedules sound playback for pillars using the Sonic Pi server."""          
    
    def __init__(self, pillar_id, initial_state=None):
        self.pillar_id = pillar_id
        self.session = Session()
        self.state = initial_state if initial_state is not None else DEFAULT_STATE
        print(self.state)
        for k, d in DEFAULT_STATE.items(): # merge (note is not recursive)
            if k not in self.state:
                self.state[k] = d
        self.composer = Composer(self.session, self.state)

    def __repr__(self):
        """String representation of the pillar for debugging."""
        return f"Pillar({self.pillar_id}) {self.state}"
    
    def update_pillar_setting(self, setting_name, value):
        """Updates the settings dictionary for a specific pillar."""
        self.composer.update(setting_name, value)

    def tick(self, time_delta=1/30.0):
        # Check if background fork is still alive
        if not self.composer.active_forks["background"].alive:
            print("[WARNING] Background fork died! Restarting...")
            self.composer.active_forks["background"] = self.composer.session.fork(
                self.composer.fork_background, args=(self.composer.shared_state,)
            )
        
        # Start melody/harmony forks if needed (background always running)
        self.composer.play()
        wait(time_delta, units="time")


if __name__=="__main__":

    sm = SoundManager("test")
    while True:
        sm.tick()
    # session = Session()
    # session.bpm = 60
    # comp = Composer(session, DEFAULT_STATE)
    # while True:
        # comp.play()
        # wait(1/30.0, units="time")

    
