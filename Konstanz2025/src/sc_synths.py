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
    """,

    "pad_synth": r"""
    SynthDef(\pad_synth, { |out=0, freq=200, volume=0.2, gate=1|
        var osc, sig, env, pan, mod, detune;
        // Random pan for wide stereo field
        pan = Rand(-0.8, 0.8);
        // Fixed duration envelope: 8s attack, 20s sustain, 12s release = 40s total
        // gate parameter kept for SCAMP compatibility but NOT used in envelope
        env = EnvGen.kr(Env.linen(8, 20, 12, 1, 'sine'), doneAction: 2);
        
        // Slow LFO modulation for movement (efficient)
        //mod = LFNoise1.kr(0.05).range(0.98, 1.02);
        //detune = LFNoise1.kr(0.08).range(-0.15, 0.15);
        
        // Reduced oscillator stack - 4 oscillators, very low/dark
        osc = Mix.new([
            SinOsc.ar(freq * 0.5, 0, 0.35),      // Very low sub
            //SinOsc.ar(freq * 0.3, 0, 0.3),    // Low detuned
            //SinOsc.ar(freq * 0.5 * mod, 0, 0.2),       // Sub octave
            //SinOsc.ar(freq * 0.4, 0, 0.1)              // Base frequency (reduced volume)
        ]);
        
        // Basic filtering - adjusted for low frequency range
        sig = HPF.ar(osc, 20);  // Remove only sub-sonic rumble below 20Hz
        sig = LPF.ar(sig, LFNoise1.kr(0.15).range(400, 1200));  // Gentle low-pass for warmth 
        
        // LIGHT reverb (reduced parameters to save CPU)
        //sig = FreeVerb.ar(sig, 0.65, 0.8, 0.5);
        
        sig = Pan2.ar(sig * volume * env * 0.2, pan);
        Out.ar(out, sig);
    })
    """,

    "pad_synth2": r"""

    SynthDef(\pad_synth2, { |out=0, freq=200, volume=0.2, gate=1|
        var tone, noise, sig, env, pan, mod;
        
        // Random stereo position per pad
        pan = Rand(-0.7, 0.7);
        
        // Long envelope: 8s attack, 25s sustain, 10s release = 43s
        env = EnvGen.kr(Env.linen(8, 25, 10, 1, 'sine'), doneAction: 2);
        
        // Gentle LFO for subtle movement
        mod = LFNoise1.kr(0.08).range(0.98, 1.02);
        
        // Smooth airy tone with subtle movement
        tone = SinOsc.ar(freq * 0.5 * mod, 0, 0.35);
        
        // Some noise for texture
        noise = LPF.ar(WhiteNoise.ar(0.02), 600);  
        
        // Combine
        sig = tone + noise;
        
        // Filtering for warmth
        sig = HPF.ar(sig, 25);
        sig = LPF.ar(sig, 1200);  // Lower for darker sound
        
        // Light reverb
        sig = FreeVerb.ar(sig, 0.4, 0.7, 0.3);
        
        // Stereo output with pan
        Out.ar(out, Pan2.ar(sig * volume * env * 0.4, pan));
    })
    

    """,

    "bass_synth": r"""
    SynthDef(\bass_synth, { |out=0, freq=440, volume=0.5, gate=1|
        var freqs = [36.71, 55, 73.42, 110];
        var chosenFreq = freqs.choose * rrand(0.99, 1.01);
        var pan = rrand(-0.4, 0.4);
        var carrier, modulator, mod_env, amp_env, sig, sub, metal, mid, harmonic;
        amp_env = Env.linen(0.8, 3, 2.5, 1, 'sine').kr(doneAction: 2);
        mod_env = Env.perc(0.01, 1.5, 1, -4).kr;
        modulator = SinOsc.ar(chosenFreq * 2.1, 0, chosenFreq * mod_env * 12);
        carrier = SinOsc.ar(chosenFreq + modulator, 0, 0.8);
        metal = SinOsc.ar(chosenFreq * 1.5 + (modulator * 0.4), 0, 0.35);
        mid = SinOsc.ar(chosenFreq * 3 + (modulator * 0.2), 0, 0.25);
        harmonic = SinOsc.ar(chosenFreq * 4, 0, 0.15);
        sub = SinOsc.ar(chosenFreq * 0.5, 0, 0.6);
        sig = (carrier + metal + mid + harmonic + sub) * amp_env;
        sig = LPF.ar(sig, LFNoise1.kr(0.2).range(800, 2500));
        sig = HPF.ar(sig, 35);
        sig = (sig * 1.3).tanh;
        Out.ar(out, Pan2.ar(sig * volume * gate, pan));
    })
    """,

    "lead_synth": r"""
    SynthDef(\lead_synth, { |out=0, freq=440, volume=0.25, gate=1|
        var numGrains = rrand(5, 10);
        var sig = Mix.fill(numGrains, {
            var grainFreq = exprand(400, 6000) * rrand(0.95, 1.05);
            var pan = rrand(-0.9, 0.9);
            var amp = exprand(0.15, 0.35);
            var bw = exprand(0.1, 0.6);
            var env = Env.perc(0.005, exprand(0.05, 0.2), 1, -6).kr(doneAction: 0);
            var source = Mix.ar([
                LFSaw.ar(grainFreq * LFNoise1.kr(exprand(5, 20)).range(0.98, 1.02), 0, 0.7),
                PinkNoise.ar(0.8)
            ]);
            var filtered = Mix.ar([
                BPF.ar(source, grainFreq, bw),
                BPF.ar(source, grainFreq * LFNoise1.kr(exprand(2, 10)).range(1.5, 2.5), bw * 0.8),
                BPF.ar(source, grainFreq * LFNoise1.kr(exprand(1, 8)).range(0.5, 0.7), bw * 1.2)
            ]);
            filtered = filtered + PitchShift.ar(filtered, 0.05, LFNoise1.kr(10).range(0.995, 1.005), 0, 0.01, 0.3);
            Pan2.ar(filtered * env * amp, pan)
        });
        DetectSilence.ar(sig, doneAction: 2);
        Out.ar(out, sig * volume * gate);
    })
    """,

    "lead2_synth": r"""
    SynthDef(\lead2_synth, { |out=0, freq=440, volume=0.18, gate=1|
        var voiceFreq = exprand(300, 700);
        var pan = rrand(-0.4, 0.4);
        var vowel = [0, 1, 2, 3, 4].choose;
        var sig, env, source, formants, f, a, q, vibrato, finalFreq;
        env = Env.linen(1.5, 3, 2.5, 1, 'sine').kr(doneAction: 2);
        vibrato = SinOsc.kr(exprand(2.5, 4), mul: exprand(2, 5));
        finalFreq = voiceFreq + vibrato;
        source = Saw.ar(finalFreq.lag(0.4));
        f = Select.kr(vowel, [
            [730, 1090, 2440, 3400, 4950],
            [530, 1840, 2480, 3470, 4950],
            [270, 2290, 3010, 3490, 4950],
            [570, 840, 2410, 3400, 4950],
            [300, 870, 2240, 3400, 4950]
        ]);
        a = Select.kr(vowel, [
            [1, 0.5, 0.35, 0.1, 0.02],
            [1, 0.4, 0.3, 0.08, 0.015],
            [1, 0.25, 0.2, 0.06, 0.01],
            [1, 0.45, 0.28, 0.09, 0.015],
            [1, 0.3, 0.15, 0.05, 0.008]
        ]);
        q = [0.1, 0.08, 0.05, 0.04, 0.03];
        formants = Mix.fill(5, { |i| BBandPass.ar(source, f[i], q[i]) * a[i] });
        sig = Pan2.ar(formants * env * volume * gate * 0.5, pan);
        Out.ar(out, sig);
    })
    """
}

def create_supercollider_synth(s: Session, name: str):
    return s.new_supercollider_part(name, SC_PARTS[name])
    
