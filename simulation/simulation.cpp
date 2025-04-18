#include <algorithm>
#include <iostream>
#include <vector>
#include <string>
#include <filesystem>
#include <omp.h>
#include <cstdlib>
#include <fstream>   // para criar completed.flag
#include <unistd.h>

namespace fs = std::filesystem;

int run_simulation(const std::string& folder) {
    // Verifica se existe um "completed.flag" indicando que a sim terminou
    std::string completion_flag = folder + "/completed.flag";
    if (fs::exists(completion_flag)) {
        std::cout << "[INFO] Skipping simulation in folder: " << folder 
                  << " (completed.flag found)\n";
        return 0; // pular
    }

    // Get current directory for script path
    std::string current_dir = fs::current_path().string();
    std::string script_path = current_dir + "/simulation/co2lab3DPUMLE.m";

    // Check if script exists
    if (!fs::exists(script_path)) {
        std::cerr << "[ERROR] Script file not found: " << script_path << "\n";
        return 1;
    }

    // Precisamos dos 10 .mat?
    // ex.: "Fluid_<hash>.mat", "Schedule_<hash>.mat" ...
    // Montamos o comando do Octave:
    std::vector<std::string> param_files = {
        "Paths_", "PreProcessing_", "Grid_", "Fluid_", 
        "InitialConditions_", "BoundaryConditions_", "Wells_", 
        "Schedule_", "EXECUTION_", "SimNums_"
    };

    // Descobrimos o hash a partir do nome da pasta (ex: "staging_abc12345")
    // Poderíamos extrair substring, mas não é estritamente necessário
    // Se preferir, parse a substring
    // auto baseName = fs::path(folder).filename().string(); // "staging_abc12345"
    // std::string hash = baseName.substr(8); // remove "staging_"

    // Constrói o comando Octave
    std::string command = "octave --eval \"addpath('" + current_dir + "/simulation'); ";
    command += "co2lab3DPUMLE(";
    
    for (const auto& prefix : param_files) {
        // ex: folder + "/Fluid_abc12345.mat"
        // Precisamos saber qual hash? Vamos supor que folder = ".../staging_abc12345"
        // e dentro temos "Fluid_abc12345.mat", etc.
        
        // Se preferir recuperar o hash, e concatenar prefix + hash
        // Mas aqui, param_files são base, então:
        // "Fluid_" + hash + ".mat"
        // Precisaríamos do hash; mas se for consistent, ok

        // Maneira simples: busque qualquer .mat que comece com prefix
        // ou podemos "adivinhar" o hash fazendo substring do folder
        auto baseName = fs::path(folder).filename().string(); 
        std::string hash = baseName.substr(8); 
        std::string file_path = folder + "/" + prefix + hash + ".mat";
        if (!fs::exists(file_path)) {
            std::cerr << "[ERROR] Missing required file: " << file_path << "\n";
            return 1;
        }
        command += "'" + file_path + "', ";
    }

    // remove ", "
    command.pop_back(); 
    command.pop_back();
    command += ")\"";

    std::cout << "[INFO] Running Octave simulation in: " << folder << std::endl;
    int status = std::system(command.c_str());
    if (status != 0) {
        std::cerr << "[ERROR] Simulation in " << folder << " failed with status: " << status << std::endl;
        return status;
    }

    // Cria o completed.flag
    std::ofstream cflag(completion_flag);
    cflag << "Simulation done\n";
    cflag.close();

    return 0;
}

int main(int argc, char* argv[]) {
    // Get current directory
    std::string current_path = fs::current_path().string();
    std::string data_lake_path = "data_lake/staging/";
    std::string directory = current_path + "/" + data_lake_path;

    // Create staging directory if it doesn't exist
    if (!fs::exists(directory)) {
        fs::create_directories(directory);
    }

    std::vector<std::string> folders;
    for (const auto& entry : fs::directory_iterator(directory)) {
        if (entry.is_directory()) {
            std::string dirname = entry.path().filename().string();
            if (dirname.rfind("staging_", 0) == 0) {
                folders.push_back(entry.path().string());
            }
        }
    }

    if (folders.empty()) {
        std::cerr << "No simulation folders found in " << directory << std::endl;
        return 1;
    }

    // Sort folders
    std::sort(folders.begin(), folders.end());

    int num_simulations = (int) folders.size();
    std::cout << "[INFO] Found " << num_simulations << " staging folders." << std::endl;

    // Get thread count from command line
    int threads = 4; 
    if (argc > 1) {
        threads = std::stoi(argv[1]);
    }
    omp_set_num_threads(threads);

    std::cout << "[INFO] Using " << threads << " threads.\n";

    int global_status = 0;

    #pragma omp parallel for schedule(dynamic) shared(global_status)
    for (int i = 0; i < num_simulations; ++i) {
        int status = run_simulation(folders[i]);
        if (status != 0) {
            #pragma omp critical
            {
                global_status = status;
            }
        }
    }

    if (global_status != 0) {
        std::cerr << "[ERROR] One or more simulations failed.\n";
        return global_status;
    }

    std::cout << "[INFO] All simulations completed." << std::endl;
    return 0;
}
