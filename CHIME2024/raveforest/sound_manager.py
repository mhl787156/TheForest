from scamp import Session, wait, current_clock
import scamp_extensions.process as seprocess
import expenvelope as expe
 
import multiprocessing as mp
from queue import Queue
import random
import numpy as np

from interfaces import DEFAULT_STATE, SCALE_TYPES, INSTRUMENTS

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
        if self.instrument_names[function] == instrument_name:
            return
        
        if self.instrument_names[function] is not None:
            # Remove Existing Instrument
            current_instruments = [i.name for i in self.session.instruments]
            idx = list(current_instruments).index(self.instrument_name[function])
            self.session.pop_instrument(idx)
            
        self.instruments[function] = self.session.new_part(instrument_name)
        self.instrument_names[function] = instrument_name

    def melody_instrument(self):
        return self.instruments["melody"]

    def harmony_instrument(self):
        return self.instruments["harmony"]

    def background_instrument(self):
        return self.instruments["background"]

class Composer:

    def __init__(self, session, initial_state):
        self.session = session

        self.state = initial_state

        self.mp_manager = mp.Manager()

        # Instruments
        self.instrument_manager = InstrumentManager(self.session)
        for k,v in initial_state["instruments"].items():
            self.instrument_manager.update_instrument(v, function=k)

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

    def update(self, new_state):
        pass

    def update_key(self):
        self.shared_state["key"].value += 5

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
        
    def start_fork(self, function_name, function):
        # If a fork is active or not alive, then start the new fork
        if self.active_forks[function_name] is None or not self.active_forks[function_name].alive:
            self.active_forks[function_name] = self.session.fork(function, args=(self.shared_state,))
    
    def fork_melody(self, shared_state):
                # Random: 
        # 1. If playing a note
        play_note_thresh = 0.05
        # 2. Number of notes (heavily weigted to 1,2,3)
        geom_p = 0.00001
        # 3. The duration of each of those notes
        # duration_weightings = [1, 1, 1, 50, 200, 150, 100, 50, 2, 2]
        duration_values = [0.125, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
        duration_weightings = [0, 3, 3, 1, 0, 0, 0]
        # 4. Generate initial note from scale in a random octave weighted between 3-6
        # octave_weightings = {0:}
        # 5. The weighted notes themselves OR weighted intervals between them (4th/5ths etc)
        # note_weightings = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

        if random.random() >= play_note_thresh:
            return
        
        number_of_notes  = random.choices([1, 2, 3, 4, 5], weights=[300, 100, 50, 50, 30], k=1)[0]

        if number_of_notes == 0:
            return

        durations = random.choices(duration_values,
            weights=duration_weightings, k=number_of_notes)
        durations = [d for d in durations]
        
        # Generate initial note
        scale = SCALE_TYPES[self.state["melody_scale"]](self.shared_state["key"].value)
        note_numbers = random.choices(list(scale) + [None], k=number_of_notes)
        print(list(scale))
        note_octaves = np.clip(np.round(np.random.normal(4, 1.5, number_of_notes)).astype(int), 0, 7)

        instrument = self.instrument_manager.melody_instrument()
        for n, d in zip(note_numbers, durations):
            instrument.play_note(n, 0.5, d, blocking=True)

    def fork_harmony(self, shared_state):
        # current_clock().tempo = self.state["bpm"]["harmony"]
        instrument = self.instrument_manager.harmony_instrument()
        key = next(self.key_generator)
        # print("harmony", key)
        scale = list(SCALE_TYPES[self.state["melody_scale"]](key))

        # Add 7/9/11/13 etc depending on chord_levels
        chord_levels = shared_state["chord_levels"].value

        chord = []
        gen_chords = [0, 2, 4] + [6 + 2*chord_levels*i for i in range(chord_levels)]
        for offset in gen_chords:
            if offset > len(scale):
                new_offset = offset % len(scale)
                number_up = offset // len(scale)
                print(offset, new_offset, number_up)
                note = scale[new_offset] + number_up * 12
            else:
                note = scale[offset]
            chord.append(int(note))

        # Adjust voicings
        # print(chord)
        random.shuffle(chord)
        key_idx = chord.index(key)
        chord = np.array(chord)
        chord[key_idx:] += 12 # If some of the chords are below tonic, shift down octave
        # print(chord)

        shared_state["key"].value = key
        volume = self.state["volume"]["harmony"]
        envelope = expe.envelope.Envelope.from_levels_and_durations(
            [0.1, volume, 1.0], [0.5, 3.0]
        )
        instrument.play_chord(chord, envelope, 4.0, blocking=True)

        if chord_levels > 0:
            shared_state["chord_levels"].value -= 1

    def fork_background(self, shared_state):
        # current_clock().tempo = self.state["bpm"]["background"]
        instrument = self.instrument_manager.background_instrument()
        volume = self.state["volume"]["background"]
        # for note in seprocess.generators.random_walk(40, clamp_min=35, clamp_max=50):
        while True:
            note = shared_state["key"].value - 24
            # print("background", note)
            instrument.play_note(note, volume, 4.0*4, blocking=True)


class SoundManager:
    """Manages and schedules sound playback for pillars using the Sonic Pi server."""          
    
    def __init__(self, pillar_id, initial_state=None):
        self.pillar_id = pillar_id

        self.session = Session()
        self.state = initial_state if initial_state is not None else DEFAULT_STATE

        self.composer = Composer(self.session, self.state)


    def __repr__(self):
        """String representation of the pillar for debugging."""
        return f"Pillar({self.pillar_id}) {self.state}"
    
    def update_pillar_setting(self, setting_name, value):
        """Updates the settings dictionary for a specific pillar."""
        # Update the actual pillar object
        getattr(self, f'set_{setting_name}')(value)  # Dynamically call the set method

    def tick(self, time_delta=1/30.0):
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

    