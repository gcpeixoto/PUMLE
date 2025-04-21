"""
PUMLE - Python-based Unified Machine Learning Environment
Core class for managing CO2 injection simulations.
"""

import logging
import os
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import numpy as np
import shutil

from src.pumle.ini import Ini
from src.pumle.mat_files import MatFiles
from src.pumle.parameters_variation import ParametersVariation
from src.pumle.sim_results_parser import SimResultsParser
from src.pumle.arrays import Arrays, ArrayConfig
from src.pumle.tabular import Tabular
from src.pumle.utils import generate_param_hash
from src.pumle.db import DBManager


class Pumle:
    """Main class for managing CO2 injection simulations."""
    
    # Default configuration values
    DEFAULT_PARAMETER_VARIATION = 0.2
    DEFAULT_NUM_THREADS = 4
    DEFAULT_SAVING_METHOD = "numpy"
    
    # Default parameter schema
    DEFAULT_PARAMS_SCHEMA = {
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
                "injection_rampup_dt_initial",
            ],
            True,
        ),
        "EXECUTION": (["octave", "mrst_root"], False),
        "SimNums": (["sim_id"], True),
    }
    
    # Default data lake paths
    DEFAULT_DATA_LAKE_PATHS = {
        "staging": "data_lake/staging",
        "bronze_data": "data_lake/bronze_data",
        "silver_data": "data_lake/silver_data",
        "golden_data": "data_lake/golden_data",
        "tabular_data": "data_lake/tabular_data",
    }

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize PUMLE with configuration.
        
        Args:
            config: Dictionary containing configuration parameters
        """
        self.config = config
        self.configs: Optional[List[Dict]] = None
        self._setup_logger()
        self.db = DBManager()
        self._setup_paths()
        self._validate_setup()
        self.logger.info("PUMLE initialized successfully")

    def _setup_logger(self) -> None:
        """Configure logging for the PUMLE instance."""
        self.logger = logging.getLogger("pumle")
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def _setup_paths(self) -> None:
        """Set up all required paths and configurations."""
        self.root_path = self.config.get(
            "root_path", 
            os.path.dirname(os.path.abspath(__file__))
        )
        self.setup_ini = self.config.get("setup_ini", "setup.ini")
        self.params_schema = self.config.get(
            "params_schema", 
            self.DEFAULT_PARAMS_SCHEMA
        )
        self.simulation_script_path = os.path.join(
            self.root_path, 
            "simulation_script.sh"
        )
        self.data_lake = self.config.get(
            "data_lake_paths", 
            self.DEFAULT_DATA_LAKE_PATHS
        )

    def _validate_setup(self) -> None:
        """Validate the setup configuration."""
        if not os.path.exists(self.setup_ini):
            raise FileNotFoundError(f"Setup file {self.setup_ini} not found")

        if not os.path.exists(self.simulation_script_path):
            raise FileNotFoundError(
                f"Simulation script {self.simulation_script_path} not found"
            )

    def _validate_external_dependencies(self, params: Dict) -> None:
        """Validate external dependencies in parameters.
        
        Args:
            params: Dictionary containing simulation parameters
            
        Raises:
            ValueError: If required external dependencies are missing
        """
        if not params.get("EXECUTION", {}).get("octave"):
            raise ValueError("Octave path not found in setup.ini")
        if not params.get("EXECUTION", {}).get("mrst_root"):
            raise ValueError("MRST root path not found in setup.ini")

    def pre_process(self) -> List[Dict]:
        """Prepare simulation parameters and generate necessary files.
        If variation_delta is 0, only the base parameters are used.
        
        Returns:
            List of dictionaries containing simulation configurations (usually one if delta is 0)
        """
        self.logger.info("Starting pre-processing...")
        ini_reader = Ini(
            self.root_path, 
            self.setup_ini, 
            self.params_schema
        )
        base_parameter = ini_reader.get_params()
        self.logger.debug("Base parameters loaded from INI.")

        self._validate_external_dependencies(base_parameter)

        # --- Conditional Parameter Variation --- 
        variation_delta = self.config.get("variation_delta", self.DEFAULT_PARAMETER_VARIATION)
        selected_parameters = self.config.get("selected_parameters")
        
        all_parameters = []
        if variation_delta == 0 or not selected_parameters:
            if variation_delta == 0:
                 self.logger.info("Variation delta is 0. Using only base parameters.")
            else:
                 self.logger.info("No parameters selected for variation. Using only base parameters.")
            # Assign a default sim_id if needed, or ensure it exists in base_parameter
            if "SimNums" not in base_parameter or "sim_id" not in base_parameter.get("SimNums", {}):
                 if "SimNums" not in base_parameter:
                     base_parameter["SimNums"] = {}
                 base_parameter["SimNums"]["sim_id"] = 1 # Assign default ID 1
                 self.logger.warning("Assigning default sim_id=1 to base parameters.")
            all_parameters = [base_parameter]
        else:
            self.logger.info(f"Generating parameter variations with delta={variation_delta} for parameters: {selected_parameters}")
            parameters_variation = ParametersVariation(
                base_parameters=base_parameter,
                selected_parameters=selected_parameters,
                variation_delta=variation_delta,
            )
            all_parameters = parameters_variation.generate_variations()
            self.logger.info(f"Generated {len(all_parameters)} parameter sets.")
        # --- End Conditional Variation ---

        if not all_parameters:
            self.logger.error("No parameter configurations were generated. Aborting pre-process.")
            raise ValueError("Parameter generation resulted in an empty list.")

        generated_configs = []
        for params in all_parameters:
            # Generate simulation hash and staging folder from Fluid parameters
            fluid_params = params.get("Fluid", {})
            if not fluid_params:
                 self.logger.warning("Fluid parameters missing in a configuration set. Skipping hash generation.")
                 continue # Or handle error appropriately
                 
            sim_hash = generate_param_hash(fluid_params)
            
            # Ensure SimNums exists before accessing/setting
            if "SimNums" not in params:
                params["SimNums"] = {}
                
            params["SimNums"]["sim_hash"] = sim_hash
            params["SimNums"]["staging_folder"] = f"staging_{sim_hash}"
            sim_id = params["SimNums"].get("sim_id", "N/A") # Use get for safety

            # Insert into database (handle potential errors)
            try:
                self.db.insert_simulation(sim_hash, sim_id, str(fluid_params))
            except Exception as db_err:
                 self.logger.error(f"Failed to insert simulation {sim_hash} into DB: {db_err}. Skipping this configuration.")
                 continue # Skip if DB insert fails

            # Generate .mat files (handle potential errors)
            try:
                mat_files = MatFiles(params)
                mat_files.write()
                self.logger.info(f"Generated .mat files for simulation {sim_hash} (ID: {sim_id})")
                generated_configs.append(params) # Add only if successful
            except Exception as mat_err:
                self.logger.error(f"Failed to generate .mat files for {sim_hash}: {mat_err}. Skipping this configuration.")
                # Optionally update DB status to FAILED here
                try:
                    self.db.update_sim_status(sim_hash, SimulationStatus.FAILED)
                except Exception as db_update_err:
                    self.logger.error(f"Failed to update status to FAILED for {sim_hash} after .mat error: {db_update_err}")

        self.configs = generated_configs # Store only successfully pre-processed configs
        if not self.configs:
             self.logger.error("Pre-processing completed, but no configurations were successfully processed.")
             # Depending on desired behavior, maybe raise an error here
        else:
             self.logger.info(f"Pre-processing completed successfully for {len(self.configs)} configurations.")
             
        return self.configs

    def run_simulations(self) -> None:
        """Execute the simulation process."""
        if not self.configs:
            raise ValueError("No simulation configurations found. Run pre_process first.")

        # Update database status
        for params in self.configs:
            sim_hash = params["SimNums"]["sim_hash"]
            self.db.update_sim_status(sim_hash, "RUNNING")

        # Execute simulation script
        num_threads = str(self.config.get("num_threads", self.DEFAULT_NUM_THREADS))
        result = subprocess.run(
            ["sh", "simulation_script.sh", num_threads],
            check=True
        )

        # Update database status
        for params in self.configs:
            sim_hash = params["SimNums"]["sim_hash"]
            self.db.update_sim_status(sim_hash, "COMPLETED")

    def post_process(self, sim_hash: str) -> List[Dict]:
        """Process simulation results.
        
        Args:
            sim_hash: Unique identifier for the simulation
            
        Returns:
            List of dictionaries containing processed results
        """
        parser = SimResultsParser(
            self.data_lake["bronze_data"], 
            sim_hash=sim_hash
        )
        return parser.get_all()

    def save_data(self, sim_hash: str, result: List[Dict]) -> None:
        """Save simulation results.
        
        Args:
            sim_hash: Unique identifier for the simulation
            result: List of dictionaries containing results to save
            
        Raises:
            ValueError: If result is empty or invalid
            TypeError: If result contains invalid data types
        """
        if not result:
            raise ValueError("Result list cannot be empty")
            
        try:
            # Convert result to proper format if needed
            processed_result = []
            for state in result:
                if not isinstance(state, dict):
                    raise TypeError(f"Expected dict, got {type(state)}")
                    
                processed_state = {}
                for key, value in state.items():
                    if isinstance(value, (list, np.ndarray)):
                        # Convert lists and numpy arrays to proper format
                        processed_state[key] = np.array(value).tolist()
                    else:
                        processed_state[key] = value
                        
                processed_result.append(processed_state)
            
            # Initialize Arrays object
            arrays_obj = Arrays(self.data_lake["golden_data"])
            
            # Create ArrayConfig instance from main config
            array_config = ArrayConfig(
                saving_method=self.config.get("saving_method", self.DEFAULT_SAVING_METHOD),
                upload_to_s3=self.config.get("upload_to_s3", False),
                s3_config=self.config.get("s3_config") if self.config.get("upload_to_s3") else None
            )

            # Save the processed data using the ArrayConfig instance
            arrays_obj.save_golden_data(
                sim_id=sim_hash,
                result=processed_result,
                config=array_config, # Pass the correctly typed config object
            )
            
            self.logger.info(f"Successfully saved data for simulation {sim_hash}")
            
        except Exception as e:
            self.logger.error(f"Failed to save data for simulation {sim_hash}: {e}")
            raise

    def clean_older_files(self) -> None:
        """Clean up old simulation files and staging folders."""
        self.logger.info("Cleaning up old files...")

        # Clean files within all specified data lake paths (excluding staging for folders)
        for layer, path_str in self.data_lake.items():
            if layer == "staging": # Skip staging folders in this specific file loop
                continue
            path = Path(path_str)
            if path.exists() and path.is_dir():
                self.logger.debug(f"Cleaning files in non-staging layer: {path}")
                for item in path.iterdir():
                    try:
                        if item.is_file():
                            item.unlink() # Remove file
                            self.logger.debug(f"Removed file: {item}")
                        # Optionally, you could add logic here to remove empty dirs in non-staging layers
                    except Exception as e:
                        self.logger.warning(f"Could not remove item {item} in {layer}: {e}")

        # Specifically clean everything (files and folders) within the staging directory
        staging_path_str = self.data_lake.get("staging")
        if staging_path_str:
            staging_path = Path(staging_path_str)
            if staging_path.exists() and staging_path.is_dir():
                self.logger.info(f"Cleaning all contents of staging directory: {staging_path}")
                for item in staging_path.iterdir(): # Iterate through items directly in staging
                    try:
                        if item.is_dir():
                            shutil.rmtree(item) # Recursively remove directory and contents
                            self.logger.info(f"Removed staging directory: {item}")
                        elif item.is_file():
                            item.unlink() # Remove file
                            self.logger.debug(f"Removed staging file: {item}")
                    except Exception as e:
                        self.logger.error(f"Failed to remove staging item {item}: {e}")

        self.logger.info("Cleanup completed.")

    def create_data_lake(self) -> None:
        """Create data lake directory structure."""
        self.logger.info("Creating data lake directories")
        for path in self.data_lake.values():
            Path(path).mkdir(parents=True, exist_ok=True)

    def exclude_previous_layers(self, layer: str) -> None:
        """Remove previous data from specified layer.
        
        Args:
            layer: Name of the data lake layer to clean
        """
        if os.path.exists(self.data_lake[layer]):
            subprocess.run(["rm", "-rf", self.data_lake[layer]])

    def save_tabular_data(self) -> None:
        """Save simulation results in tabular format."""
        tab = Tabular(
            self.data_lake["golden_data"],
            self.data_lake["tabular_data"],
            self.config.get("saving_method", self.DEFAULT_SAVING_METHOD),
        )
        tab.read_data()
        tab.structute_data()
        tab.save_data()
