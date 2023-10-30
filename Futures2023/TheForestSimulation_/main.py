from Forest_Swarm import *
if __name__ == '__main__':
    S1 = Forest_Swarm(3, 7, 2)
    S1.agents.append(Forest_Agent_Red(7, 2,[1,0],5, 0.5)) # change rules bias, [1,0] means agent will always run the first rule.
    S1.agents.append(Forest_Agent_Blue_Green(7, 2,[1,0], 5, 0.5))
    S1.agents.append(Forest_Agent_Yellow(7, 2,[1,0], 5, 0.5))
    #S1.agents.append(Forest_Agent_Random(7, 2, 5, 0.5)
    S1.simulate(50)
    S1.generate_coords_tubes(3)
    S1.save_data()
    S1.animation()
    


