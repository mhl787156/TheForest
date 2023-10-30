from typing import List, Tuple, overload
import time
import random

class Forest_Agent:
    goal=[]

    def __init__(self,num_tubes,num_pillars):
        self.last_call_time = time.time()
        self.num_tubes=num_tubes
        self.num_pillars=num_pillars

    def call(self):
        return -1

class Forest_Agent_Random(Forest_Agent):
    def __init__(self, num_tubes,num_pillars, delay_mu=5, delay_sigma=1):
        super().__init__(num_tubes,num_pillars)  # Call parent class

        self.delay = 0.0
        self.delay_mu = delay_mu
        self.delay_sigma = delay_sigma
        self.time_since_last_call=0


    def call(self,current_lights: List[List[int]]):

        self.time_since_last_call+=1
        remaining_delay = self.delay - self.time_since_last_call



        if remaining_delay <= 0.0:

            # Reset Delay Press
            self.delay = random.gauss(self.delay_mu, self.delay_sigma)
            self.time_since_last_call=0

            # Start Press
            pillar_choice=random.choice(range(self.num_pillars))
            tube_choice = random.choice(range(self.num_tubes))
            current_lights[pillar_choice][tube_choice]=random.choice([40,90,160,255])
            return current_lights
        else:
            self.delay = remaining_delay
            return []


class Forest_Agent_Yellow(Forest_Agent):
    def __init__(self, num_tubes,num_pillars,action_bias, delay_mu=5, delay_sigma=1):
        super().__init__(num_tubes,num_pillars)  # Call parent class

        self.delay = 0.0
        self.delay_mu = delay_mu
        self.delay_sigma = delay_sigma
        self.time_since_last_call=0
        self.trigger=40
        self.action_bias = action_bias


    def call(self,current_lights:List[List[int]]):

        self.time_since_last_call+=1
        remaining_delay = self.delay - self.time_since_last_call



        if remaining_delay <= 0.0:

            # Reset Delay Press
            self.delay = random.gauss(self.delay_mu, self.delay_sigma)
            self.time_since_last_call=0

            # Start Press
            pillar_choice=random.choice(range(self.num_pillars))

            for t in(range(self.num_tubes)):
                if(current_lights[pillar_choice][t] == self.trigger):
                    rule1 = random.choices([1, 0], weights=self.action_bias)
                    if (rule1==1):
                        left_action = random.choice([1, 0])
                        if (left_action==1):
                            if (t + 1 == self.num_tubes):
                                current_lights[pillar_choice][0] = 160
                            else:
                                current_lights[pillar_choice][t + 1] = 160
                        else:
                            if (t - 1 == -1):
                                current_lights[pillar_choice][0] = 160
                            else:
                                current_lights[pillar_choice][t - 1] = 160
                    else:
                        current_lights[pillar_choice][t] = 255
                        tube_choice = random.choice([a for a in range(self.num_tubes) if a!= t])
                        current_lights[pillar_choice][tube_choice] = 255
                        tube_choice = random.choice([a for a in range(self.num_tubes) if a!= t and a!=tube_choice])
                        current_lights[pillar_choice][tube_choice] = 255
                    return current_lights
            return []
        else:
            self.delay = remaining_delay
            return []


    def call_with_goal(self,current_lights:List[List[int]],goal_pattern:List[int]):

        self.time_since_last_call+=1
        remaining_delay = self.delay - self.time_since_last_call
        self.goal_color1=0
        self.goal_color2=0
        print(goal_pattern)



        if remaining_delay <= 0.0:

            # Reset Delay Press
            self.delay = random.gauss(self.delay_mu, self.delay_sigma)
            self.time_since_last_call=0

            # Start Press
            pillar_choice=random.choice(range(self.num_pillars))
            duplicates = [val for idx, val in enumerate(current_lights[pillar_choice]) if val in current_lights[pillar_choice][:idx]]
            duplicates_idx=[]
            for d in set(duplicates):
                duplicates_idx.append([idx for idx, val in enumerate(current_lights[pillar_choice]) if val==d ])

            for t in(range(self.num_tubes)):
                if(current_lights[pillar_choice][t] == self.trigger):
                    rule1 = random.choices([1, 0], weights=self.action_bias)
                    if (rule1==1):
                        left_action = random.choice([1, 0])
                        if (left_action==1):
                            if (t + 1 == self.num_tubes):
                                current_lights[pillar_choice][0] = 160
                            else:
                                current_lights[pillar_choice][t + 1] = 160
                        else:
                            if (t - 1 == -1):
                                current_lights[pillar_choice][0] = 160
                            else:
                                current_lights[pillar_choice][t - 1] = 160
                    else:
                        current_lights[pillar_choice][t] = 255
                        tube_choice = random.choice([a for a in range(self.num_tubes) if a!= t])
                        current_lights[pillar_choice][tube_choice] = 255
                        tube_choice = random.choice([a for a in range(self.num_tubes) if a!= t and a!=tube_choice])
                        current_lights[pillar_choice][tube_choice] = 255
                    return current_lights
            return []
        else:
            self.delay = remaining_delay
            return []

