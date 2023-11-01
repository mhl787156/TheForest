from Forest_Swarm import *
if __name__ == '__main__':
    S1 = Forest_Swarm(6, 6, 2)
    S1.agents.append(Forest_Agent_Red(6, 2, [0.3, 0.7], 5, 0.5))
    S1.agents.append(Forest_Agent_Blue_Green(6, 2, [0.3, 0.7], 5, 0.5))
    S1.agents.append(Forest_Agent_Yellow(6, 2, [0.3, 0.7], 5, 0.5))
    S1.agents.append(Forest_Agent_Red(6, 2, [0.3, 0.7], 5, 0.5))
    S1.agents.append(Forest_Agent_Blue_Green(6, 2, [0.3, 0.7], 5, 0.5))
    S1.agents.append(Forest_Agent_Yellow(6, 2, [0.3, 0.7], 5, 0.5))
    # S1.agents.append(Forest_Agent_Random(6, 2, 5, 0.5))
    S1.simulate(50)
    S1.save_data()
    S1.animation()



