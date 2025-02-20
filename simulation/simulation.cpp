#include <algorithm>
#include <iostream>
#include <vector>
#include <string>
#include <filesystem>
#include <omp.h>
#include <cstdlib>
#include <unistd.h>

namespace fs = std::filesystem;

// Function to run a single Octave simulation with given parameters
int run_simulation(const std::string& folder, int sim_id) {
    std::vector<std::string> param_files = {
        "Paths", "PreProcessing", "Grid", "Fluid", 
        "InitialConditions", "BoundaryConditions", "Wells", 
        "Schedule", "EXECUTION", "SimNums"
    };
    
    std::string command = "octave --eval \"co2lab3DPUMLE(";
    for (const auto& param : param_files) {
        std::string file_path = folder + "/" + param + "ParamsPUMLE_" + std::to_string(sim_id) + ".mat";
        if (!fs::exists(file_path)) {
            std::cerr << "Missing required file: " << file_path << "\n";
           return 1;
        }
        command += "'" + file_path + "', ";
    }
    command.pop_back(); command.pop_back(); // Remove last comma and space
    command += ")\"";
    std::cout << "Running simulation " << sim_id << " with parameters in " << folder << std::endl;
    int status = std::system(command.c_str());
    if (status != 0) {
        std::cerr << "Simulation " << sim_id << " failed with status: " << status << std::endl;
        return 1;
    }
    return 0;
}
    

int main() {
    std::string current_path = fs::current_path().string();

    std::string data_lake_path = "/data_lake/staging/";
    std::string output_data_lake_path = "/data_lake/silver_data/";
    
    std::string directory = current_path + data_lake_path;
    std::string output_directory = current_path + output_data_lake_path;


    std::vector<std::string> folders;
    for (const auto& entry : fs::directory_iterator(directory)) {
        if (entry.is_directory() && entry.path().string().find("staging_") != std::string::npos) {
            folders.push_back(entry.path().string());
        }
    }
    
    if (!fs::exists(output_directory)) {
        fs::create_directory(output_directory);
    }
    std::vector<std::string> output_folders;
    for (const auto& entry : fs::directory_iterator(output_directory)) {
        output_folders.push_back(entry.path().string());
    }

    int num_simulations = folders.size();
    // Workaround to skip already run simulations
    int num_simulations_already_run = output_folders.size();
    
    std::cout << "Found " << num_simulations_already_run << " simulations already run." << std::endl;
    std::sort(folders.begin(), folders.end(), [](const std::string& a, const std::string& b) {
        return std::stoi(a.substr(a.find_last_of("_") + 1)) < std::stoi(b.substr(b.find_last_of("_") + 1));
    });
    
    if (num_simulations == 0) {
        std::cerr << "No simulation folders found in " << directory << std::endl;
        return 1;
    }

    std::cout << "Found " << num_simulations << " simulation folders." << std::endl; 

    chdir("./simulation/");

    // TODO: Find the error here

    int global_status = 0;
    int number_of_simulations_to_run = num_simulations + num_simulations_already_run;
    #pragma omp parallel for schedule(dynamic) shared(global_status)
    for (int i = num_simulations_already_run; i < number_of_simulations_to_run; ++i) {
        int status = run_simulation(folders[i], i + 1);

        if (status != 0) {
            std::cerr << "Simulation " << i + 1 << " failed." << std::endl;
            #pragma omp critical
            {
                global_status = status;
            }
        }
    }

    if (global_status != 0) {
        return global_status;
    }

    chdir("../");

    std::cout << "All simulations completed." << std::endl;
    return 0;
}
