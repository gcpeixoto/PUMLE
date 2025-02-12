# src/pumle/pumle.py
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
from src.pumle.tabular import Tabular


class Pumle:
    def __init__(self, config: Dict) -> None:
        self.config = config
        self.logger = logging.getLogger("pumle")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())
        self.setup()
        self.logger.info("Pumle initialized")

    def checks(self) -> None:
        if not os.path.exists(self.setup_ini):
            raise FileNotFoundError(f"Setup file {self.setup_ini} not found")

        if not os.path.exists(self.simulation_script_path):
            raise FileNotFoundError(
                f"Simulation script {self.simulation_script_path} not found"
            )

    def checks_external(self, params) -> None:
        if params.get("EXECUTION").get("octave") is None:
            raise ValueError("Octave path not found in setup.ini")

        if params.get("EXECUTION").get("mrst_root") is None:
            raise ValueError("MRST root path not found in setup.ini")

    def set_root_path(self) -> None:
        self.root_path = self.config.get(
            "root_path", os.path.dirname(os.path.abspath(__file__))
        )

    def set_setup_ini(self) -> None:
        self.setup_ini = self.config.get("setup_ini", "setup.ini")

    def set_params_schema(self) -> None:
        self.params_schema = self.config.get(
            "parms_schema",
            {
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
            },
        )

    def set_metadata(self) -> None:
        mpath = os.path.join(self.root_path, "data_lake/metadata")
        self.meta = Metadata(mpath)

    def set_simulation_script_path(self) -> None:
        self.simulation_script_path = os.path.join(
            self.root_path, "simulation_script.sh"
        )

    def set_data_lake_paths(self) -> None:
        self.data_lake = self.config.get(
            "data_lake_paths",
            {
                "metadata": "data_lake/metadata",
                "pre_bronze": "data_lake/pre_bronze",
                "bronze_data": "data_lake/bronze_data",
                "silver_data": "data_lake/silver_data",
                "golden_data": "data_lake/golden_data",
                "tabular_data": "data_lake/tabular_data",
            },
        )

    def setup(self) -> None:
        self.logger.info("Pumle setting up")
        self.set_params_schema()
        self.set_setup_ini()
        self.set_root_path()
        self.set_simulation_script_path()
        self.set_data_lake_paths()
        self.set_metadata()

    def pre_process(self) -> List[dict]:
        base_parameter = Ini(
            self.root_path, self.setup_ini, self.params_schema
        ).get_params()

        self.checks_external(base_parameter)

        parameters_variation = ParametersVariation(
            base_parameters=base_parameter,
            selected_parameters=self.config.get("selected_parameters"),
            variation_delta=self.config.get("variation_delta"),
            cache_file=self.config.get("parameters_variation_cache"),
        )
        all_parameters = parameters_variation.generate_parameter_variations()
        if self.config.get("save_metadata"):
            self.meta.get_data(
                parameters=all_parameters, base_schema=self.params_schema
            )
            self.meta.save_bronze_data()

        for p in all_parameters:
            sim_id = p["SimNums"]["sim_id"]
            mat_files = MatFiles(p)
            mat_files.write()
            self.logger.info(f"Mat file {sim_id} generated")
        if not os.path.exists(self.data_lake["bronze_data"]):
            os.makedirs(self.data_lake["bronze_data"])
        self.configs = all_parameters
        return all_parameters

    def run_simulations(self) -> None:
        num_threads = str(self.config.get("num_threads"))
        if num_threads is None:
            result = subprocess.run(["sh", self.simulation_script_path])
        else:
            result = subprocess.run(["sh", self.simulation_script_path, num_threads])
            
        if result.returncode != 0:
            self.logger.error("Simulation failed")
            raise RuntimeError("Simulation failed")

    def post_process(self) -> None:
        parser = SimResultsParser(self.data_lake["bronze_data"])
        parser.save_all(self.data_lake["silver_data"])
        if self.config.get("save_metadata"):
            self.meta.get_data(dimensions=parser.get_dimensions())
            self.meta.save_silver_data()

    def save_data(self) -> None:
        arrays_obj = Arrays(
            self.data_lake["silver_data"], self.data_lake["golden_data"]
        )
        s3_config = self.config.get("s3_config")
        if self.config.get("saving_method"):
            arrays_obj.save_golden_data(
                saving_method=self.config.get("saving_method"),
                upload_to_s3=self.config.get("upload_to_s3", False),
                s3_config=s3_config,
            )
        else:
            arrays_obj.save_golden_data(
                upload_to_s3=self.config.get("upload_to_s3", False), s3_config=s3_config
            )
        if self.config.get("save_metadata"):
            self.meta.get_data(timestamps=arrays_obj.timestamps)
            self.meta.save_golden_data()

    def clean_older_files(self) -> None:
        self.logger.info("Pumle cleaning older files")
        for path in self.data_lake.values():
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        os.remove(os.path.join(root, file))
        self.logger.info("Pumle cleaned older files")

    def create_data_lake(self) -> None:
        self.logger.info("Pumle creating data lake directories")
        for path in self.data_lake.values():
            if not os.path.exists(path):
                os.makedirs(path)

    def exclude_previous_layers(self, layer) -> None:
        if os.path.exists(self.data_lake[layer]):
            subprocess.run(["rm", "-rf", self.data_lake[layer]])

    def save_tabular_data(self) -> None:
        tab = Tabular(
            self.data_lake["golden_data"],
            self.data_lake["tabular_data"],
            self.config.get("saving_method"),
        )
        tab.read_data()
        tab.structute_data()
        tab.save_data()

    def run(
        self,
        should_clean_older_files: bool = False,
        layers_to_keep: set = {
            "pre_bronze",
            "bronze_data",
            "silver_data",
            "golden_data",
            "tabular_data",
        },
    ) -> None:
        start_time = time.time()
        self.logger.info("Pumle running")
        self.setup()

        if should_clean_older_files:
            self.clean_older_files()
            self.create_data_lake()
    
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
        
        self.logger.info("Pumle saving tabular data")
        self.save_tabular_data()
        
        self.logger.info("Pumle Finished")
        elapsed = time.time() - start_time
        print(f"--- {elapsed:.2f} seconds ---")
        print(f"--- {elapsed/60:.2f} minutes ---")
