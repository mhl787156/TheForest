#!/usr/bin/env python3
"""Test if SuperCollider audio works at all"""

from scamp import Session, wait
from scamp_extensions.playback.supercollider import add_sc_extensions

add_sc_extensions()

print("Starting SCAMP session...")
s = Session()

print("Creating simple test synth...")
test_synth_def = r"""
SynthDef(\test_beep, { |out=0, freq=440, volume=0.5, gate=1|
    var sig, env;
    env = EnvGen.kr(Env.perc(0.01, 1.0), doneAction: 2);
    sig = SinOsc.ar(freq) * env * volume;
    Out.ar(out, sig ! 2);
})
"""

print("Loading synth into SuperCollider...")
test_instrument = s.new_supercollider_part("test_beep", test_synth_def)

print("Playing test beep at 440Hz...")
test_instrument.play_note(440, 0.5, 1.0, blocking=True)

print("Waiting 1 second...")
wait(1.0)

print("Playing test beep at 880Hz...")
test_instrument.play_note(880, 0.5, 1.0, blocking=True)

print("Test complete. Did you hear two beeps?")
print("If YES: SuperCollider audio works, issue is with pad_synth")
print("If NO: Audio routing or SuperCollider server issue")

