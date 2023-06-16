use_bpm 60
use_osc "localhost", 4559

set :request_stop_samples_list, []
set :currently_playing, []

define :sample_player_2 do |samples, sname, start, finish|
  # Thread with name seems to work best
  # Deals with case of multiple starts without stops
  # Sync deals with case of stopping (only play once)
  return in_thread do
    print "Starting thread", sname
    dur = sample_duration samples, sname, start: start, finish: finish
    qdur = quantise(dur, 1) # To make sure the sample finishes on beat.
    
    # Play full sample
    s = sample samples, sname,
      start: start, finish: finish,
      amp: 1, rate: 1, beat_stretch: qdur, release: 0.5, attack: 0.5
    control s
    
    print "Syncing on", sname
    sync sname
    control s, amp: 0, amp_slide: 1
    # sample_free samples, sname
    print "Live loop stopped", sname
    stop
  end
end


live_loop :startcue do #wait for incoming /start OSC message
  use_real_time
  b = sync "/osc*/start"
  print "Received to start", b
  t = sample_player_2 samples, b[0], 0, 1.0
  print "Thread", t
end

live_loop :stopcue do #wait for incvoming /stop OSC message
  use_real_time
  print "Watiing on stop message"
  b = sync "/osc*/stop"
  print "Received on stop", b
  cue b[0]
end