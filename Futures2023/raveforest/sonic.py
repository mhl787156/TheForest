from threading import Thread, Condition
from multiprocessing import Value
import time

def timing_thread(condition, bpm_value):

    while True:
        with condition:
            condition.notifyAll()
        delay = 1.0 / (bpm_value.value / 60)
        time.sleep(delay)


def run_next_beat(condition, callback, beats_in_the_future):
    for _ in range(beats_in_the_future):
        with condition:
            condition.wait()
    callback()

def sonic_thread(condition, pan):
    p = PillarSequencer()
    while True:

        with condition:
            condition.wait()

class SoundManager(object):

    def __init__(self, bpm=60):
        
        self.bpm_shared = Value('i', bpm)
        self.timing_condition = Condition()

        # Start BPM Thread
        bpm_thread = Thread(name="bpm_thread", 
                            target=timing_thread, 
                            args=(self.timing_condition, self.bpm_shared,))
        bpm_thread.daemon = True
        bpm_thread.start()

    def set_bpm(self, bpm):
        self.bpm_shared.value = bpm

    def run_on_next_beat(self, callback, beats_in_the_future=1):
        """Run a callback on one of the next beats in the future (defaults to next beat)

        Args:
            callback (function): Any function that can be passed to a thread
            beats_in_the_future (int, optional): Number of beats in the future to schedule this callback. Defaults to 1.
        """
        t = Thread(target=run_next_beat, args=(self.timing_condition, callback, beats_in_the_future, ))
        t.daemon = True
        t.start()




class PillarSequencer(object):

    def __init__(self):
        pass


