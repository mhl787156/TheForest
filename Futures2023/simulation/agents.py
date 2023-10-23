from typing import List, Tuple
import time
import random
import os
import json

class Agent(object):
    
    def __init__(self, num_tubes):
        self.num_tubes = num_tubes
        self.last_call_time = time.time()

    def call(self, current_lights: List[Tuple[float]]) -> int:
        self.current_call_time = time.time()
        self.time_since_last_call = self.current_call_time - self.last_call_time
        self.last_call_time = self.current_call_time

        return self.__call(self.time_since_last_call, current_lights)

    def __call(self, time_since_last_call:float, current_lights: List[Tuple[float]]) -> int:
        """TO IMPLEMENT IN SUBCLASSES

        Args:
            time_since_last_call (float): The time since last call
            current_lights (List[Tuple[float]]): The current set of lights
        """
        return -1

class RandomAgent(Agent):

    def __init__(self, num_tubes, delay_mu=5, delay_sigma=1, press_mu=2, press_sigma=0.5) -> None:
        super().__init__(num_tubes) # Call parent class

        self.delay = 0.0
        self.press_length = 0.0

        self.tube_choice = 0

        self.delay_mu = delay_mu
        self.delay_sigma = delay_sigma
        self.press_mu = press_mu
        self.press_sigma = press_sigma

    def __call(self, time_since_last_call:float, current_lights: List[Tuple[float]]) -> int:
        """Randomly press tube based on a randomly chosen delay for a randomly chosen amount of time

        Args:
            time_since_last_call (float): The time since last call
            current_lights (List[Tuple[float]]): The current set of lights
        """
        remaining_delay = self.delay - time_since_last_call
        press_length = self.press_length - time_since_last_call

        if remaining_delay <= 0.0:
            # Press Button
            if press_length <= 0.0:               
                # Reset Delay Press 
                self.delay = random.gauss(self.delay_mu, self.delay_sigma) # Dunno how good this is? 

                # Finished Press
                self.press_length = random.gauss(self.press_mu, self.press_sigma)

                # Start Press
                self.tube_choice = random.choice(range(self.num_tubes))

            else:
                self.press_length = press_length
            
            return self.tube_choice
            
        else:
            self.delay = remaining_delay
            return -1
        