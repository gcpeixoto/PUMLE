import logging
import os
import json
import subprocess
import time
from typing import Dict, List, Tuple

from src.pumle.ini import Ini
from src.pumle.mat_files import MatFiles
from src.pumle.parameters_variation import ParametersVariation
from src.pumle.sim_results_parser import SimResultsParser
from src.pumle.arrays import Arrays
from src.pumle.tabular import Tabular
from src.pumle.utils import generate_param_hash
from src.pumle.db import DBManager


class Pumle:
    def __init__(self, config: Dict) -> None:
        self.config = config
        self.configs = None
        self.logger = logging.getLogger("pumle")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.StreamHandler())
        self.db = DBManager()
        self.default_parameter_variation = 0.2
        self.setup()
        self.checks()
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
            "params_schema",
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

    def set_simulation_script_path(self) -> None:
        self.simulation_script_path = os.path.join(
            self.root_path, "simulation_script.sh"
        )

    def set_data_lake_paths(self) -> None:
        self.data_lake = self.config.get(
            "data_lake_paths",
            {
                "staging": "data_lake/staging",
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
        self.logger.info("Pumle set up")

    def pre_process(self) -> List[dict]:
        base_parameter = Ini(
            self.root_path, self.setup_ini, self.params_schema
        ).get_params()

        self.checks_external(base_parameter)

        parameters_variation = ParametersVariation(
            base_parameters=base_parameter,
            selected_parameters=self.config.get("selected_parameters"),
            variation_delta=self.config.get(
                "variation_delta", self.default_parameter_variation
            ),
        )
        all_parameters = parameters_variation.generate_parameter_variations()

        for p in all_parameters:
            # Gerar sim_hash e staging_folder
            fluid_params = p.get("Fluid", {})
            sim_hash = generate_param_hash(fluid_params)
            p["SimNums"]["sim_hash"] = sim_hash
            p["SimNums"]["staging_folder"] = f"staging_{sim_hash}"

            # Se você ainda usa sim_id, tudo bem, mas não será pro naming:
            sim_id = p["SimNums"]["sim_id"]

            # Insere no DB se quiser
            self.db.insert_simulation(sim_hash, sim_id, str(fluid_params))

            # Gera .mat
            mat_files = MatFiles(p)
            mat_files.write()
            self.logger.info(f"[pre_process] .mat files created for hash={sim_hash}")

        self.configs = all_parameters
        return all_parameters

    def run_simulations(self) -> None:
        # Marca no DB como RUNNING
        for p in self.configs:
            sim_hash = p["SimNums"]["sim_hash"]
            self.db.update_sim_status(sim_hash, "RUNNING")

        # Chama o script (que por sua vez chama simulation.cpp).
        num_threads = str(self.config.get("num_threads", 4))
        result = subprocess.run(["sh", "simulation_script.sh", num_threads])
        if result.returncode != 0:
            raise RuntimeError("Simulation script failed")

        # Se chegou aqui, subimos no DB para COMPLETED
        for p in self.configs:
            sim_hash = p["SimNums"]["sim_hash"]
            self.db.update_sim_status(sim_hash, "COMPLETED")

    def post_process(self, sim_hash) -> List[dict]:
        parser = SimResultsParser(self.data_lake["bronze_data"], sim_hash=sim_hash)
        result = parser.get_all()
        return result

    def save_data(self, sim_hash: str, result) -> None:
        arrays_obj = Arrays(self.data_lake["golden_data"])
        s3_config = self.config.get("s3_config")
        method = self.config.get("saving_method", "numpy")
        arrays_obj.save_golden_data(
            sim_id=sim_hash,
            result=result,
            saving_method=method,
            upload_to_s3=self.config.get("upload_to_s3", False),
            s3_config=s3_config,
        )

    def clean_older_files(self) -> None:
        self.logger.info("Pumle cleaning older files")
        for path in self.data_lake.values():
            if os.path.exists(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        os.remove(os.path.join(root, file))

        if os.path.exists(self.data_lake["staging"]):
            for root, dirs, files in os.walk(path):
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))

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
