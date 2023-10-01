define :background_sound do |pitch, amp, pan, rate|
    use_bpm 30
    
    chords = [chord(:E3, :minor),chord(:A3, :major), chord(:B3, :minor), chord(:G3, :major)]
    
    live_loop :bass_melody do
      chords.each do |chord|
        chord.each do |note|
          use_synth :dark_ambience
          play note + pitch, attack: 3, release: 3, amp: 0.2 , pan: pan
          if one_in(4)
            with_fx :echo, mix: 0.3, phase: 0.2 do
              sample :bass_thick_c, rate: rate +1.2, amp: 0.2, attack: 2.3, decay: 1.4, sustain: 1.2, release: 1.7
            end
          end
          sleep 25
        end
      end
    end
    
    live_loop :singletone do
      with_fx :ping_pong do
        use_synth :hollow
        play :Fs2 + pitch, attack: 0.5, release: 1, amp: amp, pan: pan
      end
      sleep 3
    end
    
    live_loop :string do
      use_synth :blade
      play_pattern_timed [chord(:E3, :minor7).choose + pitch, chord(:A3, :minor7).choose + pitch], [1], attack: 1.5, attack_level: 1, decay: 0.2, sustain_level: 0.4, sustain: 1, release: 0.5, amp: 0.1, pan: pan
      sleep 13
    end
    
    live_loop :crescendo do
      with_fx :reverb, room: 0.8 do
        use_synth :growl
        play chord(:E4, :minor).choose + pitch, attack: 0.4, release: 0.7, amp: 0.2, pan: pan, res: 0.9
      end
      sleep 7
    end
    
    live_loop :crescendo do
      with_fx :reverb, room: 0.8 do
        use_synth :growl
        play chord(:E4, :major).choose - pitch, attack: 0.5, release: 1.4, amp: 0.2, pan: pan, res: 0.9
      end
      sleep 14
    end
  end
  
  #pitch [0,20]
  #amp [0,1]
  #pan [-1,1]
  #rate[-10,10]
  background_sound pitch=1, amp=0.2, pan=0.2, rate=-5
  
  