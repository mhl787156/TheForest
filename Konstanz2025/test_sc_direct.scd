// Test SuperCollider audio directly (no Python/SCAMP)
// Run in SuperCollider IDE or: sclang test_sc_direct.scd

s.waitForBoot({
    fork {
        "SuperCollider booted, waiting 1 second...".postln;
        1.wait;
        
        "Playing 440Hz sine wave for 1 second...".postln;
        { SinOsc.ar(440) * 0.3 ! 2 }.play;
        1.5.wait;
        
        "Playing 880Hz sine wave for 1 second...".postln;
        { SinOsc.ar(880) * 0.3 ! 2 }.play;
        1.5.wait;
        
        "Test complete. Did you hear two tones?".postln;
        "If YES: SuperCollider audio works, issue is SCAMP".postln;
        "If NO: SuperCollider/JACK configuration issue".postln;
    }
});


