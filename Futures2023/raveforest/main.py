import time
import atexit

from psonic import *

from .gui import GUI
from .pillar_hw_interface import Pillar

class Controller():

    def __init__(self, num_pillars):
        self.num_pillars = num_pillars

        self.pillars = {
            0: Pillar(0, "COM3"),
            1: Pillar(1, "COM4")
        }

        self.running = True
        atexit.register(self.stop)
    
    def start(self, frequency=10):
        delay = 1.0/frequency

        while self.running:
            start_time = time.time()  # Record the start time
            self.loop()  # Call your function

            # Calculate the time elapsed during the function execution
            elapsed_time = time.time() - start_time

            # If the function execution took less time than the desired delay, sleep for the remaining time
            if elapsed_time < delay:
                time.sleep(delay - elapsed_time)
    
    def stop(self):
        self.running = False
        
    def loop(self):
        
        for _, p in self.pillars:
            p.read_from_serial()


def main():
    c = Controller(2)
    GUI(c).run(debug=True)



