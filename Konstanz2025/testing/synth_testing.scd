SynthDef(\bassHum_beating, {
	arg out=0, amp=2.0, baseHz=36, spread=0.45, drift=0.02, color=0.4, atk=10, rel=40;
	// var freqs = baseHz* [1, 1.0015, 0.999].linexp(0,1,[1,1+spread,-1*spread]);
	var lfos  = LFNoise2.kr(0.02!3).range(1-drift, 1+drift);
	var sig   = SinOsc.ar(baseHz * lfos, Rand(0,2pi)!3).sum * (amp/3);
	var tilt = color.linlin(0,1,-6,6); // dB shift
	sig = tanh(sig * 2.0);

	sig = BLowShelf.ar(sig, 120, 1, tilt); // counter-tilt
	//sig = LPF.ar(sig, 300);
	sig = Balance2.ar(sig, sig);
	sig = sig * Env.asr(atk, 1, rel).kr(doneAction:2);
	Out.ar(0, sig);
}).play;

SynthDef(\bassHum_notch, { |out=0, amp=1.0, baseHz=48, noise=0.12, notchQ=0.2, atk=8, rel=50|
	var core  = LFSaw.ar(baseHz*[0.5,1], 0).tanh * 0.4
	          + LPF.ar(WhiteNoise.ar(noise), 400);
	var center = (LFNoise1.kr(0.01).range(120, 600));
	var sig = BPF.ar(core, center, notchQ).tanh * amp;
	sig = Splay.ar(sig, 0.25);
	sig = sig * Env.asr(atk,1,rel).kr(doneAction:2);
	sig.scope;
	Out.ar(0, sig);
}).play;

SynthDef(\bassHum_reson, { |amp=1.0, freq=32, rq=0.08, excite=0.1, mod=0.02, atk=6, rel=60|
	var trig = Dust.kr(excite);
	var exc  = Decay2.ar(Trig1.ar(trig,0.005), 0.01, 0.3) * PinkNoise.ar(0.2);
	var fmod = LFNoise2.kr(0.02).range(1-mod,1+mod);
	var body = RLPF.ar(exc, freq*fmod, rq).tanh;
	body = body + (CombL.ar(body, 0.2, 1/(freq.clip(20,200)), 6) * 0.2);
	body = LPF.ar(body, 300);
	body = Splay.ar(body, 0.2) * amp;
	body = body * Env.asr(atk,1,rel).kr(doneAction:2);
	body.scope;
	Out.ar(0, body);
}).play;


SynthDef(\melody_reed, { |out=0, amp=1.0, freq=440, bend=0, breath=0.15, vib=0.2, atk=0.02, rel=4|
	var v = SinOsc.kr(5, 0, vib*0.01+0.001);
	var f = freq * (bend.midiratio) * (1+v);
	var exc = LPF.ar(WhiteNoise.ar(breath), f*2);
	var body = LPF.ar(Blip.ar(f, 5), f*1.5) + exc*0.2;
	body = RLPF.ar(body.tanh, f*1.2, 0.2);
	body = body * Env.perc(atk, rel, curve: -3).kr(doneAction:2) * amp;
	Out.ar(0, body!2);
}).play;

SynthDef(\pop_pip, { |amp=1.0, freq=1200, rel=0.08, bend=0|
	var env = Env.perc(0.0008, rel, curve:-6).kr(doneAction:2);
	var sig = SinOsc.ar(freq * (bend.midiratio)) * env;
	sig = BPF.ar(sig, freq*1.2, 0.4);
	Out.ar(0, (sig!2) * amp);
}).play;

SynthDef(\pop_sparkle, { |amp=1, cf=3000, q=0.15, rel=0.12|
	var exc = Decay2.ar(Impulse.ar(0), 0.002, rel) * WhiteNoise.ar(0.6);
	var bands = Mix([1.0,1.26,1.5,2.0].collect{|r| BPF.ar(exc, cf*r, q) });
	var sig = (bands * 0.5).tanh * amp;
	DetectSilence.ar(sig, doneAction:2);
	Out.ar(0, Splay.ar(sig, 0.7));
}).play;

SynthDef(\pop_fmblip, { |out=0, amp=1.0, freq=600, idx=3, atk=0.001, rel=0.2, color=0.6|
	var mod = SinOsc.ar(freq*1.99) * freq * idx;
	var sig = SinOsc.ar(freq + mod);
	sig = BPF.ar(sig, freq*(1.5+color*2), 0.3);
	sig = sig * Env.perc(atk, rel, curve: -8).kr(doneAction:2) * amp;
	Out.ar(0, Splay.ar(sig, 0.6));
}).play;


