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


