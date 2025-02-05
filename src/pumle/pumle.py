import logging
import os
import subprocess
import time
from typing import Dict, List, Tuple

from src.pumle.ini import Ini
from src.pumle.mat_files import MatFiles
from src.pumle.parameters_variation import ParametersVariation
from src.pumle.sim_results_parser import SimResultsParser
from src.pumle.dataset import Dataset


class Pumle:
    def __init__(self, config: Dict) -> None:
        self.config = config
        self.logger = logging.getLogger("pumle")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())
        self.logger.info("Pumle initialized")

    def set_root_path(self) -> None:
        if self.config.get("root_path"):
            self.root_path = self.config.get("root_path")
        else:
            self.root_path = os.path.dirname(os.path.abspath(__file__))

    def set_setup_ini(self) -> None:
        if self.config.get("setup_ini"):
            self.setup_ini = self.config.get("setup_ini")
        else:
            self.setup_ini = "setup.ini"

    def set_params_schema(self) -> None:
        if self.config.get("parms_schema"):
            self.params_schema = self.config.get("parms_schema")
        else:
            self.params_schema: Dict[str, Tuple[List[str], bool]] = {
                "Paths": (["PUMLE_ROOT", "PUMLE_RESULTS"], False),
                "Pre-Processing": (["case_name", "file_basename", "model_name"], False),
                "Grid": (["file_path", "repair_flag"], False),
                "Fluid": (
                    [
                        "pres_ref",
                        "temp_ref",
                        "cp_rock",
                        "srw",
                        "src",
                        "pe",
                        "XNaCl",
                        "rho_h2o",
                    ],
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

    def pre_process(self) -> None:
        base_parameter = Ini(
            self.root_path, self.setup_ini, self.params_schema
        ).get_params()

        parameters = ParametersVariation(
            base_parameters=base_parameter,
            selected_parameters=self.config.get("selected_parameters"),
            variation_delta=self.config.get("variation_delta"),
        )

        for p in parameters.generate_parameter_variations():
            id_ = p["SimNums"]["sim_id"]
            matFiles = MatFiles(p)
            matFiles.write()
            self.logger.info(f"Mat file {id_} generated")

    def set_simulation_script_path(self) -> None:
        self.simulation_script_path = os.path.join(
            self.root_path, "simulation_script.sh"
        )

    def run_simulations(self) -> None:
        subprocess.run(["sh", self.simulation_script_path])

    def set_data_lake_paths(self) -> None:
        if self.config.get("data_lake_paths"):
            self.data_lake = self.config.get("data_lake_paths")
        else:
            self.data_lake = {
                "mat_files": "data_lake/mat_files",
                "sim_results": "data_lake/sim_results",
                "json_results": "data_lake/json_results",
                "consolidated_data": "data_lake/consolidated_data",
            }

    def post_process(self) -> None:
        parser = SimResultsParser(self.data_lake["sim_results"])
        parser.save_all(self.data_lake["json_results"])

    def save_data(self) -> None:
        data = Dataset(
            self.data_lake["json_results"], self.data_lake["consolidated_data"]
        )
        data.save_consolidated_data(saving_method=self.config.get("saving_method"))

    def run(self, clean_older_files: bool = False) -> None:
        start_time = time.time()
        self.logger.info("Pumle running")

        self.logger.info("Pumle setting up")
        self.set_params_schema()
        self.set_setup_ini()
        self.set_root_path()
        self.set_simulation_script_path()
        self.set_data_lake_paths()

        if clean_older_files:
            self.logger.info("Pumle cleaning older files")
            for path in self.data_lake.values():
                if os.path.exists(path):
                    subprocess.run(["rm", "-rf", path])

            self.logger.info("Pumle cleaned older files")

            self.logger.info("Pumle creating data lake directories")
            for path in self.data_lake.values():
                os.makedirs(path)

        self.logger.info("Pumle pre-processing")
        self.pre_process()

        self.logger.info("Pumle running simulations")
        self.run_simulations()

        self.logger.info("Pumle post-processing")
        self.post_process()

        self.logger.info("Pumle saving data")
        self.save_data()

        self.logger.info("Pumle Finished")
        print("--- %s seconds ---" % (time.time() - start_time))
        print("--- %s minutes ---" % ((time.time() - start_time) / 60))
