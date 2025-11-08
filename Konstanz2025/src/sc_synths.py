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
        sig = LPF.ar(sig, 800);
        //sig = LPF.ar(sig, LFNoise1.kr(0.15).range(400, 1200));  // Gentle low-pass for warmth 
        
        // LIGHT reverb (reduced parameters to save CPU)
        //sig = FreeVerb.ar(sig, 0.65, 0.8, 0.5);
        
        sig = Pan2.ar(sig * volume * env * 0.2, pan);
        Out.ar(out, sig);
    })
    """,

    "pad_synth2": r"""

    SynthDef(\pad_synth2, { |outBus=0, freq=200, amp=0.2, pan=0, volume=0.2, gate=1|
        var osc, sig, detune, mod, env;
        // Long attack/release envelope for smooth morphing
        env = EnvGen.kr(Env.linen(8, 20, 12, 1, 'sine'), doneAction: 2);
        // Slow LFO modulation for movement
        mod = LFNoise1.kr(0.05).range(0.97, 1.03);
        detune = LFNoise1.kr(0.08).range(-0.2, 0.2);
        // Rich harmonic stack with detuning
        osc = Mix.new([
            SinOsc.ar(freq * 0.5 * mod, 0, 0.3),
            SinOsc.ar(freq * 0.501 + detune, 0, 0.25),
            Saw.ar(freq * 1.5 * mod, 0.15),
            Pulse.ar(freq * 2.99, LFNoise1.kr(0.1).range(0.3, 0.7), 0.12),
            SinOsc.ar(freq * 3.01 - detune, 0, 0.18),
            SinOsc.ar(freq * 5, 0, 0.1)
        ]);
        // Subtle chorus/shimmer effect
        sig = osc + DelayC.ar(osc, 0.05, LFNoise1.kr(0.2).range(0.01, 0.03), 0.4);
        sig = HPF.ar(sig, 40);
        sig = LPF.ar(sig, LFNoise1.kr(0.15).range(800, 3200));
        // Deep reverb
        sig = FreeVerb.ar(sig, 0.95, 0.95, 0.7);
        // Stereo spread
        sig = sig + PitchShift.ar(sig, 0.2, LFNoise1.kr(0.3).range(0.998, 1.002), 0, 0.01);
        sig = Pan2.ar(sig * amp * env * 0.6, pan);
        Out.ar(outBus, sig);
		})

    """,

    "bass_synth": r"""
    SynthDef(\bass_synth, { |out=0, freq=440, volume=0.5, gate=1|
        var pan, carrier, modulator, mod_env, amp_env, sig, sub, metal, mid, harmonic;
        
        // Random pan (narrower for bass)
        pan = rrand(-0.2, 0.2);
        
        // SHORT staccato envelope: 0.05s attack, 0.3s sustain, 0.15s release = 0.5s total
        amp_env = Env.linen(0.05, 0.3, 0.15, 1, 'sine').kr(doneAction: 2);
        mod_env = Env.perc(0.01, 0.4, 1, -4).kr;
        
        // FM synthesis
        modulator = SinOsc.ar(freq * 2.1, 0, freq * mod_env * 12);
        carrier = SinOsc.ar(freq + modulator, 0, 0.8);
        
        // Brighter harmonics (increased levels)
        metal = SinOsc.ar(freq * 1.5 + (modulator * 0.4), 0, 0.5);   // Increased from 0.35
        mid = SinOsc.ar(freq * 3 + (modulator * 0.2), 0, 0.35);      // Increased from 0.25
        harmonic = SinOsc.ar(freq * 4, 0, 0.2);                       // Increased from 0.15
        
        // Deep sub component
        //sub = SinOsc.ar(freq * 0.5, 0, 0.6);
        
        sig = (carrier + metal + mid + harmonic) * amp_env;
        
        // Brighter filter (raised cutoff)
        sig = LPF.ar(sig, 3500);  // Raised from 2500
        sig = HPF.ar(sig, 35);
        
        // Subtle saturation
        //sig = (sig * 1.3).tanh;
        
        Out.ar(out, Pan2.ar(sig * volume, pan));  // gate removed (doneAction handles it)
    })
    """,

    "smooth_bass_synth": r"""
    SynthDef(\smooth_bass, { |out=0, freq=440, volume=0.5, gate=1|
    var pan, carrier, modulator, mod_env, amp_env, sig, sub, warmth, air, detune;
    
    // Gentle pan
    pan = rrand(-0.3, 0.3);
    
    // SMOOTHER, LONGER envelopes for sustained vibe
    amp_env = Env.adsr(
        attackTime: 0.08,    // Slightly longer attack
        decayTime: 0.15,     // Gentle decay
        sustainLevel: 0.7,   // Sustained portion
        releaseTime: 0.3,    // Longer release for smooth fade
        peakLevel: 1.0,
        curve: -2
    ).kr(doneAction: 2);
    
    mod_env = Env.adsr(0.05, 0.2, 0.3, 0.25).kr;
    
    // Detuned oscillators for warmth
    detune = 1.005; // Slight detune
    carrier = Mix([
        SinOsc.ar(freq, 0, 0.6),
        SinOsc.ar(freq * detune, 0.5, 0.4)
    ]);
    
    // Gentle FM modulation
    modulator = SinOsc.ar(freq * 1.8, 0, freq * mod_env * 4); // Reduced modulation index
    
    // Warm harmonic content
    warmth = Mix([
        SinOsc.ar(freq * 2, 0, 0.3),    // Octave
        SinOsc.ar(freq * 3, 0.2, 0.15), // 12th
        SinOsc.ar(freq * 0.5, 0, 0.4)   // Sub octave
    ]);
    
    // Air/breath component
    air = LPF.ar(
        PinkNoise.ar(0.1),
        freq * 8
    ) * mod_env * 0.3;
    
    sig = (carrier + modulator + warmth + air) * amp_env;
    
    // Gentle filtering for smoothness
    sig = LPF.ar(sig, 2800); // Lower cutoff for warmth
    sig = HPF.ar(sig, 40);   // Gentle rumble filter
    
    // Subtle compression and saturation
    sig = (sig * 1.1).tanh * 0.9;
    
    // Gentle stereo enhancement
    sig = Pan2.ar(sig, pan);
    
    Out.ar(out, sig * volume);
    })
    """,

    "lead_synth": r"""
    SynthDef(\lead_synth, { |out=0, freq=440, volume=0.25, gate=1|
        var sig, env, source, filtered, pan, amp, bw;
        
        // Random parameters per grain (at synth creation, matches synth.scd)
        pan = rrand(-0.9, 0.9);
        amp = exprand(0.15, 0.35);
        bw = exprand(0.1, 0.6);
        
        // Short grain envelope
        env = EnvGen.kr(Env.perc(0.005, exprand(0.05, 0.2), 1, -6), doneAction: 2);
        
        // Source: mixture of saw and noise for spectral richness
        // Uses PASSED freq parameter (randomized in Python)
        source = Mix.ar([
            LFSaw.ar(freq * LFNoise1.kr(exprand(5, 20)).range(0.98, 1.02), 0, 0.7),
            PinkNoise.ar(0.8)
        ]);
        
        // Multiple bandpass filters for spectral sculpting
        filtered = Mix.ar([
            BPF.ar(source, freq, bw),
            BPF.ar(source, freq * LFNoise1.kr(exprand(2, 10)).range(1.5, 2.5), bw * 0.8),
            BPF.ar(source, freq * LFNoise1.kr(exprand(1, 8)).range(0.5, 0.7), bw * 1.2)
        ]);
        
        // Add shimmer with pitch shift (0.4-0.6 = down almost an octave!)
        sig = filtered + PitchShift.ar(filtered, 0.05, LFNoise1.kr(10).range(0.4, 0.6), 0, 0.01, 0.3);
        sig = sig * env * amp * volume;  // gate not used - synth frees itself via doneAction
        
        // Pan before FX (matches synth.scd routing)
        sig = Pan2.ar(sig, pan);
        
        // FX chain: reverb + delay for watery texture
        sig = FreeVerb.ar(sig, 0.5, 0.9, 0.5);
        sig = sig + CombN.ar(sig, 0.6, 0.45, 3, 0.4);
        
        Out.ar(out, sig);
    })
    """,

    
}

def create_supercollider_synth(s: Session, name: str):
    return s.new_supercollider_part(name, SC_PARTS[name])
    