// ~scales = [
// 	Scale.minorPentatonic,
// 	//Scale.ryukyu, // bright pentatonic
// 	Scale.dorian,
// 	Scale.major // fallback if akira missing
// ];
//
// SynthDef(\melody_modalGlass, { |out=0, amp=1.0, midinote=60, modeIdx=0, bright=0.5, atk=0.01, rel=6|
// 	var scale = Select.kr(modeIdx.clip(0, ~scales.size-1), ~scales.collect{ |sc| sc.as(LocalBuf).bufnum }.asArray);
// 	// translate MIDI to freq externally; here we just render
// 	var f = midinote.midicps;
// 	var partials = [1, 2.01, 2.5, 3.01, 4.2];
// 	var env = Env.perc(atk, rel, curve: -4).kr(doneAction:2);
// 	var sig = Mix.fill(partials.size, { |i|
// 		var a = (1/(i+1)).pow(0.9);
// 		SinOsc.ar(f*partials[i], 2pi.rand) * a
// 	});
// 	sig = sig * (0.3 + bright*0.7);
// 	sig = BPF.ar(sig, f*3, 0.2) + sig*0.5;
// 	sig = sig * env * amp;
// 	Out.ar(0, sig!2);
// }).play;

SynthDef(\melody_karplus, { |out=0, amp=30.0, freq=330, damp=0.3, decay=8, pick=0.3|
	var exc = Decay2.ar(Impulse.ar(0), 0.005, 0.08) * PinkNoise.ar(pick);
	var sig = Pluck.ar(exc, trig:1, maxdelaytime:0.2, delaytime:freq.reciprocal, decaytime:decay, coef:(1-damp.clip(0,1)));
	sig.scope;
	sig = LPF.ar(sig, freq*3);
	sig = sig * amp;
	Out.ar(0, sig);
	//DetectSilence.ar(sig, doneAction:2);
	//Out.ar(0, sig!2);
}).play;


SynthDef(\mel_bells, { |out=0, amp=0.08, freq=440, bright=0.6, atk=0.005, rel=4|
	var parts = [1, 2.7, 3.8, 5.1, 6.7];
	var env = Env.perc(atk, rel, curve:-4).kr(doneAction:2);
	var sig = Mix.fill(parts.size, { |i|
		var a = (1/(i+1)).pow(0.9);
		SinOsc.ar(freq*parts[i], 2pi.rand) * a
	});
	sig = (HPF.ar(sig, 200) * (0.3 + bright*0.7));
	sig = (sig!2) * env * amp;
	Out.ar(out, sig);
}).play;

SynthDef(\mel_vocal, { |out=0, amp=1.0, freq=330, vowel=0.8, vib=0.2, atk=0.02, rel=3|
	var v = SinOsc.kr(5).range(-1*vib*0.01, vib*0.01);
	var f = freq * (1+v);
	// interpolate a couple of formants
	var f1 = LinLin.kr(vowel, 0,1, 500, 900);
	var f2 = LinLin.kr(vowel, 0,1, 1100, 1500);
	var f3 = LinLin.kr(vowel, 0,1, 2500, 2800);
	var src = Blip.ar(f, 8).tanh;
	var sig = BPF.ar(src, f1, 0.2) * 0.7 + BPF.ar(src, f2, 0.1) * 0.4 + BPF.ar(src, f3, 0.08) * 0.3;
	sig = (sig!2) * Env.perc(atk, rel, curve:-3).kr(doneAction:2) * amp;
	Out.ar(out, sig);
}).play;

SynthDef(\mel_softEP, { |out=0, amp=0.07, freq=330, index=1.2, ratio=2, atk=0.005, dec=1.2, rel=4, tone=3000|
	var envA = Env.perc(atk, dec, curve:-4).kr;
	var envR = Env.asr(0,1,rel).kr(doneAction:2);
	var mod  = SinOsc.ar(freq*ratio) * (freq*index*envA);
	var car  = SinOsc.ar(freq + mod);
	var body = LPF.ar(car.tanh, tone);
	var sig  = (body!2) * envR * amp;
	// sig.scope;
	Out.ar(out, sig);
}).play;

SynthDef(\mel_pluckLite, { |out=0, amp=2.0, freq=440, damp=0.35, decay=6|
	var exc = Decay2.ar(Impulse.ar(0), 0.003, 0.06) * PinkNoise.ar(0.5);
	var sig = Pluck.ar(exc, 1, 0.2, freq.reciprocal, decay, 1-damp);
	sig = LPF.ar(sig, freq*4);
	DetectSilence.ar(sig, doneAction:2);
	Out.ar(out, (sig!2) * amp);
}).play;

