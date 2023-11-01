from Forest_Swarm import *

# First experiment - Random agents 
def first_experiment():
    # Random agent implementation
    ## Agents do not follow any rule- they randomly select tubes and colors
    # Create environment
    S1 = Forest_Swarm(3, 7, 2)
    # Add random agents
    S1.agents.append(Forest_Agent_Random(7, 2,5, 0.5)) #(num_tubes,num_pillars, delay_mu=5, delay_sigma=1)
    S1.agents.append(Forest_Agent_Random(7, 2, 5, 0.5))
    S1.agents.append(Forest_Agent_Random(7, 2, 5, 0.5))
    #
    # Start the simulation
    S1.simulate(50)
    S1.generate_coords_tubes(3)
    # Save data in a csv file
    S1.save_data()
    # Show animation
    S1.animation()

# Second experiment - First rule bias agents 
def second_experiment():
    # Create environment
    S1 = Forest_Swarm(3, 7, 2)
    # Add agents
    S1.agents.append(Forest_Agent_Red(7, 2,[1,0],5, 0.5)) # (self, num_tubes,num_pillars,action_bias, delay_mu=5, delay_sigma=1)
    S1.agents.append(Forest_Agent_Blue_Green(7, 2,[1,0], 5, 0.5))
    S1.agents.append(Forest_Agent_Yellow(7, 2,[1,0], 5, 0.5))
    #
    # Start the simulation
    S1.simulate(50)
    S1.generate_coords_tubes(3)
    # Save data in a csv file
    S1.save_data()
    # Show animation
    S1.animation()

# Third experiment - Agents select rules with equal probability
def third_experiment():
    # Create environment
    S1 = Forest_Swarm(3, 7, 2)
    # Add agents
    S1.agents.append(Forest_Agent_Red(7, 2,[.5,.5],5, 0.5)) # (self, num_tubes,num_pillars,action_bias, delay_mu=5, delay_sigma=1)
    S1.agents.append(Forest_Agent_Blue_Green(7, 2,[.5,.5], 5, 0.5))
    S1.agents.append(Forest_Agent_Yellow(7, 2,[.5,.5], 5, 0.5))
    #
    # Start the simulation
    S1.simulate(50)
    S1.generate_coords_tubes(3)
    # Save data in a csv file
    S1.save_data()
    # Show animation
    S1.animation()
    



if __name__ == '__main__':
    # Run the experiments
    first_experiment()
    second_experiment()
    third_experiment()
    
    """
    S1 = Forest_Swarm(3, 7, 2)
    S1.agents.append(Forest_Agent_Red(7, 2,[1,0],5, 0.5)) # change rules bias, [1,0] means agent will always run the first rule.
    S1.agents.append(Forest_Agent_Blue_Green(7, 2,[1,0], 5, 0.5)) # (self, num_tubes,num_pillars,action_bias, delay_mu=5, delay_sigma=1)
    S1.agents.append(Forest_Agent_Yellow(7, 2,[1,0], 5, 0.5))
    #S1.agents.append(Forest_Agent_Random(7, 2, 5, 0.5)
    S1.simulate(50)
    S1.generate_coords_tubes(3)
    S1.save_data()
    S1.animation()
    """




