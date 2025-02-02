import os
from src.pumle.ini import Ini
from src.pumle.mat_files import MatFiles
from src.pumle.parameters_variation import ParametersVariation
from typing import Dict, List, Tuple


root_path = os.path.dirname(os.path.abspath(__file__))
setup_ini = "setup.ini"

# Define parameter lists and whether they should be cast to float
params_schema: Dict[str, Tuple[List[str], bool]] = {
    "Paths": (["PUMLE_ROOT", "PUMLE_RESULTS"], False),
    "Pre-Processing": (["case_name", "file_basename", "model_name"], False),
    "Grid": (["file_path", "repair_flag"], False),
    "Fluid": (
        ["pres_ref", "temp_ref", "cp_rock", "srw", "src", "pe", "XNaCl", "rho_h2o"],
        True,
    ),
    "Initial Conditions": (["sw_0"], True),
    "Boundary Conditions": (["type"], False),
    "Wells": (["CO2_inj"], True),
    "Schedule": (
        [
            "injection_time",
            "migration_time",
            "injection_timesteps",
            "migration_timesteps",
        ],
        True,
    ),
    "EXECUTION": (["octave", "mrst_root"], False),
    "SimNums": (["sim_id"], True),
}

base_parameter = Ini(root_path, setup_ini, params_schema).get_params()

print(base_parameter)

parameters = ParametersVariation(base_parameter, ["pres_ref"])
print(parameters.parameters_combinations)

for p in parameters.generate_parameter_variations():
    id_ = p["SimNums"]["sim_id"]
    matFiles = MatFiles(p)
    matFiles.write()
    print(f"Mat file {id_} generated")
