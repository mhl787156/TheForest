
"""
    The code defines classes and functions for managing and playing sounds using the psonic library in
    Python, including setting parameters, scheduling callbacks on future beats, and running a sequencer
    for each pillar.
    
    :param udp_ip: The `udp_ip` parameter is used to specify the IP address of the UDP server
    for communication. This is used in networking applications to define the destination IP
    address for sending UDP packets
    :param log_file: The `log_file` parameter in the `setup_psonic` function is used to specify the path
    to a log file that contains information needed to set up the Psonic server. This log file likely
    contains details such as the UDP IP address for communication
    
    SoundManager: The `SoundManager` class is used to manage the threading and scheduling of sounds
    between the two pillars. Each pillars has six tubes, where each tube corresponds to a different
    sound parameter. The `SoundManager` class is responsible for setting and getting parameters for
    each tube, running callbacks on the next beat, and managing the timing of the sequencer.
    
    timing_thread: The `timing_thread` function is a thread that runs in the background to manage the
    timing of the sequencer. It uses a condition variable to notify other threads when a new beat has
    occurred, based on the current BPM value of each pillar. 
    
    run_next_beat: The `run_next_beat` function is used to run a callback on the next beat in the future.
    It takes a callback function, the number of beats in the future to run the callback, and a kill event
    to cancel the callback if needed. This function is used by the `SoundManager` class to schedule
    callbacks for each pillar.
    
    sonic_thread: The `sonic_thread` function is a thread that runs the sound for each pillar. It uses
    the `PillarSound` class to play the sound based on the parameters retrieved by the `SoundManager` class.
    
    pillar_params = {"amp": 1.0, "pitch": 50, "synth": "SAW", "bpm": 120, "pan": 0.0, "envelope": "default}
    
    pillar_params: The `pillar_params` dictionary contains the parameters for each pillar, including the
    amplitude, pitch, synth, BPM, pan, and envelope. These parameters are used to set the sound for each
    tube in the pillar. 
"""
from threading import Thread, Condition, Event
import time
from psonic import *
from psonic import play, set_server_parameter_from_log

def setup_psonic(udp_ip, log_file):
    #print(f"Setting up Psonic with UDP IP: {udp_ip} and log file: {log_file}")
    set_server_parameter_from_log(udp_ip, log_file)

