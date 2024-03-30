from threading import Thread, Condition, Event
from multiprocessing import Value
import time
import queue
import socket

from psonic import *

def setup_psonic(udp_ip, log_file):
    set_server_parameter_from_log(udp_ip, log_file)

def timing_thread(condition, bpm_value):
    print(f"Started timing thread")
    while True:
        with condition:
            condition.notifyAll()
        delay = 1.0 / (bpm_value.value / 60)
        time.sleep(delay)


def run_next_beat(condition, callback, kill_event, beats_in_the_future):
    for _ in range(beats_in_the_future):
        with condition:
            condition.wait()
    # If it has not been cancelled
    if not kill_event.is_set():
        callback()
    else:
        print("Thread killed")

def sonic_thread(pillar, bpm, condition, notes_in_queue):
    print(f"Started sonic thread sequencer for {pillar.id}")
    p = PillarSequencer( pillar, bpm, condition, notes_in_queue)
    p.run()

class SoundManager(object):

    def __init__(self, bpm, pillars):
        
        self.bpm_shared = Value('i', bpm)
        self.timing_condition = Condition()
        self.current_synths = {}
        self.current_amp = {}
        self.current_notes = {}

        # Start BPM Thread
        bpm_thread = Thread(name="bpm_thread", 
                            target=timing_thread, 
                            args=(self.timing_condition, self.bpm_shared,))
        bpm_thread.daemon = True
        bpm_thread.start()

        # Start queue and thread for each pillar
        self.pillar_data_in_queues = {p_id: queue.Queue() for p_id in pillars.keys()}
        self.pillar_sequencers = {}
        for p_id, pillar  in pillars.items():
            pthread = Thread(target=sonic_thread, 
                                args=(pillar, self.bpm_shared, self.timing_condition, self.pillar_data_in_queues[p_id],))
            pthread.daemon = True
            pthread.start()
            self.pillar_sequencers[p_id] = pthread


            self.set_amp(p_id, 1.0)
            self.set_synth(p_id, "SAW")

        
        # Others
        self.run_on_next_beat_events = {}

    def get_bpm(self):
        return self.bpm_shared.value

    def set_bpm(self, bpm):
        self.bpm_shared.value = bpm

    def set_notes(self, pillar_id, notes):
        self.current_notes[pillar_id] = notes
        self.pillar_data_in_queues[pillar_id].put({"notes": notes})
    
    def get_notes(self, pillar_id):
        return self.current_notes[pillar_id]

    def get_all_notes(self):
        return self.current_notes

    def set_synth(self, pillar_id:int, synth:str):
        if synth in globals():
            self.current_synths[pillar_id] = synth
            # Convert synth name as a string into the variable
            var = globals()[synth]
            self.pillar_data_in_queues[pillar_id].put({"synth": var})
        else:
            print(f"Synth '{synth}' not found")
    
    def set_amp(self, pillar_id:int, amp:float):
        self.current_amp[pillar_id] = amp
        self.pillar_data_in_queues[pillar_id].put({"amp": amp})
    
    def get_amps(self):
        return self.current_amp

    def get_synths(self):
        return self.current_synths
    
    def get_synth(self, pillar_id):
        return self.current_synths[pillar_id]

    def run_on_next_beat(self, callback, beats_in_the_future=1, force_unique_id=None):
        """Run a callback on one of the next beats in the future (defaults to next beat)

        Args:
            callback (function): Any function that can be passed to a thread
            beats_in_the_future (int, optional): Number of beats in the future to schedule this callback. Defaults to 1.
            force_unique_id (Union[int, None], optional): if there should only ever be one version of this callback
        """
        kill_event = Event()
        t = Thread(target=run_next_beat, args=(self.timing_condition, callback, kill_event, beats_in_the_future, ))
        t.daemon = True
        t.start()

        if force_unique_id is not None:
            if force_unique_id in self.run_on_next_beat_events:
                self.run_on_next_beat_events[force_unique_id].set()

            self.run_on_next_beat_events[force_unique_id] = kill_event

            print("Setting unique id", force_unique_id)

class PillarSequencer(object):

    def __init__(self, pillar, bpm, condition, notes_in_queue):
        self.condition = condition
        self.pillar = pillar
        self.bpm_value = bpm
        self.notes_in_queue = notes_in_queue
        self.amp = 1.0
        self.delay =  (1.0 / (self.bpm_value.value / 60)) / 2.0 

        self.current_notes = None # This is now a sound state object
        self.seq_current_idx = 1
    
    def run(self):
        while True:
            with self.condition:
                self.condition.wait()
            
            try:
                while True:
                    packet = self.notes_in_queue.get(block=False)
                    
                    if "notes" in packet:
                        new_notes = packet["notes"]
                        print(f"Got New Notes! {new_notes}")
                        # Check new note properties and do something?
                        self.current_notes = new_notes

                    if "synth" in packet:
                        print(f"Setting Synth to {packet['synth'].name}")
                        use_synth(packet["synth"])
                    

                    if "amp" in packet:
                        print(f"Setting amp {packet['amp']}")
                        self.amp = packet["amp"]

            except queue.Empty:
                pass

            time.sleep(self.delay * int(self.pillar.id))

            # Play the note
            current_note = self.current_notes.note
            print(f"{self.pillar.id} playing {current_note} with seqidx: {self.seq_current_idx}")
            play(current_note, amp=self.amp)

            self.advance_seq()

    def advance_seq(self):
        self.seq_current_idx = (self.seq_current_idx + 1) % self.pillar.num_touch_sensors
