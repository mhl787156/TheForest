from scamp import *
import random
from scamp_extensions.playback.supercollider import add_sc_extensions

def init_scamp_extensions():
    add_sc_extensions()


SC_PARTS = {

    "vibrato": r"""
    SynthDef(\vibSynth, { |out=0, freq=440, volume=0.1, vibFreq=20, vibWidth=0.5, gate=1|
        var envelope = EnvGen.ar(Env.asr(releaseTime:0.5), gate, doneAction: 2);
        var vibHalfSteps = SinOsc.ar(vibFreq) * vibWidth;
        var vibFreqMul = 2.pow(vibHalfSteps / 12);
        var vibSine =  SinOsc.ar(freq * vibFreqMul) * volume / 10;
        Out.ar(out, (envelope * vibSine) ! 2);
    }, [\ir, 0.1, 0.1, 0.1, 0.1, \kr])
    """,

    "bassHum_beating": r"""
    SynthDef(\bassHum_beating, { |out=0, volume=1.0, freq=36, spread=0.45, drift=0.02, color=0.4, atk=10, rel=40, gate=1|
        var envelope = EnvGen.ar(Env.asr(atk, 1, rel), gate, doneAction: 2);
        var lfos  = LFNoise2.kr(0.02!3).range(1-drift, 1+drift);
        var sig   = SinOsc.ar(freq * lfos, Rand(0,2pi)!3).sum * (volume/3);
        var tilt = color.linlin(0,1,-6,6); // dB shift		
        sig = tanh(sig * 2.0);
        sig = BLowShelf.ar(sig, 120, 1, tilt); // counter-tilt
        sig = Balance2.ar(sig, sig);
        sig = sig * envelope;
        Out.ar(out, sig);
    })
    """,

    "bass_fmGrowl": r"""
    SynthDef(\bass_fmGrowl, { |out=0, volume=0.08, freq=45, ratio=1.99, index=2.5, drift=0.02, atk=0.5, rel=10, gate=1|
        var envelope = EnvGen.ar(Env.asr(atk, 1, rel), gate, doneAction: 2);
        var mod = SinOsc.ar(freq*ratio, 0, freq*index);
        var base = SinOsc.ar(freq + mod);
        var slow = LFNoise2.kr(0.1).range(1-drift, 1+drift);
        var sig = (base * slow).tanh;
        sig = LPF.ar(sig, 600);
        sig = (sig!2) * Env.asr(atk,1,rel).kr(doneAction:2) * volume * envelope;
        Out.ar(out, sig);
    })
    """,

    "melody_reed": r"""
    SynthDef(\melody_reed, { |out=0, volume=0.5, freq=440, bend=0, breath=0.15, vib=0.2, atk=0.02, rel=4, gate=1|
        var envelope = EnvGen.ar(Env.asr(atk, 1, rel), gate, doneAction: 2);
        var v = SinOsc.kr(5, 0, vib*0.01+0.001);
        var f = freq * (bend.midiratio) * (1+v);
        var exc = LPF.ar(WhiteNoise.ar(breath), f*2);
        var body = LPF.ar(Blip.ar(f, 5), f*1.5) + exc*0.2;
        body = RLPF.ar(body.tanh, f*1.2, 0.2);
        body = body * Env.perc(atk, rel, curve: -3).kr(doneAction:2) * volume * envelope;
        Out.ar(out, body!2);
    });
    """,

    "melody_karplus": r"""
    SynthDef(\melody_karplus, { |out=0, volume=30.0, freq=330, damp=0.3, atk=0.02, rel=0.08, decay=8, pick=0.3, gate=1|
        var envelope = EnvGen.ar(Env.asr(atk, 1, rel), gate, doneAction: 2);
        var exc = Decay2.ar(Impulse.ar(0), 0.005, 0.08) * PinkNoise.ar(pick);
        var sig = Pluck.ar(exc, trig:1, maxdelaytime:0.2, delaytime:freq.reciprocal, decaytime:decay, coef:(1-damp.clip(0,1)));
        sig = LPF.ar(sig, freq*3);
        sig = sig * volume * envelope;
        Out.ar(out, sig);
    });
    """,

    "pop_pip": r"""
    SynthDef(\pop_pip, { |volume=1.0, freq=1200, atk=0.1, rel=0.08, bend=0, gate=1|
        var envelope = EnvGen.ar(Env.asr(atk, 1, rel), gate, doneAction: 2);
        var env = Env.perc(0.0008, rel, curve:-6).kr(doneAction:2);
        var sig = SinOsc.ar(freq * (bend.midiratio)) * env;
        sig = BPF.ar(sig, freq*1.2, 0.4);
        Out.ar(0, (sig!2) * volume * envelope);
    });
    """,

    "melody_bells": r"""
    SynthDef(\mel_bells, { |out=0, volume=0.08, freq=440, bright=0.6, atk=0.005, rel=4, gate=1|
        var parts = [1, 2.7, 3.8, 5.1, 6.7];
        var envelope = EnvGen.ar(Env.asr(atk, 1, rel), gate, doneAction: 2);
        var env = Env.perc(atk, rel, curve:-4).kr(doneAction:2);
        var sig = Mix.fill(parts.size, { |i|
            var a = (1/(i+1)).pow(0.9);
            SinOsc.ar(freq*parts[i], 2pi.rand) * a
        });
        sig = (HPF.ar(sig, 200) * (0.3 + bright*0.7));
        sig = (sig!2) * env * volume * envelope;
        Out.ar(out, sig);
    });
    """,

    "melody_softEP": r"""
    SynthDef(\mel_softEP, { |out=0, volume=0.07, freq=330, gate=1, index=1.2, ratio=2, atk=0.005, dec=1.2, rel=4, tone=3000|
        var envelope = EnvGen.ar(Env.asr(atk, 1, rel), gate, doneAction: 2);
        var envA = Env.perc(atk, dec, curve:-4).kr;
        var envR = Env.asr(0,1,rel).kr(doneAction:2);
        var mod  = SinOsc.ar(freq*ratio) * (freq*index*envA);
        var car  = SinOsc.ar(freq + mod);
        var body = LPF.ar(car.tanh, tone);
        var sig  = (body!2) * envR * volume * envelope;
        Out.ar(out, sig);
    });
    """,

    "melody_vocal": r"""
    SynthDef(\mel_vocal, { |out=0, volume=1.0, freq=330, gate=1, vowel=0.8, vib=0.2, atk=0.02, rel=3|
        var v = SinOsc.kr(5).range(-1*vib*0.01, vib*0.01);
        var f = freq * (1+v);
        // interpolate a couple of formants
        var f1 = LinLin.kr(vowel, 0,1, 500, 900);
        var f2 = LinLin.kr(vowel, 0,1, 1100, 1500);
        var f3 = LinLin.kr(vowel, 0,1, 2500, 2800);
        var src = Blip.ar(f, 8).tanh;
        var sig = BPF.ar(src, f1, 0.2) * 0.7 + BPF.ar(src, f2, 0.1) * 0.4 + BPF.ar(src, f3, 0.08) * 0.3;
        var envelope = EnvGen.ar(Env.asr(atk, 1, rel), gate, doneAction: 2);
        sig = (sig!2) * Env.perc(atk, rel, curve:-3).kr(doneAction:2) * volume * envelope;
        Out.ar(out, sig);
    });
    """
}

def create_supercollider_synth(s: Session, name: str):
    return s.new_supercollider_part(name, SC_PARTS[name])
    
