from scamp import Session, wait, current_clock
import scamp_extensions.process as seprocess
import expenvelope as expe
 
import multiprocessing as mp
from queue import Queue
import random
import numpy as np
import copy
import time
import threading

from interfaces import *

class InstrumentManager:

    def __init__(self, session):
        self.session = session

        self.instrument_names= {
            "melody": None,
            "harmony": None,
            "background": None
        }

        self.instruments = {
            "melody": None,
            "harmony": None,
            "background": None
        }

    def update_instrument(self, instrument_name, function="melody"):
        print(f"[DEBUG] Sound Manager updating {function} instrument to {instrument_name}")
        if self.instrument_names[function] == instrument_name:
            return
        
        if self.instrument_names[function] is not None:
            # Remove Existing Instrument
            current_instruments = [i.name for i in self.session.instruments]
            idx = list(current_instruments).index(self.instrument_names[function])
            self.session.pop_instrument(idx)
            print(f"[DEBUG] Previous instrument removed: {self.instrument_names[function]}")
            
        self.instruments[function] = self.session.new_part(instrument_name)
        self.instrument_names[function] = instrument_name
        print(f"[DEBUG] New instrument added: {self.instrument_names[function]}")

    def melody_instrument(self):
        return self.instruments["melody"]

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
            "chord_levels": self.mp_manager.Value('d', 0)
        }

        self.active_forks = {
            "melody": None,
            "harmony": None,
            "background": None
        }
        
        # Track active reaction notes for debugging and max duration control
        self.active_reaction_notes = {}  # {note_id: {"note": note, "start_time": timestamp}}
        self.max_note_duration = 3.0  # Maximum duration in seconds for reaction notes
        
        # Create a thread to monitor and terminate long-running notes
        self.note_monitor_thread = threading.Thread(target=self.monitor_active_notes, daemon=True)
        self.note_monitor_thread.start()
        
        print("[DEBUG] Composer initialized with instruments:", self.state["instruments"])

    def monitor_active_notes(self):
        """Thread function to monitor active notes and terminate those that exceed max duration"""
        while True:
            current_time = time.time()
            notes_to_remove = []
            
            # Check all active notes
            for note_id, note_info in self.active_reaction_notes.items():
                if current_time - note_info["start_time"] > self.max_note_duration:
                    # Note has exceeded max duration, mark for removal
                    notes_to_remove.append(note_id)
                    print(f"[DEBUG] Terminating long-running note {note_info['note']} (exceeded {self.max_note_duration}s)")
            
            # Remove expired notes
            for note_id in notes_to_remove:
                del self.active_reaction_notes[note_id]
            
            # Sleep to avoid excessive CPU usage
            time.sleep(0.5)

    def update(self, setting_name, value):
        print(f"[DEBUG] Updating {setting_name} with value: {value}")

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
                print(f"[DEBUG] Setting tempo target to {value}")
                self.session.set_tempo_target(value, 0.2)
            if setting_name == "reaction_notes":
                # Clear previous reaction note forks
                for note_id in list(self.active_reaction_notes.keys()):
                    print(f"[DEBUG] Clearing previous note: {self.active_reaction_notes[note_id]['note']}")
                    del self.active_reaction_notes[note_id]
                
                # Start new note forks
                for i, note in enumerate(value):
                    print(f"[DEBUG] Playing reaction note: {note}")
                    note_id = f"note_{time.time()}_{i}"
                    self.active_reaction_notes[note_id] = {
                        "note": note,
                        "start_time": time.time()
                    }
                    self.session.fork(self.fork_melody_single_note, args=(note, note_id))
            
    def update_instruments(self, instruments):
        for k,v in instruments.items():
            self.instrument_manager.update_instrument(v, function=k)

    def update_key(self, key):
        print(f"[DEBUG] Updating key to {key}")
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
        # self.start_fork("melody", self.fork_melody)
        self.start_fork("harmony", self.fork_harmony)
        self.start_fork("background", self.fork_background)
        
    def clear_active_notes(self):
        """Clear all active reaction notes"""
        print(f"[DEBUG] Clearing all active notes. Count: {len(self.active_reaction_notes)}")
        self.active_reaction_notes.clear()
        
    def start_fork(self, function_name, function):
        # If a fork is active or not alive, then start the new fork
        if self.active_forks[function_name] is None or not self.active_forks[function_name].alive:
            print(f"[DEBUG] Starting fork: {function_name}")
            self.active_forks[function_name] = self.session.fork(function, args=(self.shared_state,))
    
    def fork_melody_single_note(self, note, note_id=None):
        volume = self.state["volume"]["melody"]
        
        # Make sure the melody instrument exists and is initialized
        if self.instrument_manager.melody_instrument() is None:
            print("[DEBUG] Initializing melody instrument because it doesn't exist")
            self.instrument_manager.update_instrument(self.state["instruments"]["melody"], function="melody")
            
        instrument = self.instrument_manager.melody_instrument()
        
        # Only play the note if it's still in active_reaction_notes
        if note_id is None or note_id in self.active_reaction_notes:
            # Print more visible message to confirm note is being played
            print(f"[DEBUG] PLAYING NOTE: {note} with volume {volume} on {instrument.name}")
            
            # Test with different envelope to make sure we hear it
            try:
                # Use a longer duration with non-blocking to make the note more audible
                # Add articulation to make it more pronounced
                instrument.play_note(note, volume, 1.0, "marcato", blocking=False)
                
                # If we have a note_id, remove it from active notes after playing
                if note_id and note_id in self.active_reaction_notes:
                    # Wait a short time then remove the note
                    wait(1.1, units="time")
                    if note_id in self.active_reaction_notes:
                        del self.active_reaction_notes[note_id]
                        print(f"[DEBUG] Note {note} completed normally")
            except Exception as e:
                print(f"[ERROR] Failed to play note {note}: {e}")
                # Try again with simpler parameters
                try:
                    instrument.play_note(note, volume, 1.0, blocking=True)
                except Exception as e2:
                    print(f"[ERROR] Failed again: {e2}")

    def fork_melody(self, shared_state):        
        # Generate initial note
        scale = SCALE_TYPES[self.state["melody_scale"]](self.shared_state["key"].value)
        melody_num = self.state["melody_number"]
        melody = MELODIES[melody_num]
        
        volume = self.state["volume"]["melody"]
        instrument = self.instrument_manager.melody_instrument()
        for n, d in melody:
            if n is None:
                note = None
            else:
                note = scale.degree_to_pitch(n)
            instrument.play_note(note, volume, d, blocking=True)

    def fork_harmony(self, shared_state):
        # Skip completely if harmony_enabled is False
        if hasattr(self, 'harmony_enabled') and not self.harmony_enabled:
            print("[DEBUG] Harmony playback skipped - disabled")
            return
        
        # Also check volume directly as a backup
        if hasattr(self, 'harmony_volume') and self.harmony_volume == 0:
            print("[DEBUG] Harmony playback skipped - volume is 0")
            return
        
        instrument = self.instrument_manager.harmony_instrument()
        key = next(self.key_generator)
        print(f"[DEBUG] Harmony using key: {key}")
        scale = list(SCALE_TYPES[self.state["melody_scale"]](key))

        # Add 7/9/11/13 etc depending on chord_levels
        chord_levels = min(shared_state["chord_levels"].value, 2)  # Limit complexity

        chord = []
        gen_chords = [0, 2, 4] + [6 + 2*chord_levels*i for i in range(chord_levels)]
        for offset in gen_chords:
            if offset >= len(scale):
                new_offset = offset % len(scale)
                number_up = offset // len(scale)
                note = scale[new_offset] + number_up * 12
            else:
                note = scale[offset]
            chord.append(int(note))

        # Adjust voicings
        random.shuffle(chord)
        key_idx = chord.index(key)
        chord = np.array(chord)
        chord[key_idx:] += 12 # If some of the chords are below tonic, shift down octave
        
        volume = self.state["volume"]["harmony"]
        
        # Create a short attack/decay to avoid long sustained harmony
        envelope = expe.envelope.Envelope.adsr(0.1, volume, 0.3, 0.4, 0.15, 0.2)
        
        # Reduce duration from 4.0 to 2.0 to avoid long sustained harmony
        print(f"[DEBUG] Playing harmony chord: {chord} for 2.0 seconds")
        instrument.play_chord(chord, envelope, 2.0, blocking=True)

        if chord_levels > 0:
            shared_state["chord_levels"].value -= 1

        shared_state["key"].value = key

    def fork_background(self, shared_state):
        instrument = self.instrument_manager.background_instrument()
        volume = self.state["volume"]["background"]
        
        # Add bassline patterns based on current scale
        bassline_patterns = {
            "walking": [0, 3, 5, 7],
            "boogie": [0, 0, 7, 0],
            "octave": [0, 12, 7, 12],
            "fifth": [0, 7, 0, 7],
            "arpeggios": [0, 4, 7, 12],
        }
        
        # Track which pattern we're using
        current_pattern = random.choice(list(bassline_patterns.keys()))
        
        # Track when melody last changed
        last_melody_change = time.time()
        last_melody_number = self.state["melody_number"]
        fill_played = False
        
        while True:
            # Get base note
            note = shared_state["key"].value - 24  # 2 octaves below the current key
            
            # Check if melody has changed
            current_time = time.time()
            if last_melody_number != self.state["melody_number"]:
                last_melody_change = current_time
                last_melody_number = self.state["melody_number"]
                fill_played = False
            
            # Determine if we should play a fill
            melody_static_duration = current_time - last_melody_change
            should_play_fill = melody_static_duration > 10.0 and not fill_played
            
            if should_play_fill:
                # Play a fill since melody hasn't changed in over 10 seconds
                print(f"Playing background fill - melody static for {melody_static_duration:.1f}s")
                
                # Create a fill pattern that's musically interesting
                fill_notes = [note, note+7, note+12, note+7, note+5, note+7, note+3, note]
                
                # Play the fill with a different articulation
                for fill_note in fill_notes:
                    instrument.play_note(fill_note, volume * 1.1, 0.5, "marcato", blocking=True)
                
                # Mark that we've played a fill
                fill_played = True
                
                # Optionally change the pattern after a fill
                current_pattern = random.choice(list(bassline_patterns.keys()))
                
            else:
                # Get the current bassline pattern
                pattern = bassline_patterns[current_pattern]
                
                if self.state["baseline_style"] == "long":
                    # For long style, play a sustained note but with the bassline pattern
                    # as subtle changes in pitch
                    for offset in pattern:
                        bass_note = note + offset
                        # Shorter duration for each note in the pattern
                        duration = 4.0 * 4 / len(pattern)
                        instrument.play_note(bass_note, volume, duration, blocking=True)
                    
                elif self.state["baseline_style"] == "pulsing":
                    # For pulsing, apply the pattern with tremolo effect
                    for offset in pattern:
                        bass_note = note + offset
                        duration = 4.0 * 4 / len(pattern)
                        instrument.play_note(bass_note, volume, duration, "tremolo", blocking=True)
                    
                else:  # "beat" style
                    # For beat style, play staccato notes following the pattern
                    for offset in pattern:
                        bass_note = note + offset
                        instrument.play_note(bass_note, volume, 0.5, "staccato", blocking=True)
                        wait(0.5)
                
                # Occasionally change the pattern (10% chance)
                if random.random() < 0.1:
                    new_pattern = random.choice(list(bassline_patterns.keys()))
                    if new_pattern != current_pattern:
                        print(f"Changing bassline pattern from {current_pattern} to {new_pattern}")
                        current_pattern = new_pattern


