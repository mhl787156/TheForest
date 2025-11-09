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
import subprocess
import os
import time

from interfaces import *
from sc_synths import * 

add_sc_extensions()

# ========== DIAGNOSTIC FUNCTIONS ==========

def print_server_info(prefix=""):
    """Print scsynth process info and top CPU consumers"""
    try:
        out = subprocess.check_output(["ps", "aux"]).decode()
        scs = [l for l in out.splitlines() if "scsynth" in l]
        print(f"{prefix} scsynth processes: {len(scs)}")
        for s in scs:
            print("   ", s)
    except Exception as e:
        print(f"{prefix} Couldn't query ps:", e)

    try:
        top = subprocess.check_output(["bash","-c","ps -eo pid,cmd,%cpu,%mem --sort=-%cpu | head -n 8"]).decode()
        print(f"{prefix} Top procs:\n{top}")
    except Exception as e:
        print(f"{prefix} Couldn't query top:", e)

def query_sc_status():
    """Query SuperCollider server status via OSC (placeholder for now)"""
    # To implement: would need pythonosc to send /status to port 57110
    # and listen for /status.reply on port 57120
    # For now, process info from print_server_info() is sufficient
    pass

# ==========================================

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
        
        # Safety limit for concurrent pads
        self.active_pad_count = 0
        self.max_concurrent_pads = 6  # Limit to prevent overload
        
        # Start background immediately - runs continuously
        print("[COMPOSER] Starting background pad")
        self.active_forks["background"] = self.session.fork(self.fork_background, args=(self.shared_state,))

    def update(self, setting_name, value, extra_arg=None): #TODO make nice

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
                print(f"[COMPOSER] Received active_synths: {value}")
                self.handle_synth_triggers(value,extra_arg)
            
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
    
    def handle_synth_triggers(self, active_synths, generated_notes):
        """Handle direct triggers from button presses"""
        notes = generated_notes['notes']
        time = generated_notes['time']

        if active_synths.get("harmony", False):
            print("[TRIGGER] Harmony burst")
            self.session.fork(self.trigger_harmony_burst, args=(notes,time))
        
        if active_synths.get("melody1", False):
            print("[TRIGGER] Melody1 burst")
            self.session.fork(self.trigger_melody1_burst, args=(notes,time))
        
        if active_synths.get("melody2", False):
            print("[TRIGGER] Melody2 burst")
            self.session.fork(self.trigger_melody2_burst, args=(notes,time))
    
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

    def trigger_melody1_burst(self, notes, wait_time):
        """Trigger 2-second spectral swarm burst """
        instrument = self.instrument_manager.melody1_instrument()
        volume = self.state["volume"]["melody1"]

        print(f"[MELODY1] Starting swarm")
        
        grain_count = 0
        
        for i, note in enumerate(notes):
            # Spawn grain
            instrument.play_note(
                note,  # Random pitch (400-6000Hz range)
                volume, 
                0.2,  # Duration (EnvGen uses its own random envelope 0.05-0.2s)
                blocking=False
            )
            grain_count += 1
            
            grain_interval = wait_time[i] + random.uniform(0,0.1)
            # Wait before next grain
            wait(grain_interval, units="time")
        
        print(f"[MELODY1] Swarm complete: spawned {grain_count} grains")
    
    def trigger_melody2_burst(self, notes, wait_time):
        """Trigger 2-measure phrase: 2 formant voices"""
        instrument = self.instrument_manager.melody2_instrument()
        volume = self.state["volume"]["melody2"]
        
        for i, note in enumerate(notes):
            wait(wait_time[i], units="time")
            instrument.play_note(60, volume, 7.0, blocking=False)
            print(f"[MELODY2] Voice at t={t}s")

    def trigger_harmony_burst(self, notes, wait_time):
        """Trigger 4-note syncopated bass line (2s duration)"""    
        instrument = self.instrument_manager.harmony_instrument()
        volume = self.state["volume"]["harmony"]
        
        print(f"[HARMONY] Starting bass line: 4 notes over 2s")
        
        for i, note in enumerate(notes):
            wait(wait_time[i], units="time")
            instrument.play_note(note, volume, 0.5, blocking=False)
            print(f"[HARMONY] Note {i+1} at t={t}s: {note:.1f}Hz")
        
        print(f"[HARMONY] Bass line complete")

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
            # D1, A1, D2, A2, D3 harmonics (one octave lower)
            pad_freqs = [36.71, 55, 73.42, 110, 146.83]
            iteration = 0
            while True:
                iteration += 1
                # Get fresh instrument reference each time to ensure it's valid
                instrument = self.instrument_manager.background_instrument()
                volume = self.state["volume"]["background"]
                
                # Check if we've hit the concurrent pad limit
                if self.active_pad_count >= self.max_concurrent_pads:
                    print(f"[BACKGROUND #{iteration}]  PAD LIMIT REACHED ({self.active_pad_count}/{self.max_concurrent_pads}) - skipping spawn")
                    print_server_info(f"[BACKGROUND #{iteration}]")
                else:
                    # Pick random frequency with slight detune
                    freq = pad_freqs[iteration % len(pad_freqs)] * random.uniform(0.98, 1.02)
                    
                    # Spawn single pad: 8s attack + 20s sustain + 12s release = 40s total
                    print(f"[BACKGROUND #{iteration}] Spawning pad: freq={freq:.2f}Hz, vol={volume:.2f}, active_pads={self.active_pad_count}/{self.max_concurrent_pads}")
                    
                    # Increment counter before spawning
                    self.active_pad_count += 1
                    
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
        start_time = time.time()
        try:
            print(f"[BACKGROUND #{iteration}] Note fork started, calling play_note")
            # Use blocking=False + manual wait for fixed-duration Env.linen
            # Duration param is ignored with linen (envelope is always 8+20+12=40s)
            instrument.play_note(freq, volume, 1.0, blocking=False)
            print(f"[BACKGROUND #{iteration}] Note triggered successfully, waiting 40s...")
            
            # Wait for full envelope: 8s attack + 20s sustain + 12s release = 40s total
            wait(40.0, units="time")
            
            # Decrement counter when pad finishes
            self.active_pad_count = max(0, self.active_pad_count - 1)
            elapsed = time.time() - start_time
            print(f"[BACKGROUND #{iteration}] Pad complete after {elapsed:.1f}s, active_pads now {self.active_pad_count}")
        except Exception as e:
            self.active_pad_count = max(0, self.active_pad_count - 1)
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
        
        # Diagnostics
        self.tick_counter = 0
        self.diagnostic_interval = 150  # Print every 150 ticks (~10 seconds at 15Hz)

    def __repr__(self):
        """String representation of the pillar for debugging."""
        return f"Pillar({self.pillar_id}) {self.state}"
    
    def update_pillar_setting(self, setting_name, value, extra_arg=None):
        """Updates the settings dictionary for a specific pillar."""
        self.composer.update(setting_name, value, extra_arg)

    def tick(self, time_delta=1/15.0):  # Reduced from 30Hz to 15Hz to lower overhead
        self.tick_counter += 1
        
        # Periodic diagnostics
        #if self.tick_counter % self.diagnostic_interval == 0:
        #    print(f"\n{'='*60}")
        #    print(f"[TICK #{self.tick_counter}] Periodic diagnostic")
        #    print(f"  Active pads: {self.composer.active_pad_count}/{self.composer.max_concurrent_pads}")
        #    print(f"  Background fork alive: {self.composer.active_forks['background'].alive}")
            
        
        # Check if background fork is still alive
        if not self.composer.active_forks["background"].alive:
            print(f"\n{'!'*60}")
            print(f"[TICK #{self.tick_counter}]  CRITICAL: Background fork died! Restarting...")
            print_server_info("[FORK DEATH]")
            print(f"{'!'*60}\n")
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

    
