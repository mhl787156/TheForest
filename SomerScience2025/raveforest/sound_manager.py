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
import json
import os
import traceback

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    print("[SOUND] psutil not available - process priority adjustment will be skipped")
    HAS_PSUTIL = False

try:
    from scamp import Session, wait, current_clock
    import scamp_extensions.process as seprocess
    import expenvelope as expe
    HAS_SCAMP = True
except ImportError:
    print("[CRITICAL] SCAMP library not found - sound functionality will be disabled")
    HAS_SCAMP = False

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
            try:
                # Remove Existing Instrument
                current_instruments = [i.name for i in self.session.instruments]
                idx = list(current_instruments).index(self.instrument_names[function])
                self.session.pop_instrument(idx)
                print(f"[DEBUG] Previous instrument removed: {self.instrument_names[function]}")
            except Exception as e:
                print(f"[WARNING] Could not remove previous instrument: {e}")
        
        try:    
            self.instruments[function] = self.session.new_part(instrument_name)
            self.instrument_names[function] = instrument_name
            print(f"[DEBUG] New instrument added: {self.instrument_names[function]}")
        except Exception as e:
            print(f"[ERROR] Failed to add new instrument {instrument_name}: {e}")
            self.instruments[function] = None
            self.instrument_names[function] = None

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
        
        # Skip if melody volume is 0
        if volume == 0:
            print(f"[DEBUG] Skipping note {note} - melody volume is 0")
            return
        
        # Cache the instrument for faster access
        if not hasattr(self, '_melody_instrument_cache'):
            self._melody_instrument_cache = self.instrument_manager.melody_instrument()
            if self._melody_instrument_cache is None:
                print("[DEBUG] Initializing melody instrument because it doesn't exist")
                self.instrument_manager.update_instrument(self.state["instruments"]["melody"], function="melody")
                self._melody_instrument_cache = self.instrument_manager.melody_instrument()
        
        instrument = self._melody_instrument_cache
        
        # Record time to measure latency
        start_time = time.time()
        
        # Use very short duration for immediate response
        try:
            # Non-blocking with shorter duration for faster response
            # instrument.play_note(note, volume, 0.5, "staccato", blocking=False) # Old short staccato
            # Play longer note without staccato
            instrument.play_note(note, volume, 1, blocking=False)
            print(f"[SOUND] ⚡ Note {note} started at {start_time:.3f}, latency: {time.time() - start_time:.3f}s")
        except Exception as e:
            print(f"[ERROR] Failed to play note {note}: {e}")
            # Try simpler approach as fallback
            try:
                # instrument.play_note(note, volume, 0.2, blocking=False) # Old fallback
                instrument.play_note(note, volume, 1.0, blocking=False) # Longer fallback
            except Exception as e2:
                print(f"[ERROR] Fallback play failed: {e2}")

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
        # Skip completely if harmony_enabled is False or volume is 0
        if hasattr(self, 'harmony_enabled') and not self.harmony_enabled:
            print("[DEBUG] Harmony playback skipped - disabled")
            return
        
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
    """Class to manage the sound output for a pillar"""
    
    def __init__(self, pillar_id=0):
        """Initializes the sound manager"""
        print(f"Initializing SoundManager for pillar: {pillar_id}")
        self.pillar_id = pillar_id

        # Load configuration with proper defaults
        default_state = {
            "volume": {"melody": 0.9, "harmony": 0.0, "background": 0.5},
            "instruments": {"melody": "xylophone", "harmony": "flute", "background": "strings"},
            "key": 60,
            "bpm": 100,
            "melody_scale": "pentatonic",
            "melody_number": 0,
            "baseline_style": "long",
            "chord_levels": 0,
            "reaction_notes": []
        }
        
        try:
            self.state = default_state
            
            # Initialize attributes with defaults - ensures they exist even if errors occur
            self._instruments_cache = {}
            self._direct_instrument = None
            self.last_notes_played = []
            self.last_play_time = 0
            self.debounce_time = 0.05
            self.last_clear_time = time.time()
            self.clear_interval = 5.0
            
            # Initialize SCAMP session with proper error handling
            self.session = None
            if HAS_SCAMP:
                try:
                    print("[SOUND] Initializing SCAMP session...")
                    self.session = Session()
                    
                    # Set basic tempo but handle version differences
                    self.session.tempo = 120  # Higher tempo can reduce perceived latency
                    
                    # Check if set_synchronization_mode exists before calling it
                    if hasattr(self.session, 'set_synchronization_mode'):
                        self.session.set_synchronization_mode('loose')  # Use looser synchronization for lower latency
                        print(f"[SOUND] SCAMP session initialized with loose synchronization")
                    else:
                        print("[SOUND] SCAMP session initialized (set_synchronization_mode not available in this version)")
                    
                    # CRITICAL: Instrument preloading
                    try:
                        self._preload_instruments()
                        print("[SOUND] Instrument preloading completed successfully")
                    except Exception as preload_error:
                        print(f"[ERROR] Instrument preloading failed: {preload_error}")
                        self._direct_instrument = None
                except Exception as e:
                    print(f"[ERROR] Failed to initialize SCAMP session: {e}")
                    print(f"[DEBUG] SCAMP exception details: {traceback.format_exc()}")
                    self.session = None
            else:
                print("[ERROR] SCAMP libraries not available - sound functionality disabled")
                self.session = None
                
            # Setup sound composer with proper state
            self.composer = None
            if self.session is not None:
                try:
                    print("[SOUND] Creating sound composer...")
                    self.composer = Composer(self.session, default_state)
                    
                    # Explicitly set volume properties
                    self.composer.melody_volume = default_state["volume"]["melody"]
                    self.composer.harmony_volume = default_state["volume"]["harmony"]
                    self.composer.background_volume = default_state["volume"]["background"]
                    self.composer.harmony_enabled = False  # Explicitly disable harmony
                    
                    print(f"[SOUND] Volumes set - melody: {self.composer.melody_volume}, harmony: {self.composer.harmony_volume}")
            
                    # Explicitly set melody instrument to xylophone after composer creation
                    try:
                        print("[SOUND] Ensuring melody instrument is xylophone for reaction notes.")
                        self.composer.instrument_manager.update_instrument("xylophone", function="melody")
                    except Exception as inst_err:
                        print(f"[ERROR] Failed to set initial melody instrument: {inst_err}")
                except Exception as e:
                    print(f"[ERROR] Failed to create sound composer: {e}")
                    print(f"[DEBUG] Composer exception details: {traceback.format_exc()}")
                    self.composer = None
            else:
                print("[ERROR] Cannot create composer - no valid session")
                self.composer = None
            
            # Set process priority if psutil is available
            if HAS_PSUTIL:
                try:
                    process = psutil.Process(os.getpid())
                    # Check for platform-specific priority constants
                    if hasattr(psutil, 'ABOVE_NORMAL_PRIORITY_CLASS'):
                        process.nice(psutil.ABOVE_NORMAL_PRIORITY_CLASS)
                    else:
                        # On Unix systems, use negative nice values for higher priority
                        process.nice(-10)  # Higher priority on Unix systems
                    print("[SOUND] Increased process priority for better audio performance")
                except Exception as e:
                    print(f"[SOUND] Failed to set process priority: {e}")
        except Exception as e:
            print(f"[CRITICAL] Sound manager initialization failed: {e}")
            print(f"[DEBUG] Initialization traceback: {traceback.format_exc()}")
            
        print(f"SoundManager initialization complete for pillar: {pillar_id}")
        
        # Verify initialization
        self.verify_initialization()
    
    def _preload_instruments(self):
        """OPTIMIZATION: Pre-initialize all instruments we'll need"""
        try:
            # Pre-create instruments for faster access during performance
            print("[SOUND] Pre-initializing instruments for lower latency")
            
            # CRITICAL: Create dedicated instrument for direct note playing
            # This avoids any initialization delay when a touch happens
            self._direct_instrument = self.session.new_part("xylophone")
            print("[SOUND] Created dedicated fast-response instrument")
            
            # Cache other commonly used instruments
            instruments = ["piano", "flute", "strings", "synth", "glockenspiel"]
            for name in instruments:
                try:
                    instrument = self.session.new_part(name)
                    self._instruments_cache[name] = instrument
                    print(f"[SOUND] Pre-loaded instrument: {name}")
                except Exception as e:
                    print(f"[SOUND] Failed to pre-load {name}: {e}")
                    
        except Exception as e:
            print(f"[ERROR] Failed in instrument preloading: {e}")

    def run_diagnostics(self):
        """Run sound system diagnostics"""
        print("\n=== SOUND SYSTEM DIAGNOSTICS ===")
        print(f"Melody volume: {getattr(self.composer, 'melody_volume', 'unknown')}")
        print(f"Harmony volume: {getattr(self.composer, 'harmony_volume', 'unknown')}")
        print(f"Background volume: {getattr(self.composer, 'background_volume', 'unknown')}")
        print(f"Instrument settings: {getattr(self.composer, 'instruments', {})}")
        
        # Test sound output
        self.test_sound()
        print("=================================\n")
    
    def test_sound(self):
        """Test if sound output is working"""
        print("[TEST] Playing test note...")
        try:
            if self.session is not None:
                try:
                    piano = self.session.new_part("piano")
                    piano.play_note(60, 0.5, 0.5)  # Play middle C
                    from scamp import wait
                    wait(0.5)
                    print("[TEST] Test note completed")
                    return True
                except Exception as e:
                    print(f"[ERROR] Failed to play test note with piano: {e}")
            else:
                print("[ERROR] Cannot play test note - no valid session")
            return False
        except Exception as e:
            print(f"[ERROR] Failed in test_sound method: {e}")
            return False
    
    def verify_initialization(self):
        """Verify that the sound manager is initialized correctly"""
        if self.session is None:
            print("[ERROR] SoundManager initialization failed - no valid session")
            return False
        if self.composer is None:
            print("[ERROR] SoundManager initialization failed - no valid composer")
            return False
        return True
    
    def ensure_direct_instrument(self):
        """Ensure the direct instrument is ready for playback"""
        if hasattr(self, '_direct_instrument') and self._direct_instrument is not None:
            return True  # Already initialized
            
        print("[SOUND] Setting up direct instrument...")
        try:
            if hasattr(self, 'session') and self.session is not None:
                # Try to create the instrument directly - prioritize responsive instruments
                try:
                    # Xylophone is generally more responsive with clear attack
                    self._direct_instrument = self.session.new_part("xylophone")
                    print("[SOUND] Direct xylophone instrument created for responsive playback")
                    return True
                except Exception:
                    # Fallback to piano if xylophone fails
                    try:
                        self._direct_instrument = self.session.new_part("piano")
                        print("[SOUND] Direct piano instrument created (fallback)")
                        return True
                    except Exception as e:
                        print(f"[ERROR] Failed to create standard instruments: {e}")
                        
                # Last-resort fallback: try to create any available instrument
                try:
                    # Get all available instruments
                    available_instruments = getattr(self.session, 'available_instruments', 
                                               ["piano", "xylophone", "marimba", "glockenspiel"])
                    
                    # Try instruments one by one until one works
                    for inst_name in available_instruments:
                        try:
                            self._direct_instrument = self.session.new_part(inst_name)
                            print(f"[SOUND] Created fallback instrument: {inst_name}")
                            return True
                        except Exception:
                            continue
                            
                    # If we get here, none of the instruments worked
                    print("[ERROR] Failed to create any instrument")
                    return False
                except Exception as e:
                    print(f"[ERROR] Fallback instrument creation failed: {e}")
                    return False
            else:
                print("[ERROR] Cannot create direct instrument - no valid session")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to create direct instrument: {e}")
            return False

    def update_pillar_setting(self, param_name, value):
        """Updates the settings dictionary for a specific pillar."""
        print(f"[SOUND] Updating parameter: {param_name} = {value}")
        
        # First check if composer is properly initialized
        if self.composer is None:
            print("[ERROR] Cannot update settings - composer not initialized")
            # Try to reinitialize the composer
            try:
                if self.session is not None:
                    print("[SOUND] Attempting to recreate composer...")
                    self.composer = Composer(self.session, self.state)
                    print("[SOUND] Successfully recreated composer")
                else:
                    print("[ERROR] Cannot recreate composer - no valid session")
                    return
            except Exception as e:
                print(f"[ERROR] Failed to recreate composer: {e}")
                return
        
        try:
            # Special handling for volume settings
            if param_name == "volume":
                # Store current values before updating
                self.composer.update(param_name, value)
                
                # Explicitly handle harmony silencing when volume is 0
                if "harmony" in value and value["harmony"] == 0:
                    print("[SOUND] Explicitly disabling harmony (volume=0)")
                    self.composer.harmony_enabled = False
                else:
                    self.composer.harmony_enabled = True
            
            # Special handling for reaction notes
            elif param_name == "reaction_notes" and value:
                print(f"[SOUND] Playing reaction notes: {value}")
                
                # Ensure melody instrument is initialized and working
                instrument_name = self.state["instruments"]["melody"]
                if self.composer.instrument_manager.melody_instrument() is None:
                    print(f"[FIX] Reinitializing melody instrument '{instrument_name}'")
                    self.composer.instrument_manager.update_instrument(instrument_name, function="melody")
                
                # Test direct note generation for debugging
                self.play_direct_notes(value)
            
            # Default handling for other parameters
            else:
                self.composer.update(param_name, value)
                
        except Exception as e:
            print(f"[ERROR] Failed to update parameter {param_name}: {e}")
            # Try to recover the composer if needed
            if self.composer is None:
                print("[RECOVERY] Attempting to restore composer...")
                self.verify_initialization()

    def play_direct_notes(self, notes, tube_note_mapping=None):
        """
        ULTRA LOW LATENCY direct note player - optimized for minimal delay
        Bypass all normal processing for the fastest possible response time.
        
        Args:
            notes: List of MIDI note numbers to play
            tube_note_mapping: Dict mapping tube_id to note, used to track and stop notes from the same tube
        """
        if not notes:
            return False
            
        # Track notes by tube for proper note management
        if tube_note_mapping is None:
            tube_note_mapping = {}
            
        # Skip debounce check to always respond to touches immediately
        now = time.time()
        self.last_play_time = now
        
        # Get starting timestamp for latency measurement
        start_time = time.time()
        print(f"[⚡FAST] Playing {len(notes)} notes: {notes}, from tubes: {list(tube_note_mapping.keys())}")
        
        try:
            # Phase 1: Get or create the direct instrument
            # Make sure we have a direct instrument 
            if not hasattr(self, '_direct_instrument') or self._direct_instrument is None:
                print("[FIX] Direct instrument not available - creating one")
                success = self.ensure_direct_instrument()
                if not success:
                    # If we couldn't create a direct instrument, try using the composer's instrument
                    print("[FIX] Falling back to composer's instrument")
                    if hasattr(self, 'composer') and self.composer is not None:
                        try:
                            self._direct_instrument = self.composer.instrument_manager.melody_instrument()
                            if self._direct_instrument is None:
                                self.composer.instrument_manager.update_instrument("xylophone", function="melody")
                                self._direct_instrument = self.composer.instrument_manager.melody_instrument()
                        except Exception as e:
                            print(f"[ERROR] Fallback to composer instrument failed: {e}")
            
            # Phase 2: Play notes using the available instrument
            if hasattr(self, '_direct_instrument') and self._direct_instrument is not None:
                # Our primary instrument is available
                instrument = self._direct_instrument
                print(f"[SOUND] Using direct instrument for playback")
            elif hasattr(self, 'composer') and self.composer is not None:
                # Try the composer's instrument as backup
                instrument = self.composer.instrument_manager.melody_instrument()
                print(f"[SOUND] Using composer instrument for playback")
            elif hasattr(self, 'session') and self.session is not None:
                # Last resort - create a one-time instrument
                print(f"[SOUND] Creating one-time emergency instrument")
                instrument = self.session.new_part("piano")
            else:
                print("[ERROR] No valid instrument or session available")
                return False
            
            # Initialize structure for tracking active notes by tube if it doesn't exist
            if not hasattr(self, '_active_tube_notes'):
                self._active_tube_notes = {}
                
            # Also track active notes by their pitch value (for instruments without end_note)
            if not hasattr(self, '_active_notes'):
                self._active_notes = {}
                
            # Phase 3: Play each note with maximal reliability
            volume = 1.0  # Maximum volume
            success_count = 0
            
            # First check if end_note is supported by the instrument
            has_end_note = hasattr(instrument, 'end_note')
            
            # For each tube in the mapping, stop previous notes if needed
            for tube_id, note in tube_note_mapping.items():
                # Stop previous note on this tube if one exists
                if tube_id in self._active_tube_notes:
                    try:
                        previous_note = self._active_tube_notes[tube_id]
                        
                        # Try to stop the note using the most appropriate method
                        if has_end_note:
                            print(f"[SOUND] Stopping previous note {previous_note} on tube {tube_id}")
                            instrument.end_note(previous_note)
                        elif hasattr(instrument, 'stop_note'):
                            # Alternative method in some SCAMP versions
                            print(f"[SOUND] Stopping previous note {previous_note} using stop_note")
                            instrument.stop_note(previous_note)
                        elif hasattr(self, '_active_notes') and previous_note in self._active_notes:
                            # Try to release the note in the _active_notes dictionary
                            # Mark it for release by setting its volume to 0
                            print(f"[SOUND] Marking previous note {previous_note} for release")
                            self._active_notes[previous_note]['releasing'] = True
                            
                            # Play a zero-volume note to "cut off" the previous one (hack)
                            try:
                                instrument.play_note(previous_note, 0, 0.01, blocking=False)
                            except Exception as e:
                                print(f"[WARNING] Failed to cut off note with zero volume: {e}")
                    except Exception as stop_error:
                        print(f"[WARNING] Failed to stop previous note: {stop_error}")
                
                # Store the new active note for this tube
                self._active_tube_notes[tube_id] = note
            
            # Play each note with minimal latency
            for note in notes:
                try:
                    # Use non-blocking to maximize responsiveness
                    # Use a longer duration for better sound quality (1.5 seconds)
                    instrument.play_note(note, volume, 1, blocking=False)
                    
                    # Track this note with its start time for future management
                    self._active_notes[note] = {
                        'start_time': now,
                        'releasing': False,
                        'volume': volume
                    }
                    
                    success_count += 1
                    
                    # Calculate latency but don't wait for it
                    latency_ms = (time.time() - start_time) * 1000
                    print(f"[⚡LATENCY] Note {note} triggered in {latency_ms:.1f}ms")
                except Exception as note_error:
                    print(f"[ERROR] Note {note} failed: {note_error}")
            
            # Clean up old notes from tracking dictionary to prevent memory leaks
            # Only keep notes that started in the last 10 seconds
            if hasattr(self, '_active_notes'):
                old_notes = []
                for note, info in self._active_notes.items():
                    if now - info['start_time'] > 10.0:
                        old_notes.append(note)
                
                for note in old_notes:
                    if note in self._active_notes:
                        del self._active_notes[note]
            
            # Return success if we played at least one note
            return success_count > 0
            
        except Exception as e:
            print(f"[ERROR] Note playback system completely failed: {e}")
            # If EVERYTHING else failed, create a completely new session as absolute last resort
            try:
                if HAS_SCAMP:
                    emergency_session = Session()
                    emergency_instrument = emergency_session.new_part("piano")
                    for note in notes:
                        emergency_instrument.play_note(note, 1.0, 0.2, blocking=False)
                    print("[EMERGENCY] Created completely new session for last-resort playback")
                    return True
                return False
            except Exception as final_error:
                print(f"[FATAL] Complete system failure: {final_error}")
                return False
                
    def stop_notes(self, tubes):
        """
        Stop notes for specific tubes when they are released
        
        Args:
            tubes: List of tube IDs to stop notes for
            
        Returns:
            bool: True if at least one note was stopped
        """
        if not tubes:
            return False
            
        print(f"[SOUND] Stopping notes for tubes: {tubes}")
        
        # Get the current instrument
        instrument = None
        if hasattr(self, '_direct_instrument') and self._direct_instrument is not None:
            instrument = self._direct_instrument
        elif hasattr(self, 'composer') and self.composer is not None:
            instrument = self.composer.instrument_manager.melody_instrument()
        elif hasattr(self, 'session') and self.session is not None:
            # Last resort - create a one-time instrument
            try:
                instrument = self.session.new_part("piano")
            except Exception as e:
                print(f"[ERROR] Failed to create emergency instrument: {e}")
        
        if instrument is None:
            print("[ERROR] No valid instrument available to stop notes")
            return False
            
        # Check if we have active tube notes to stop
        if not hasattr(self, '_active_tube_notes'):
            print("[WARNING] No active tube notes to stop")
            return False
            
        # Track success
        success_count = 0
        
        # Check if end_note or stop_note is supported
        has_end_note = hasattr(instrument, 'end_note')
        has_stop_note = hasattr(instrument, 'stop_note')
        
        # For each tube, stop its note if it exists
        for tube_id in tubes:
            if tube_id in self._active_tube_notes:
                try:
                    note = self._active_tube_notes[tube_id]
                    print(f"[SOUND] Stopping note {note} for tube {tube_id}")
                    
                    # Try to stop the note using the most appropriate method
                    if has_end_note:
                        instrument.end_note(note)
                        success_count += 1
                    elif has_stop_note:
                        instrument.stop_note(note)
                        success_count += 1
                    elif hasattr(self, '_active_notes') and note in self._active_notes:
                        # Mark it for release using zero volume
                        self._active_notes[note]['releasing'] = True
                        
                        # Play a zero-volume note to "cut off" the previous one
                        try:
                            instrument.play_note(note, 0, 0.01, blocking=False)
                            success_count += 1
                        except Exception as e:
                            print(f"[WARNING] Failed to stop note with zero volume: {e}")
                    
                    # Remove the note from active tube notes regardless of success
                    del self._active_tube_notes[tube_id]
                    
                except Exception as e:
                    print(f"[ERROR] Failed to stop note for tube {tube_id}: {e}")
        
        return success_count > 0

    def manage_active_notes(self):
        """
        Manage the lifecycle of active notes - release old notes, clean up memory
        This should be called periodically from the tick method
        """
        now = time.time()
        
        if not hasattr(self, '_active_notes') or not self._active_notes:
            return  # Nothing to do
        
        # Get the current instrument if available
        instrument = None
        if hasattr(self, '_direct_instrument') and self._direct_instrument:
            instrument = self._direct_instrument
        elif hasattr(self, 'composer') and self.composer and hasattr(self.composer, 'instrument_manager'):
            instrument = self.composer.instrument_manager.melody_instrument()
        
        if not instrument:
            # No valid instrument to work with, just clean up old notes
            self._active_notes = {}
            return
            
        # Identify notes to clean up
        notes_to_remove = []
        
        # Process each active note
        for note, info in self._active_notes.items():
            age = now - info['start_time']
            
            # Notes older than 10 seconds should be removed
            if age > 10.0:
                notes_to_remove.append(note)
                # Try to explicitly stop old notes if possible
                if hasattr(instrument, 'end_note'):
                    try:
                        instrument.end_note(note)
                    except Exception:
                        pass  # Ignore errors when stopping old notes
            
            # Notes in releasing state should fade out
            elif info.get('releasing', False):
                # Play a zero-volume version to effectively stop it
                try:
                    instrument.play_note(note, 0, 0.01, blocking=False)
                    notes_to_remove.append(note)  # Remove after processing
                except Exception:
                    pass  # Ignore errors
        
        # Clean up notes marked for removal
        for note in notes_to_remove:
            if note in self._active_notes:
                del self._active_notes[note]
                
    def tick(self, time_delta=1/30.0):
        """Process a time step in the sound system."""
        try:
            # Periodically clean up active notes
            self.manage_active_notes()
            
            # Periodically clear reaction notes
            current_time = time.time()
            if current_time - self.last_clear_time > self.clear_interval:
                print("[SOUND] Periodic reaction notes clearing")
                self.update_pillar_setting("reaction_notes", [])
                self.last_clear_time = current_time
                
            # Process sound generation if composer exists
            if hasattr(self, 'composer') and self.composer is not None:
                try:
                    self.composer.play()
                    wait(time_delta, units="time")
                except Exception as e:
                    print(f"[ERROR] Composer play/wait failed: {e}")
        except Exception as e:
            print(f"[ERROR] Error in sound manager tick: {e}")

    def get_pillar_settings(self):
        """Return current sound settings for diagnostics"""
        return {
            "melody_volume": getattr(self.composer, "melody_volume", None),
            "harmony_volume": getattr(self.composer, "harmony_volume", None),
            "background_volume": getattr(self.composer, "background_volume", None),
            "harmony_enabled": getattr(self.composer, "harmony_enabled", None),
            "last_notes": getattr(self, "last_notes", [])
        }

    def cleanup(self):
        """Clean up resources properly before shutdown"""
        print("[SOUND] Performing sound system cleanup...")
        
        try:
            # Stop any active notes
            if hasattr(self, '_active_notes') and self._active_notes:
                # Get the main instrument
                instrument = None
                if hasattr(self, '_direct_instrument') and self._direct_instrument:
                    instrument = self._direct_instrument
                elif hasattr(self, 'composer') and self.composer and self.composer.instrument_manager:
                    instrument = self.composer.instrument_manager.melody_instrument()
                
                if instrument:
                    # Try to stop each active note
                    for note in self._active_notes.keys():
                        try:
                            if hasattr(instrument, 'end_note'):
                                instrument.end_note(note)
                            elif hasattr(instrument, 'stop_note'):
                                instrument.stop_note(note)
                        except Exception:
                            pass  # Ignore errors when stopping notes
                
                # Clear the active notes dictionary
                self._active_notes.clear()
            
            # Clear any composer resources
            if hasattr(self, 'composer') and self.composer:
                # Stop any active forks
                for fork_name, fork in getattr(self.composer, 'active_forks', {}).items():
                    if fork and hasattr(fork, 'kill'):
                        try:
                            fork.kill()
                            print(f"[SOUND] Stopped active fork: {fork_name}")
                        except Exception:
                            pass
                
                # Clear active notes in composer
                if hasattr(self.composer, 'active_reaction_notes'):
                    self.composer.active_reaction_notes.clear()
            
            # Close the SCAMP session if present
            if hasattr(self, 'session') and self.session:
                # Some SCAMP versions have an explicit shutdown method
                if hasattr(self.session, 'cleanup') and callable(self.session.cleanup):
                    try:
                        self.session.cleanup()
                        print("[SOUND] SCAMP session cleanup called")
                    except Exception as e:
                        print(f"[WARNING] Error during session cleanup: {e}")
                        
                # Alternative shutdown approaches
                if hasattr(self.session, 'stop') and callable(self.session.stop):
                    try:
                        self.session.stop()
                        print("[SOUND] SCAMP session stopped")
                    except Exception:
                        pass
                        
                # Clear reference to session
                self.session = None
            
            print("[SOUND] Cleanup complete")
            return True
        except Exception as e:
            print(f"[ERROR] Error during sound system cleanup: {e}")
            return False
            
    def restart_sound_system(self):
        """Attempt to restart the sound system after failures"""
        print("[SOUND] Attempting to restart sound system...")
        
        try:
            # Clean up existing resources
            self.cleanup()
            
            # Create a new session
            if HAS_SCAMP:
                self.session = Session()
                print("[SOUND] Created new SCAMP session")
                
                # Recreate direct instrument
                success = self.ensure_direct_instrument()
                if not success:
                    print("[WARNING] Failed to recreate direct instrument")
                
                # Recreate composer if needed
                if not hasattr(self, 'composer') or self.composer is None:
                    try:
                        self.composer = Composer(self.session, self.state)
                        print("[SOUND] Created new composer")
                    except Exception as e:
                        print(f"[ERROR] Failed to recreate composer: {e}")
                
                print("[SOUND] Sound system restarted successfully")
                return True
            else:
                print("[ERROR] SCAMP not available - cannot restart sound system")
                return False
        except Exception as e:
            print(f"[ERROR] Failed to restart sound system: {e}")
            return False

if __name__=="__main__":
    sm = SoundManager("test")
    while True:
        sm.tick()