class SoundManager:
    """Manages and schedules sound playback for pillars using the Sonic Pi server."""          
    
    def __init__(self, pillar_id, initial_state=None):
        self.pillar_id = pillar_id

        self.session = Session()
        # Turn off synchronization to prevent clock delay warnings
        current_clock().synchronization_policy = "no synchronization"
        
        self.state = initial_state if initial_state is not None else DEFAULT_STATE

        self.composer = Composer(self.session, self.state)
        
        # Explicitly initialize all instruments to make sure they exist
        print("[DEBUG] Explicitly initializing all instruments")
        for layer in ["melody", "harmony", "background"]:
            instrument_name = self.state["instruments"][layer]
            self.composer.instrument_manager.update_instrument(instrument_name, function=layer)
        
        # Track the last time reaction notes were cleared
        self.last_clear_time = time.time()
        self.clear_interval = 5.0  # Clear reaction notes every 5 seconds
        
        # Force update volume settings to ensure they're applied
        self.update_pillar_setting("volume", self.state.default_state["volume"])
        print(f"[DEBUG] Initial volumes set from default state: {self.state.default_state['volume']}")
        
        # Test the sound engine with simple commands
        print("[SOUND] Testing sound engine...")
        try:
            # Try to create a basic instrument and play a note
            from scamp import Session, wait
            test_session = Session()
            piano = test_session.new_part("piano")
            
            # Play a simple middle C
            print("[SOUND] Playing test note (middle C)")
            piano.play_note(60, 0.8, 1.0)
            wait(1)
            print("[SOUND] Test completed successfully")
        except Exception as e:
            print(f"[SOUND ERROR] Sound engine test failed: {e}")
        
        # Call this in __init__ after loading config
        self.diagnostics()
        
        print(f"[DEBUG] SoundManager initialized for pillar: {pillar_id}")

    def __repr__(self):
        """String representation of the pillar for debugging."""
        return f"Pillar({self.pillar_id}) {self.state}"
    
    def update_pillar_setting(self, param_name, value):
        """Updates the settings dictionary for a specific pillar."""
        print(f"[DEBUG] Updating sound parameter: {param_name} = {value}")
        
        # Special handling for reaction_notes (melody triggers)
        if param_name == "reaction_notes" and value:
            print(f"[MELODY] Attempting to play notes: {value}")
            # Set a flag to verify notes were processed
            self.last_notes_received = time.time()
            self.last_notes = value
        
        self.composer.update(param_name, value)

    def tick(self, time_delta=1/30.0):
        # Check if we need to clear reaction notes
        current_time = time.time()
        if current_time - self.last_clear_time > self.clear_interval:
            print("[DEBUG] Periodic reaction notes clearing")
            self.composer.clear_active_notes()
            self.last_clear_time = current_time
            
        self.composer.play()
        wait(time_delta, units="time")

    def get_pillar_settings(self):
        """Return the current sound settings."""
        # Getting the actual values from the composer or wherever they're stored
        settings = {
            "volume": {
                "melody": getattr(self.composer, "melody_volume", "unknown"),
                "harmony": getattr(self.composer, "harmony_volume", "unknown"),
                "background": getattr(self.composer, "background_volume", "unknown")
            },
            "harmony_enabled": getattr(self.composer, "harmony_enabled", "unknown"),
            # Add other relevant settings
        }
        return settings

    def test_note(self):
        """Test function to play a simple note."""
        print("[TEST] Playing test note (middle C)")
        try:
            # Direct play using SCAMP
            from scamp import Session, wait
            
            # Use a new session to avoid interfering with main one
            test_session = Session()
            test_session.tempo = 60
            
            piano = test_session.new_part("piano")
            piano.play_note(60, 0.8, 1.0)  # Middle C, 80% volume, 1 second
            wait(1)
            print("[TEST] Test note completed")
            return True
        except Exception as e:
            print(f"[TEST] Error playing test note: {e}")
            return False

    def diagnostics(self):
        """Run diagnostic checks on the sound system"""
        print("\n=== SOUND SYSTEM DIAGNOSTICS ===")
        print(f"Melody volume: {getattr(self.composer, 'melody_volume', 'unknown')}")
        print(f"Harmony volume: {getattr(self.composer, 'harmony_volume', 'unknown')}")
        print(f"Background volume: {getattr(self.composer, 'background_volume', 'unknown')}")
        print(f"Sound engine active: {self.composer.is_active()}")
        print(f"Instrument settings: {getattr(self.composer, 'instruments', 'unknown')}")
        print("=================================\n")

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

    