# from scamp import *
import numpy as np
from mingus.core import chords, scales, notes, intervals
from mingus.containers import Note, NoteContainer


class Pentatonic(scales.Ionian):
    type = "major"
    def ascending(self):
        notes = super().ascending()
        del notes[6] #remove 7 
        del notes[3] # and 4
        return notes

class MinorPentatonic(scales.Dorian):
    type = "minor"
    def ascending(self):
        notes = super().ascending()
        del notes[5] #remove 7 
        del notes[1] # and 3
        return notes
    
class BluesScale(MinorPentatonic):
    type = "major"
    def ascending(self):
        notes = super().ascending()
        notes.insert(3, intervals.minor_fifth(notes[0]))
        return notes

scale = BluesScale("C")

# Note containers 
scale_asc = scale.ascending()
note_container = NoteContainer()
note_container.add_notes(scale_asc * 2)

note_numbers = [int(n) for n in note_container]


print(scale_asc, note_numbers)

note_list = ["C", "F#", "G"]
output = scales.determine(note_list)
print(output)

# exit()
from scamp import Session
s = Session()
s.tempo = 100
# s.print_default_soundfont_presets()

# clarinet = s.new_part("clarinet")
# oboe = s.new_part("oboe")

# plist = [60, 64, 66, 69, 67]
# dlist = [1.5, 1.0, 1.0, 0.6]

# fp_cresc = Envelope.from_levels_and_durations([0.8, 0.2, 1.0], [0.2, 0.9])

# oboe.play_chord([76, 79, 84], fp_cresc, 5.0, blocking=False)

# for pitch, dur in zip(plist, dlist):
#     clarinet.play_note(pitch, 0.8, dur)
s.

trumpet = s.new_part("trumpet")
brass = s.new_part("brass")

for p in note_numbers:
    trumpet.play_note(p, 0.5, 0.5)

# def melody(instr, volume=0.8, transposition=0):
#     plist = np.array([60, 61, 63, 64, 61, 73, 78, 79, 80]) + transposition
#     dlist = [0.25, 0.25, 1.0, 0.5, 0.5, 2.0, 0.25, 0.25, 1.0]
#     for p, d in zip(plist, dlist):
#         instr.play_note(p, volume, d)

# def bass(instr, volume=0.5):
#     plist = np.array([50, 49, 48, 47]) - 10
#     dlist = [1.0, 1.0, 1.0, 1.0]
#     for p, d in zip(plist, dlist):
#         instr.play_note(p, volume, d)

# s.fork(melody, args=[trumpet])
# s.fork(melody, args=[trumpet, 0.8, 5], initial_beat_length=1.2)
# s.fork(bass, args=[brass])

s.wait_for_children_to_finish()