SynthDef(\mel_shimmer, { |out=0, amp=0.06, freq=330, mix=0.35, atk=0.02, rel=7|
	var env = Env.perc(atk, rel, curve:-2).kr(doneAction:2);
	var src = Saw.ar(freq).tanh * 0.4;
	var halo = PitchShift.ar(src, 0.15, 2.0) + PitchShift.ar(src, 0.15, 0.5);
	var sig = XFade2.ar(src, halo, (mix*2-1)) * env;
	Out.ar(out, (sig!2) * amp);
}).play;

SynthDef(\mel_chimeCluster, { |out=0, amp=0.07, freq=440, spread=0.06, count=4, rel=5|
	var freqs = Array.fill(count, { freq * (1 + LFNoise2.kr(0).range(-1*spread, spread)) * [1,1.5,1.25,2].choose });
	var env   = Env.perc(0.003, rel, curve:-5).kr(doneAction:2);
	var sig   = Mix.fill(count, { |i| SinOsc.ar(freqs[i], 2pi.rand) * (1/(i+1)).sqrt });
	sig = HPF.ar(sig, 250);
	Out.ar(out, (sig!2) * env * amp);
}).play;

SynthDef(\bass_hollow5, { |out=0, amp=100.0, base=36, spread=0.5, atk=2, rel=14|
	var f1 = base;
	var f2 = base * 1.5; // perfect fifth
	var det = LFNoise2.kr(0.05!2).range(1-spread*0.01, 1+spread*0.01);
	var sig = (SinOsc.ar([f1,f2]*det).sum * 0.7).tanh;
	sig = LPF.ar(sig, 800);
	sig = (sig!2) * Env.asr(atk,1,rel).kr(doneAction:2) * amp;
	Out.ar(out, sig);
}).play; //Nah sounds like kick drum hits

SynthDef(\bass_subPulse, { |out=0, amp=1.0, freq=36, pwm=0.5, wobble=0.1, atk=2, rel=12, tone=150|
	var lfo = SinOsc.kr(0.08, 0).range(-1 * wobble, wobble);
	var pw  = (pwm + lfo).clip(0.05, 0.95);
	var sig = Pulse.ar(freq, pw).tanh * 0.6 + LFTri.ar(freq/2)*0.2;
	sig = LPF.ar(sig, tone.clip(80, 2000));
	sig = (sig!2) * Env.asr(atk, 1, rel).kr(doneAction:2) * amp;
	Out.ar(out, sig);
}).play;  // Quite nice

SynthDef(\bass_fmGrowl, { |out=0, amp=0.08, freq=45, ratio=1.99, index=2.5, drift=0.02, atk=0.5, rel=10|
	var mod = SinOsc.ar(freq*ratio, 0, freq*index);
	var base = SinOsc.ar(freq + mod);
	var slow = LFNoise2.kr(0.1).range(1-drift, 1+drift);
	var sig = (base * slow).tanh;
	sig = LPF.ar(sig, 600);
	sig = (sig!2) * Env.asr(atk,1,rel).kr(doneAction:2) * amp;
	Out.ar(out, sig);
}).play; // Also Quite nice

SynthDef(\bass_tapeSine, { |out=0, amp=0.09, freq=32, wow=0.2, flutter=0.03, atk=3, rel=20|
	var wowL   = SinOsc.kr(0.25).range(-1*wow, wow);
	var wowH   = SinOsc.kr(5.3).range(-1*flutter, flutter);
	var fmod   = (wowL + wowH);
	var sig    = SinOsc.ar(freq * (1 + fmod)).tanh;
	sig = (sig!2) * Env.asr(atk,1,rel).kr(doneAction:2) * amp;
	Out.ar(out, sig);
}).play; // Gentle Pulsing

SynthDef(\bass_grain, { |out=0, amp=2.0, base=40, dens=2, rq=0.1, atk=3, rel=18|
	var trig = Dust.ar(dens); // few grains per second
	var exc  = Decay2.ar(trig, 0.01, 0.2) * PinkNoise.ar(0.4);
	var body = RLPF.ar(exc, base, rq).tanh;
	body = body + CombL.ar(body, 0.2, 1/base, 4)*0.2;
	body = LPF.ar(body, 400);
	body = (body!2) * Env.asr(atk,1,rel).kr(doneAction:2) * amp;
	Out.ar(out, body);
}).play;



// pick one melody
Synth(\mel_bells, [\freq, 523, \rel, 7, \amp, 100.0]);
Synth(\mel_softEP, [\freq, 392, \amp, 100.0]);
Synth(\mel_vocal, [\freq, 330, \vowel, 0.7]);

// Synth(\bassHum_reson, [\baseHz, [30,36,42].choose, \amp, 10.0]); //, \color, In.kr(~colorCtl)]);


// { 90.linexp(0,1,1.45) }.scope

