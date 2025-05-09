from enum import Enum
import random
import scamp_extensions.pitch as sepitch
import sys

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

# Ensure we have the required libraries
try:
    import scamp_extensions.pitch as sepitch
except ImportError as e:
    print(f"[ERROR] Required library not found: {e}")
    print("[ERROR] Please install required packages with: pip install scamp-extensions")
    # Don't exit, as this module might be imported by other modules that handle the error

# Define scales with error handling
SCALE_TYPES = {}
try:
    SCALE_TYPES = {
        "aeolian": sepitch.scale.Scale.aeolian,
        "blues": sepitch.scale.Scale.blues,
        "chromatic": sepitch.scale.Scale.chromatic,
        "diatonic": sepitch.scale.Scale.diatonic,
        "dorian": sepitch.scale.Scale.dorian,
        "harmonic_minor": sepitch.scale.Scale.harmonic_minor,
        "ionian": sepitch.scale.Scale.ionian,
        "locrian": sepitch.scale.Scale.locrian,
        "lydian": sepitch.scale.Scale.lydian,
        "major": sepitch.scale.Scale.major,
        "melodic_minor": sepitch.scale.Scale.melodic_minor,
        "mixolydian": sepitch.scale.Scale.mixolydian,
        "natural_minor": sepitch.scale.Scale.natural_minor,
        "octatonic": sepitch.scale.Scale.octatonic,
        "pentatonic": sepitch.scale.Scale.pentatonic,
        "pentatonic_minor": sepitch.scale.Scale.pentatonic_minor,
        "phrygian": sepitch.scale.Scale.phrygian,
        "whole_tone": sepitch.scale.Scale.whole_tone
    }
except Exception as e:
    print(f"[ERROR] Error initializing SCALE_TYPES: {e}")
    # Provide a minimal set of scales if there's an error
    SCALE_TYPES = {
        "major": lambda: [0, 2, 4, 5, 7, 9, 11],
        "minor": lambda: [0, 2, 3, 5, 7, 8, 10],
        "pentatonic": lambda: [0, 2, 4, 7, 9],
    }

# Create a list of scale types, with error handling
try:
    SCALES_TYPES_LIST = list(SCALE_TYPES)
except Exception as e:
    print(f"[ERROR] Failed to create SCALES_TYPES_LIST: {e}")
    SCALES_TYPES_LIST = ["major", "minor", "pentatonic"]  # Fallback

# Common instruments - verified to work with most sound engines
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

# Make sure we have at least one instrument as fallback
if not INSTRUMENTS:
    print("[WARNING] INSTRUMENTS list is empty, adding default instruments")
    INSTRUMENTS = ["piano", "strings", "flute"]

