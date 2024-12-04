from enum import Enum
import random
import scamp_extensions.pitch as sepitch 

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
SCALES_TYPES_LIST = list(SCALE_TYPES)

INSTRUMENTS = [
    "bass",
    "baritone",
    "alto",
    "tenor",
    "soprano",
    "flute",
    "oboe",
    "english",
    "clarinet",
    "bass clarinet",
    "bassoon",
    "contrabassoon",
    "saxophone",
    "trumpet",
    "horn",
    "trombone",
    "tuba",
    "timpani",
    "percussion",
    "xylophone",
    "harp",
    "piano",
    "strings",
    "violin",
    "viola",
    "violincello",
    "contrabass",
    "orchestra",
    "standard",
    "guitar",
    "electric",
    "pizzicato"
]

MELODIES = [
    [(0, 0.25), (1, 0.25), (2, 0.25), (3, 0.25), (4, 0.25)], # Ascending Scale
    [(4, 0.25), (3, 0.25), (2, 0.25), (1, 0.25), (0, 0.25)], # Descending Scale
    [(0, 0.25), (2, 0.25), (4, 0.25), (-1, 0.5)], # Thirds Scale
    [(0, 0.5), (None, 0.25), (5, 0.5), (4, 0.5)], # Thirds Scale
    [(4, 0.3), (3, 0.2), (4, 0.3), (3, 0.2), (4, 0.3), (3, 0.2)], # Thirds Scale
    [(6, 0.25), (4, 0.25), (2, 0.25), (5, 0.25), (3, 0.25), (1, 0.25)],
    [(-3, 0.25), (2, 0.25), (6, 0.25)], # Thirds Scale
    [(1, 0.25),(2, 0.5),(None, 0.5),(5, 0.25),(4, 0.5)],
    [(0, 0.125),(1, 0.125),(0, 0.125),(-1, 0.125),(0, 0.125)],
    [(4, 0.125),(-3, 0.125),(3, 0.125),(-2, 0.125),(2, 0.125),(-1, 0.125),(1, 0.125),(0, 0.125)],
    [(0, 0.125), (None, 0.125), (0, 0.25), (None, 0.125), (0, 0.25), (None, 0.125)],
    [(0, 0.25), (2, 0.25), (4, 0.25), (6, 0.25), (9, 0.25)], # Thirds Scale
    [(5, 0.25), (5, 0.25), (5, 0.25), (0, 0.25)],
    [(7, 0.125), (6, 0.125), (5, 0.125), (2, 0.125), (3, 0.125)],
    [(0, 0.125), (1, 0.125), (2, 0.125), (4, 0.25), (5, 0.125), (2, 0.125), (1, 0.25)],
    [(-4, 0.25), (0, 0.25), (4, 0.25), (8, 0.25), (12, 0.25)], # Ascending Scale
    [(0, 0.25), (0, 0.25), (4, 0.25), (4, 0.25), (5, 0.25), (5, 0.25), (4, 0.5)], #lol
    [(3, 0.25), (3, 0.25), (2, 0.25), (2, 0.25), (1, 0.25), (1, 0.25), (0, 0.5)], #lol
    [(6, 0.3), (4, 0.2), (6, 0.3), (4, 0.2), (2, 0.3), (4, 0.2), (6, 0.3), (7, 0.2)],
    [(4, 0.25), (2, 0.25), (0, 0.25), (5, 0.25), (3, 0.25), (1, 0.25), (-1, 0.25), (0, 0.5)], #lol
    [(0, 0.875), (-1, 0.125)], # 
    [(0, 0.125), (7, 0.125)]*4, #
    [(2, 0.125), (1, 0.125), (0, 0.125), (4, 0.125), (4, 0.125), (4, 0.125)],
    [(random.randint(-7, 7), 0.125) for _ in range(8)],
    [(random.randint(-7, 7), 0.125) for _ in range(8)],
    [(random.randint(-7, 7), 0.125) for _ in range(8)],
    [(random.randint(-7, 7), 0.25) for _ in range(4)] + [(random.randint(-7, 7), 0.125) for _ in range(4)],
]
random.shuffle(MELODIES)

BASELINE_STYLE = [
    "long",
    "pulsing",
    "beat"
]

DEFAULT_STATE = {
    "volume": {
        "melody": 1.0,
        "harmony": 0.5,
        "background": 0.3
    },
    "instruments": {
        "melody": "trumpet",
        "harmony": "flute",
        "background": "strings"
    },
    "key": 60,
    "bpm": 100,
    "melody_scale": "pentatonic",
    "melody_number": 0,
    "baseline_style": "long",
    "chord_levels": 0
}