class Forest_Agent_Red(Forest_Agent):
    def __init__(self, num_tubes,num_pillars,action_bias ,delay_mu=5, delay_sigma=1):
        super().__init__(num_tubes,num_pillars)  # Call parent class

        self.delay = 0.0
        self.delay_mu = delay_mu
        self.delay_sigma = delay_sigma
        self.time_since_last_call=0
        self.trigger=255
        self.action_bias = action_bias


    def call(self,current_lights:List[List[int]]):

        self.time_since_last_call+=1
        remaining_delay = self.delay - self.time_since_last_call



        if remaining_delay <= 0.0:

            # Reset Delay Press
            self.delay = random.gauss(self.delay_mu, self.delay_sigma)
            self.time_since_last_call=0

            # Start Press
            pillar_choice=random.choice(range(self.num_pillars))

            for t in(range(self.num_tubes)):
                if(current_lights[pillar_choice][t] == self.trigger):
                    rule1 = random.choices([1, 0], weights=self.action_bias)
                    if (rule1==1):
                        left_action = random.choice([1, 0])
                        if (left_action==1):
                            if (t + 1 == self.num_tubes):
                                current_lights[pillar_choice][0] = 90
                            else:
                                current_lights[pillar_choice][t + 1] = 90
                        else:
                            if (t - 1 == -1):
                                current_lights[pillar_choice][0] = 90
                            else:
                                current_lights[pillar_choice][t - 1] = 90
                    else:
                        current_lights[pillar_choice][t] = 40
                        tube_choice = random.choice([a for a in range(self.num_tubes) if a!= t])
                        current_lights[pillar_choice][tube_choice] = 40
                        tube_choice = random.choice([a for a in range(self.num_tubes) if a!= t and a!=tube_choice])
                        current_lights[pillar_choice][tube_choice] = 40
                    return current_lights
            return []
        else:
            self.delay = remaining_delay
            return []

class Forest_Agent_Blue_Green(Forest_Agent):
    def __init__(self, num_tubes,num_pillars,action_bias, delay_mu=5, delay_sigma=1):
        super().__init__(num_tubes,num_pillars)  # Call parent class

        self.delay = 0.0
        self.delay_mu = delay_mu
        self.delay_sigma = delay_sigma
        self.time_since_last_call=0
        self.trigger1=160 # blue
        self.trigger2= 90 #green
        self.action_bias = action_bias


    def call(self,current_lights:List[List[int]]):

        self.time_since_last_call+=1
        remaining_delay = self.delay - self.time_since_last_call



        if remaining_delay <= 0.0:

            # Reset Delay Press
            self.delay = random.gauss(self.delay_mu, self.delay_sigma)
            self.time_since_last_call=0

            # Start Press
            pillar_choice=random.choice(range(self.num_pillars))

            for t in(range(self.num_tubes)):
                rule1 = random.choices([1, 0], weights=self.action_bias)
                if(current_lights[pillar_choice][t] == self.trigger1 and rule1==1):
                        left_action = random.choice([1, 0])
                        if (left_action==1):
                            if (t + 1 == self.num_tubes):
                                current_lights[pillar_choice][0] = 40
                            else:
                                current_lights[pillar_choice][t + 1] = 40
                        else:
                            if (t - 1 == -1):
                                current_lights[pillar_choice][0] = 40
                            else:
                                current_lights[pillar_choice][t - 1] = 40
                        return current_lights
                elif (current_lights[pillar_choice][t] == self.trigger2 and rule1==0) :
                    left_action = random.choice([1, 0])
                    if (left_action==1):
                        if (t + 1 == self.num_tubes):
                            current_lights[pillar_choice][0] = 255
                        else:
                            current_lights[pillar_choice][t + 1] = 255
                    else:
                        if (t - 1 == -1):
                            current_lights[pillar_choice][0] = 255
                        else:
                            current_lights[pillar_choice][t - 1] = 255
                    return current_lights
            return []
        else:
            self.delay = remaining_delay
            return []