# Define melodic patterns with a try-except block for safety
try:
    MELODIES = [
        [(0, 0.25), (1, 0.25), (2, 0.25), (3, 0.25), (4, 0.25)],  # Ascending Scale
        [(4, 0.25), (3, 0.25), (2, 0.25), (1, 0.25), (0, 0.25)],  # Descending Scale
        [(0, 0.25), (2, 0.25), (4, 0.25), (-1, 0.5)],  # Thirds Scale
        [(0, 0.5), (None, 0.25), (5, 0.5), (4, 0.5)],  # Thirds Scale
        [(4, 0.3), (3, 0.2), (4, 0.3), (3, 0.2), (4, 0.3), (3, 0.2)],  # Thirds Scale
        [(6, 0.25), (4, 0.25), (2, 0.25), (5, 0.25), (3, 0.25), (1, 0.25)],
        [(-3, 0.25), (2, 0.25), (6, 0.25)],  # Thirds Scale
        [(1, 0.25), (2, 0.5), (None, 0.5), (5, 0.25), (4, 0.5)],
        [(0, 0.125), (1, 0.125), (0, 0.125), (-1, 0.125), (0, 0.125)],
        [(4, 0.125), (-3, 0.125), (3, 0.125), (-2, 0.125), (2, 0.125), (-1, 0.125), (1, 0.125), (0, 0.125)],
        [(0, 0.125), (None, 0.125), (0, 0.25), (None, 0.125), (0, 0.25), (None, 0.125)],
        [(0, 0.25), (2, 0.25), (4, 0.25), (6, 0.25), (9, 0.25)],  # Thirds Scale
        [(5, 0.25), (5, 0.25), (5, 0.25), (0, 0.25)],
        [(7, 0.125), (6, 0.125), (5, 0.125), (2, 0.125), (3, 0.125)],
        [(0, 0.125), (1, 0.125), (2, 0.125), (4, 0.25), (5, 0.125), (2, 0.125), (1, 0.25)],
        [(-4, 0.25), (0, 0.25), (4, 0.25), (8, 0.25), (12, 0.25)],  # Ascending Scale
        [(0, 0.25), (0, 0.25), (4, 0.25), (4, 0.25), (5, 0.25), (5, 0.25), (4, 0.5)],  # lol
        [(3, 0.25), (3, 0.25), (2, 0.25), (2, 0.25), (1, 0.25), (1, 0.25), (0, 0.5)],  # lol
        [(6, 0.3), (4, 0.2), (6, 0.3), (4, 0.2), (2, 0.3), (4, 0.2), (6, 0.3), (7, 0.2)],
        [(4, 0.25), (2, 0.25), (0, 0.25), (5, 0.25), (3, 0.25), (1, 0.25), (-1, 0.25), (0, 0.5)],  # lol
        [(0, 0.875), (-1, 0.125)],  # 
        [(0, 0.125), (7, 0.125)] * 4,  #
        [(2, 0.125), (1, 0.125), (0, 0.125), (4, 0.125), (4, 0.125), (4, 0.125)],
    ]
    
    # Only add random melodies if we have a working random module
    if random and hasattr(random, 'randint'):
        random_melodies = [
            [(random.randint(-7, 7), 0.125) for _ in range(8)],
            [(random.randint(-7, 7), 0.125) for _ in range(8)],
            [(random.randint(-7, 7), 0.125) for _ in range(8)],
            [(random.randint(-7, 7), 0.25) for _ in range(4)] + [(random.randint(-7, 7), 0.125) for _ in range(4)],
        ]
        MELODIES.extend(random_melodies)
        
    # Shuffle the melodies for variety, but handle potential errors
    try:
        random.shuffle(MELODIES)
    except Exception as shuffle_error:
        print(f"[WARNING] Could not shuffle melodies: {shuffle_error}")
        
except Exception as melody_error:
    print(f"[ERROR] Error creating melodies: {melody_error}")
    # Create simple fallback melodies
    MELODIES = [
        [(0, 0.25), (2, 0.25), (4, 0.25)],  # Simple triad
        [(0, 0.5), (4, 0.5), (7, 0.5)],  # C major chord
    ]

# Ensure we have at least one melody
if not MELODIES:
    print("[WARNING] MELODIES list is empty, adding a default melody")
    MELODIES = [[(0, 0.25), (2, 0.25), (4, 0.25)]]  # Simple triad

# Define baseline styles with validation
BASELINE_STYLE = [
    "long",
    "pulsing",
    "beat"
]

# Ensure we have at least one baseline style
if not BASELINE_STYLE:
    print("[WARNING] BASELINE_STYLE list is empty, adding a default style")
    BASELINE_STYLE = ["long"]

