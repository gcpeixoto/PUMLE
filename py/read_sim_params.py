import configparser
import os
import logging

from typing import Dict


class ReadSimulationParams:
    def __init__(self, config_file: str = '../setup.ini'):
        self.config_file = config_file
        self.logger = self._setup_logger()
        self._validate_config_file()

    def _setup_logger(self) -> logging.Logger:
        """Set up a logger for the class."""
        logger = logging.getLogger("SimulationParamsLogger")
        logger.setLevel(logging.DEBUG)

        # File handler
        log_file = os.path.join(os.getcwd(), 'simulation_params.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add handler to logger
        if not logger.hasHandlers():
            logger.addHandler(file_handler)

        return logger

    def _validate_config_file(self) -> None:
        """Validate if the configuration file exists."""
        if not os.path.isfile(self.config_file):
            self.logger.error(f"Configuration file '{self.config_file}' not found.")
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found.")


    def get_params(self) -> Dict:
        """
        Get simulation parameters from the configuration setup file.

        Returns
        -------
        dict:
            Dictionary of parameters.
        """
        config = configparser.ConfigParser()
        config.read(self.config_file)

        sections = ['Paths', 'Pre-Processing', 'Grid', 'Fluid', 'Initial Conditions',
                    'Boundary Conditions', 'Wells', 'Schedule', 'MATLAB']

        PARAMS = {}

        # Define parameter lists and whether they should be cast to float
        param_definitions = {
            'Paths': (['PUMLE_ROOT', 'PUMLE_RESULTS'], False),
            'Pre-Processing': (['case_name', 'file_basename', 'model_name'], False),
            'Grid': (['file_path', 'repair_flag'], False),
            'Fluid': (['pres_ref', 'temp_ref', 'cp_rock', 'srw', 'src', 'pe', 'XNaCl', 'rho_h2o'], True),
            'Initial Conditions': (['sw_0'], True),
            'Boundary Conditions': (['type'], False),
            'Wells': (['CO2_inj'], False),
            'Schedule': (['injection_time', 'migration_time', 'injection_timestep_rampup', 'migration_timestep'], True),
            'MATLAB': (['matlab', 'mrst_root'], False),
        }

        for section, (params, cast_to_float) in param_definitions.items():
            if not config.has_section(section):
                self.logger.warning(f"Missing section: {section}")
                PARAMS[section] = {}
                continue

            section_params = {}
            for param in params:
                try:
                    value = config.get(section, param)
                    if cast_to_float:
                        value = float(value)
                    section_params[param] = value
                except (configparser.NoOptionError, ValueError) as e:
                    self.logger.error(f"Error reading parameter '{param}' from section '{section}': {e}")
            PARAMS[section] = section_params

        self.logger.info("Simulation parameters successfully read.")
        return PARAMS

    def read_sim_params(self) -> Dict:
        """
        Read simulation parameters from the configuration file.

        Returns
        -------
        dict:
            Dictionary of simulation parameters.
        """
        self.logger.info("Reading simulation parameters from configuration file.")
        return self.get_params()
