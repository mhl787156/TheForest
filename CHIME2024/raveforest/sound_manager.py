from scamp import Session, wait
import scamp_extensions.pitch as sepitch 
import scamp_extensions.process as seprocess
import expenvelope as expe
 
import multiprocessing as mp
from queue import Queue
import random
import numpy as np

# Mapping
# class NODE_FUNCTION(Enum):
#     SCALE_TYPE=1
#     SCALE_KEY=2
#     INSTRUMENT=3
#     TEMPO=4

# NODE_FUNCTION_NAMES = {
#     NODE_FUNCTION.SCALE_KEY: "key",
#     NODE_FUNCTION.SCALE_TYPE: "scale",
#     NODE_FUNCTION.INSTRUMENT: "instr",
#     NODE_FUNCTION.TEMPO: "tempo"
# }

SCALE_TYPES = {
    "aeolian" : sepitch.scale.Scale.aeolian,
    "blues" : sepitch.scale.Scale.blues,
    "chromatic" : sepitch.scale.Scale.chromatic,
    "diatonic" : sepitch.scale.Scale.diatonic,
    "dorian" : sepitch.scale.Scale.dorian,
    "harmonic_minor" : sepitch.scale.Scale.harmonic_minor,
    "ionian" : sepitch.scale.Scale.ionian,
    "locrian" : sepitch.scale.Scale.locrian,
    "lydian" : sepitch.scale.Scale.lydian,
    "major" : sepitch.scale.Scale.major,
    "melodic_minor" : sepitch.scale.Scale.melodic_minor,
    "mixolydian" : sepitch.scale.Scale.mixolydian,
    "natural_minor" : sepitch.scale.Scale.natural_minor,
    "octatonic" : sepitch.scale.Scale.octatonic,
    "pentatonic" : sepitch.scale.Scale.pentatonic,
    "pentatonic_minor" : sepitch.scale.Scale.pentatonic_minor,
    "phrygian" : sepitch.scale.Scale.phrygian,
    "whole_tone" : sepitch.scale.Scale.whole_tone
}

INSTRUMENTS = [
    "trumpet",
    "brass",
    "piano",
    "strings",
    "oboe"
]


DEFAULT_STATE = {
    "volume": {
        "melody": 0.5,
        "harmony": 0.5,
        "background": 0.5
    },
    "instruments": {
        "melody": "trumpet",
        "harmony": "piano",
        "background": "strings"
    },
    "bpm": {
        "melody": 120,
        "harmony": 60,
        "background": 1
    },
    "melody_scale": "blues"
}


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
            "key": self.mp_manager.Value('s', next(self.key_generator))
        }

        self.active_forks = {
            "melody": None,
            "harmony": None,
            "background": None
        }

    def update(self, new_state):
        pass

    def generate_key_generator(self):
        # return seprocess.generators.random_walk(self.all_keys[0], clamp_min=min(self.all_keys), clamp_max=max(self.all_keys))
        circle_fifths = [48 + (i*5) % 12 for i in range(11)]
        return seprocess.generators.non_repeating_shuffle(list(circle_fifths))
    
    def generate_melody_generator(self, key):
        notes = SCALE_TYPES[self.state["melody_scale"]](key)
        return seprocess.generators.non_repeating_shuffle(list(notes))

    def play(self):
        self.start_fork("melody", self.fork_melody)
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
        # note_weightings = [1.0, 1.0, ]

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
        note_octaves = np.clip(np.round(np.random.normal(4, 1.5, number_of_notes)).astype(int), 0, 7)

        instrument = self.instrument_manager.melody_instrument()
        for n, d in zip(note_numbers, durations):
            instrument.play_note(n, 0.5, d, blocking=True)

    def fork_harmony(self, shared_state):
        instrument = self.instrument_manager.harmony_instrument()
        key = next(self.key_generator)
        chord = [key, key+3, key+5]

        shared_state["key"].value = key

        envelope = expe.envelope.Envelope.from_levels_and_durations(
            [0.1, 0.5, 1.0], [0.5, 3.0]
        )
        instrument.play_chord(chord, envelope, 4.0, blocking=True)

    def fork_background(self, shared_state):
        instrument = self.instrument_manager.background_instrument()

        for note in seprocess.generators.random_walk(40, clamp_min=35, clamp_max=50):
        # while True:
            # note = shared_state["key"].value - 24
            instrument.play_note(note, 0.05, 4.0*4, blocking=True)


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

    def set_amp(self, amp):
        self.amp = amp
    
    def set_pitch(self, pitch):
        self.pitch = pitch
    
    def set_synth(self, synth):
        self.synth = globals()[synth]
        
    def set_bpm(self, bpm):
        self.bpm = bpm
    
    def set_pan(self, pan):
        self.pan = pan
    
    def set_envelope(self, envelope):
        self.envelope = envelope


if __name__=="__main__":

    # sm = SoundManager("test")
    session = Session()
    session.bpm = 60
    comp = Composer(session, DEFAULT_STATE)
    while True:
        comp.play()
        wait(1/30.0, units="time")