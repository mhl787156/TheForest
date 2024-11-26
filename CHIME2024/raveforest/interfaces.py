from enum import Enum

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
    "violoncello",
    "violoncello",
    "contrabass",
    "orchestra",
    "standard",
    "guitar",
    "electric",
    "pizzicato"
]

MELODIES = [
    "melody1",
    "melody2",
    "melody3"
]

BASELINE_STYLE = [
    "long",
    "pulsing",
    "beat"
]

DEFAULT_STATE = {
    "volume": {
        "melody": 0.5,
        "harmony": 0.5,
        "background": 0.1
    },
    "instruments": {
        "melody": "trumpet",
        "harmony": "piano",
        "background": "strings"
    },
    "key": 60,
    "bpm": 120,
    "melody_scale": "pentatonic",
    "melody_number": 0,
    "baseline_style": "long"
}

