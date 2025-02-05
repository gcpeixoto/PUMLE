import logging
import os
import subprocess
import time
from typing import Dict, List, Tuple

from src.pumle.ini import Ini
from src.pumle.mat_files import MatFiles
from src.pumle.parameters_variation import ParametersVariation
from src.pumle.sim_results_parser import SimResultsParser
from src.pumle.arrays import Arrays
from src.pumle.metadata import Metadata


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

    def set_metadata(self) -> None:
        self.meta = Metadata(os.path.join(self.root_path, self.data_lake["metadata"]))

    def set_simulation_script_path(self) -> None:
        self.simulation_script_path = os.path.join(
            self.root_path, "simulation_script.sh"
        )

    def set_data_lake_paths(self) -> None:
        if self.config.get("data_lake_paths"):
            self.data_lake = self.config.get("data_lake_paths")
        else:
            self.data_lake = {
                "metadata": "data_lake/metadata",
                "pre_bronze": "data_lake/pre_bronze",
                "bronze_data": "data_lake/bronze_data",
                "silver_data": "data_lake/silver_data",
                "golden_data": "data_lake/golden_data",
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

        all_parameters = parameters.generate_parameter_variations()

        if self.config.get("save_metadata"):
            self.meta.get_data(
                parameters=all_parameters, base_schema=self.params_schema
            )
            self.meta.save_bronze_data()

        for p in all_parameters:
            id_ = p["SimNums"]["sim_id"]
            matFiles = MatFiles(p)
            matFiles.write()
            self.logger.info(f"Mat file {id_} generated")

    def run_simulations(self) -> None:
        num_threads = str(self.config.get("num_threads"))
        if num_threads is None:
            subprocess.run(["sh", self.simulation_script_path])
        else:
            subprocess.run(["sh", self.simulation_script_path, num_threads])

    def post_process(self) -> None:
        parser = SimResultsParser(self.data_lake["bronze_data"])
        parser.save_all(self.data_lake["silver_data"])

        if self.config.get("save_metadata"):
            self.meta.get_data(dimensions=parser.dimensions)
            self.meta.save_silver_data()

    def save_data(self) -> None:
        data = Arrays(self.data_lake["silver_data"], self.data_lake["golden_data"])
        data.save_golden_data(saving_method=self.config.get("saving_method"))

        if self.config.get("save_metadata"):
            self.meta.get_data(timestamps=data.timestamps)
            self.meta.save_golden_data()

    def clean_older_files(self) -> None:
        self.logger.info("Pumle cleaning older files")
        for path in self.data_lake.values():
            if os.path.exists(path):
                subprocess.run(["rm", "-rf", path])

        self.logger.info("Pumle cleaned older files")

        self.logger.info("Pumle creating data lake directories")
        for path in self.data_lake.values():
            os.makedirs(path)

    def exclude_previous_layers(self, layer) -> None:
        if os.path.exists(self.data_lake[layer]):
            subprocess.run(["rm", "-rf", self.data_lake[layer]])

    def run(
        self,
        should_clean_older_files: bool = False,
        layers_to_keep: set = {
            "pre_bronze",
            "bronze_data",
            "silver_data",
            "golden_data",
        },
    ) -> None:
        start_time = time.time()
        self.logger.info("Pumle running")

        self.logger.info("Pumle setting up")
        self.set_params_schema()
        self.set_setup_ini()
        self.set_root_path()
        self.set_simulation_script_path()
        self.set_data_lake_paths()
        self.set_metadata()

        if should_clean_older_files:
            self.clean_older_files()

        self.logger.info("Pumle pre-processing")
        self.pre_process()

        self.logger.info("Pumle running simulations")
        self.run_simulations()

        if "pre_bronze" not in layers_to_keep:
            self.exclude_previous_layers("pre_bronze")
        if "metadata" not in layers_to_keep:
            self.exclude_previous_layers("metadata")

        self.logger.info("Pumle post-processing")
        self.post_process()

        if "bronze_data" not in layers_to_keep:
            self.exclude_previous_layers("bronze_data")

        self.logger.info("Pumle saving data")
        self.save_data()

        if "silver_data" not in layers_to_keep:
            self.exclude_previous_layers("silver_data")

        self.logger.info("Pumle Finished")
        print("--- %s seconds ---" % (time.time() - start_time))
        print("--- %s minutes ---" % ((time.time() - start_time) / 60))
