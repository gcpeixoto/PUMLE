from generate_dataset import GenerateDataset
from read_sim_params import ReadSimulationParams
from simulation_dataset import SimulationDataset


NUM_SIMULATIONS = 1

if __name__ == "__main__":
    # Read simulation parameters from the setup.ini file
    params = ReadSimulationParams("setup.ini").get_params()

    # Generate the dataset
    gen_dataset = GenerateDataset(params)

    # Run multiple simulations
    gen_dataset.run_multiple_simulations(NUM_SIMULATIONS)

    # Instance of the simulation dataset
    # sim_data = SimulationDataset(params['Paths']['PUMLE_RESULTS'])
    
    # Read the simulation data files
    # data_numpy = sim_data.read_files()
    
    # Save the simulation data as a numpy file
    # sim_data.save_as_numpy(data_numpy, "simulation_data.npy")
 
    # print("Simulation dataset saved as 'simulation_data.npy'.")

    # Read the simulation data from the numpy file
    #returned_numpy = sim_data.read_numpy("simulation_data.npy")

    # print("Simulation dataset read from 'simulation_data.npy'.")