# Create a mapping from note number to hue value (0-255)
try:
    FIXED_NOTE_HUE_MAP = {
        0: 0,      # "C"
        7: 21,     # "G"
        2: 42,     # "D"
        9: 64,     # "A"
        4: 85,     # "E"
        11: 107,   # "B"
        6: 128,    # "F#"
        1: 150,    # "C#"
        8: 171,    # "G#"
        3: 193,    # "D#"
        10: 214,   # "A#"
        5: 235     # "F"
    }
    
    # Verify all keys are in the range 0-11
    invalid_keys = [k for k in FIXED_NOTE_HUE_MAP.keys() if not (isinstance(k, int) and 0 <= k <= 11)]
    if invalid_keys:
        print(f"[WARNING] Invalid keys in FIXED_NOTE_HUE_MAP: {invalid_keys}")
        for k in invalid_keys:
            del FIXED_NOTE_HUE_MAP[k]
            
    # Verify all values are in the range 0-255
    invalid_values = [(k, v) for k, v in FIXED_NOTE_HUE_MAP.items() if not (isinstance(v, int) and 0 <= v <= 255)]
    if invalid_values:
        print(f"[WARNING] Invalid values in FIXED_NOTE_HUE_MAP: {invalid_values}")
        for k, _ in invalid_values:
            # Replace with a valid value
            FIXED_NOTE_HUE_MAP[k] = (k * 21) % 256
            
except Exception as hue_map_error:
    print(f"[ERROR] Error creating FIXED_NOTE_HUE_MAP: {hue_map_error}")
    # Create a simple fallback hue map
    FIXED_NOTE_HUE_MAP = {i: (i * 21) % 256 for i in range(12)}

# Ensure all 12 semitones have a hue mapping
for i in range(12):
    if i not in FIXED_NOTE_HUE_MAP:
        print(f"[WARNING] Note {i} missing from FIXED_NOTE_HUE_MAP, adding default")
        FIXED_NOTE_HUE_MAP[i] = (i * 21) % 256

# Define default state with validation
try:
    DEFAULT_STATE = {
        "volume": {
            "melody": 1.0,
            "harmony": 0.5,
            "background": 0.3
        },
        "instruments": {
            "melody": "strings",
            "harmony": "flute",
            "background": "strings"
        },
        "key": 60,
        "bpm": 100,
        "melody_scale": "pentatonic",
        "melody_number": 0,
        "baseline_style": "long",
        "chord_levels": 0,
        "reaction_notes": []
    }
    
    # Verify instruments exist in the INSTRUMENTS list
    for layer, instr in DEFAULT_STATE["instruments"].items():
        if instr not in INSTRUMENTS:
            print(f"[WARNING] Default instrument '{instr}' for {layer} not in INSTRUMENTS list")
            # Replace with first instrument in list
            DEFAULT_STATE["instruments"][layer] = INSTRUMENTS[0] if INSTRUMENTS else "piano"
    
    # Verify melody_scale exists in SCALE_TYPES
    if DEFAULT_STATE["melody_scale"] not in SCALE_TYPES:
        print(f"[WARNING] Default scale '{DEFAULT_STATE['melody_scale']}' not in SCALE_TYPES")
        # Replace with first scale type
        DEFAULT_STATE["melody_scale"] = SCALES_TYPES_LIST[0] if SCALES_TYPES_LIST else "major"
        
    # Verify melody_number is valid
    if not isinstance(DEFAULT_STATE["melody_number"], int) or DEFAULT_STATE["melody_number"] >= len(MELODIES):
        print(f"[WARNING] Invalid melody_number: {DEFAULT_STATE['melody_number']}")
        DEFAULT_STATE["melody_number"] = 0
        
    # Verify baseline_style is valid
    if DEFAULT_STATE["baseline_style"] not in BASELINE_STYLE:
        print(f"[WARNING] Default baseline_style '{DEFAULT_STATE['baseline_style']}' not in BASELINE_STYLE")
        DEFAULT_STATE["baseline_style"] = BASELINE_STYLE[0] if BASELINE_STYLE else "long"
    
except Exception as default_state_error:
    print(f"[ERROR] Error creating DEFAULT_STATE: {default_state_error}")
    # Create a simple fallback default state
    DEFAULT_STATE = {
        "volume": {"melody": 1.0, "harmony": 0.5, "background": 0.3},
        "instruments": {"melody": "piano", "harmony": "flute", "background": "strings"},
        "key": 60,
        "bpm": 100,
        "melody_scale": "pentatonic",
        "melody_number": 0,
        "baseline_style": "long",
        "chord_levels": 0,
        "reaction_notes": []
    }