class SoundManager:
    """Manages and schedules sound playback for pillars using the Sonic Pi server."""
    
    def __init__(self, pillar_configs):
        self.timing_condition = Condition()
        self.pillars = {}
        self.pillar_settings = {}  
        self.run_on_next_beat_events = {}

        tube_param = {0: 'amp', 1: 'pitch', 2: 'synth', 3: 'bpm', 4: 'pan', 5: 'envelope'}
                
        # Iterate through the provided pillar configurations to initialize Pillar instances
        for p_id, pillar_config in pillar_configs.items():
            # Extract parameters from Tubes_Param
            params = {tube_param[idx]: pillar_config.mapping.__dict__['Tubes_Param'][idx] for idx in tube_param}
            
            #print(f"Initializing Pillar {p_id} with parameters: {params}")
            
            # Create Pillar 
            new_pillar = Pillar(p_id, **params)
            self.pillars[p_id] = new_pillar
        
        #print("SoundManager initialized with the following pillars:")
        #for pillar_id, pillar in self.pillars.items():
        #    print(f"Pillar {pillar_id} Info: {pillar}")
    
    def update_pillar_setting(self, pillar_id, setting_name, value):
        """Updates the settings dictionary for a specific pillar."""
        if pillar_id not in self.pillar_settings:
            self.pillar_settings[pillar_id] = {}
        self.pillar_settings[pillar_id][setting_name] = value
        
        # Update the actual pillar object
        if pillar_id in self.pillars:
            getattr(self.pillars[pillar_id], f'set_{setting_name}')(value)  # Dynamically call the set method



        # Initialize sound parameters for each pillar
        for pillar_id, pillar in self.pillars.items():
            pillar.init_sound_thread(self.timing_condition)

        # Debugging: Print Pillar Information
        #print("SoundManager initialized with the following pillars:")
        #for pillar_id, pillar in self.pillars.items():
        #    print(f"Pillar {pillar_id} Info: {pillar}")
            
            
    def set_amp(self, pillar_id, amp):
        if pillar_id in self.pillars:
            self.pillars[pillar_id].set_amp(amp)
    
    def set_pitch(self, pillar_id, pitch):
        if pillar_id in self.pillars:
            self.pillars[pillar_id].set_pitch(pitch)
    
    def set_synth(self, pillar_id, synth):
        if pillar_id in self.pillars:
            self.pillars[pillar_id].set_synth(synth)
    
    def set_bpm(self, pillar_id, bpm):
        if pillar_id in self.pillars:
            self.pillars[pillar_id].set_bpm(bpm)
    
    def set_pan(self, pillar_id, pan):
        if pillar_id in self.pillars:
            self.pillars[pillar_id].set_pan(pan)
    
    def set_envelope(self, pillar_id, envelope):
        if pillar_id in self.pillars:
            self.pillars[pillar_id].set_envelope(envelope)

    def run_on_next_beat(self, callback, beats_in_the_future=1, unique_id=None):
        """Schedules a callback to run on the next beat."""
        kill_event = Event()
        t = Thread(target=self._run_callback_on_next_beat, args=(callback, kill_event, beats_in_the_future))
        t.daemon = True
        t.start()

        if unique_id:
            if unique_id in self.run_on_next_beat_events:
                self.run_on_next_beat_events[unique_id].set()  # Cancel the previous event if exists
            self.run_on_next_beat_events[unique_id] = kill_event

    def _run_callback_on_next_beat(self, callback, kill_event, beats_in_the_future):
        """Internal method to wait for the specified beats and then execute the callback if not killed."""
        with self.timing_condition:
            for _ in range(beats_in_the_future):
                self.timing_condition.wait()
                if kill_event.is_set():
                    return  # Exit if the event has been canceled
        callback()  # Execute the callback

class Pillar:
    """Represents a sound pillar with unique sound parameters."""
    
    def __init__(self, pillar_id, bpm=120, amp=1.0, pitch=50, synth="saw", pan=0.0, envelope="default"):
        self.pillar_id = pillar_id
        self.bpm = bpm
        self.amp = amp
        self.pitch = pitch
        self.synth = synth
        self.pan = pan
        self.envelope = envelope

        # For debugging and information
        self.parameters = {
            "amp": self.amp, "pitch": self.pitch, "synth": self.synth,
            "bpm": self.bpm, "pan": self.pan, "envelope": self.envelope
        }

    def __repr__(self):
        """String representation of the pillar for debugging."""
        return f"Pillar({self.pillar_id}) {self.parameters}"

    def set_amp(self, amp):
        self.amp = amp
    
    def set_pitch(self, pitch):
        self.pitch = pitch
    
    def set_synth(self, synth):
        self.synth = synth
    
    def set_bpm(self, bpm):
        self.bpm = bpm
    
    def set_pan(self, pan):
        self.pan = pan
    
    def set_envelope(self, envelope):
        self.envelope = envelope

        
    def init_sound_thread(self, timing_condition):

        """Initializes and starts the thread responsible for handling sound playback."""
        thread = Thread(target=self._pillar_sound_thread, args=(timing_condition,))
        thread.daemon = True
        thread.start()

    def _pillar_sound_thread(self, timing_condition):
        
        """Internal method run by a thread to handle sound playback synchronized with beats."""
        while True:
            with timing_condition:
                #timing_condition.wait()  # Wait for the next beat
                timing_condition.notifyAll()
                
                # Placeholder for actual sound playing logic
                #print(f"Pillar {self.pillar_id} playing sound with parameters: {self.parameters}")
                    
                #use_synth("SAW")
                play(self.pitch, amp=self.amp, pan=self.pan, decay=self.envelope)

                delay = 1. / (self.bpm / 60)
                time.sleep(delay)


