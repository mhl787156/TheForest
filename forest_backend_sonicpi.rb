# Welcome to Sonic Pi

samples = "/home/pi/TheForest/Samples/"
bird_song = "269570__vonora__cuckoo-the-nightingale-duet.wav"
roads = "469313__2hear__ambient-street-traffic-dublin.wav"

use_bpm 60
use_osc "localhost", 4559

set :request_stop_samples_list, []
set :currently_playing, []

define :sample_player_2 do |samples, sname, start, finish|
  return live_loop sname do
    dur = sample_duration samples, sname, start: start, finish: finish
    qdur = quantise(dur, 1) # To make sure the sample finishes on beat.
    
    # Play full sample 
    s = sample samples, sname,
      start: start, finish: finish,
      amp: 1, rate: 1, beat_stretch: qdur, release: 0.3, attack: 0.3
    control s
    
    # While sample is playing, monitor every beat to see if buttons have been pressed
    slice_i = 0
    qdur.times do
      
      print slice_i
      sleep 1
      slice_i += 1
      
      rssl = get[:request_stop_samples_list]
      print sname, rssl, rssl.include?(sname)
      if rssl.include? sname
        print "Requested Stop", sname
        
        modrssl = rssl.dup
        modrssl.delete(sname)
        set :request_stop_samples_list, modrssl
        
        cplay = get[:currently_playing].dup
        cplay.delete(sname)
        set :currently_playing, cplay
        
        control s, amp: 0, amp_slide: 1

        sample_free samples, sname
        stop
      end
    end
  end
end



live_loop :startcue do #wait for incoming /start OSC message
  use_real_time
  b = sync "/osc*/start"
  rssl = get[:currently_playing].dup
  if !rssl.include?(b[0])
    sample_player_2 samples, b[0], 0, 1.0
    rssl.push(b[0]) # b is a list so need to get first element
    set :currently_playing, rssl
  end
end

live_loop :stopcue do #wait for incvoming /stop OSC message
  use_real_time
  print "Watiing on stop message"
  b = sync "/osc*/stop"
  print "Received on stop", b
  rssl = get[:request_stop_samples_list].dup
  rssl.push(b[0]) # b is a list so need to get first element
  set :request_stop_samples_list, rssl
end

#live_loop :checkstate do
#  rssl = get[:request_stop_samples_list].dup
#  print "RSSL:", rssl
# sleep 4
#end



# sb1 = sample_player samples, bird_song, 0, 1.0
# sr1 = sample_player samples, roads, 0, 0.5

# print sb1

#osc "/stop", "269570__vonora__cuckoo-the-nightingale-duet.wav"
#reqssl = get[:request_stop_samples_list].dup
#print(reqssl)
#reqssl.push("269570__vonora__cuckoo-the-nightingale-duet.wav")
#set :request_stop_samples_list,reqssl
