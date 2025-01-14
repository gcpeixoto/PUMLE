import platform
import os
import logging
import numpy as np
import subprocess

from datetime import datetime
from scipy.io import savemat
from typing import Dict


class GenerateDataset:
    def __init__(self, params: Dict) -> None:
        self.params = params
        self.logger = self._setup_logger()
        self._validate_params()

    def _setup_logger(self) -> logging.Logger:
        """Set up a logger to handle log messages."""
        logger = logging.getLogger("PUMLELogger")
        logger.setLevel(logging.DEBUG)

        # Create file handler
        log_file = os.path.join(self.params['Paths']['PUMLE_ROOT'], 'simulation.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create formatter and add it to the handler
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Add the handler to the logger
        if not logger.hasHandlers():
            logger.addHandler(file_handler)

        return logger

    def _validate_params(self) -> None:
        """Validate required parameters are present."""
        required_keys = ['Paths', 'MATLAB', 'Fluid', 'Pre-Processing']
        for key in required_keys:
            if key not in self.params:
                self.logger.error(f"Missing required parameter: {key}")
                raise ValueError(f"Missing required parameter: {key}")

    def _create_directory(self, path: str) -> None:
        """Create a directory if it does not exist."""
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            raise
    
    def _dict_to_ini(self, config_dict: Dict) -> str:
        """Helper function to convert a dict back to .ini format"""
        
        ini_str = ""
        for section, items in config_dict.items():
            ini_str += f"[{section}]\n"
            print(items)
            for key, value in items.items():
                ini_str += f"{key} = {value}\n"
            ini_str += "\n"
        return ini_str


    def _print_report(self, res_dir: str, msg: bool = True) -> None:
        """
        Print simulation setup report for log purposes.

        Parameters
        ---------
            res_dir: results output directory
            msg: log message
        """
        out = os.path.join(self.params['Paths']['PUMLE_ROOT'], res_dir or 'temp')
        self._create_directory(out)

        # Get date/time and system information
        system, hostname, release, *_ = platform.uname()
        date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Text elements to write
        report_lines = [
            ''.center(80, '-') + '\n',
            'PUMLE SIMULATION REPORT'.center(80, ' ') + '\n',
            ''.center(80, '-') + '\n',
            f'Date/Time: {date_time}\n',
            f'OS: {system}\n',
            f'Version: {release}\n',
            f'Hostname: {hostname}\n',
            ''.center(80, '-') + '\n',
            self._dict_to_ini(self.params)
        ]

        report_path = os.path.join(out, 'report.txt')
        try:
            with open(report_path, 'w') as report_file:
                report_file.writelines(report_lines)
            if msg:
                self.logger.info(f"Report file saved to '{report_path}'.")
        except Exception as e:
            self.logger.error(f"Failed to write report: {e}")

    def _export_to_matlab(self) -> None:
        """Export dict of simulation parameters to Matlab to be read individually."""
        mroot = os.path.join(self.params['Paths']['PUMLE_ROOT'], 'm')
        self._create_directory(mroot)

        for section, content in self.params.items():
            basename = f"{section.replace('-', '').replace(' ', '')}ParamsPUMLE"
            fname = os.path.join(mroot, f"{basename}.mat")
            try:
                savemat(fname, content, appendmat=True)
                self.logger.info(f"Matlab file '{basename}.mat' exported to '{mroot}'.")
            except Exception as e:
                self.logger.error(f"Failed to export Matlab file '{basename}.mat': {e}")
    
    def _run_matlab_batch(self) -> None:
        """Run Matlab in batch mode."""
        bin_path = self.params['MATLAB'].get('matlab')
        if not bin_path:
            self.logger.error("Path to Matlab binary is not defined.")
            raise ValueError("Path to Matlab binary is not defined.")

        mfile_dir = os.path.join(self.params['Paths']['PUMLE_ROOT'], 'm')

        # Change directory to Matlab folder
        os.chdir(mfile_dir)

        cmd = "-logfile co2lab3DPUMLE.log -nojvm -batch co2lab3DPUMLE"

        try:
            out = subprocess.run([bin_path] + cmd.split(), shell=False, check=True)
            self.logger.info(f"Matlab batch mode executed successfully with return code {out.returncode}.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error executing Matlab batch: {e}")
            raise
        finally:
            os.chdir(os.path.join(self.params['Paths']['PUMLE_ROOT'], "py"))

    def run_simulation(self) -> None:
        """
        Run the simulation pipeline.
        """
        try:
            self._export_to_matlab()
            self._run_matlab_batch()
            self._print_report(self.params['Paths']['PUMLE_RESULTS'], msg=True)
        except Exception as e:
            self.logger.error(f"Simulation pipeline failed: {e}")

    def run_multiple_simulations(self, n: int) -> None:
        """
        Run multiple simulations.

        Parameters
        ----------
            n: int - number of simulations to run
        """
        self.logger.info(f"Starting {n**3} simulations.")
        param_range = np.linspace(-1, 1, n)

        for counter_1, pres_ref in enumerate(param_range):
            for counter_2, XNaCl in enumerate(param_range):
                for counter_3, rho_h2o in enumerate(param_range):
                    self.params['Fluid']['pres_ref'] += pres_ref
                    self.params['Fluid']['XNaCl'] += XNaCl
                    self.params['Fluid']['rho_h2o'] += rho_h2o
                    self.params['Pre-Processing']['case_name'] = f"GCS01_{counter_1}_{counter_2}_{counter_3}"

                    self.logger.info(f"Running simulation {counter_1}-{counter_2}-{counter_3} with pres_ref={self.params['Fluid']['pres_ref']}, XNaCl={self.params['Fluid']['XNaCl']}, rho_h2o={self.params['Fluid']['rho_h2o']}")
                    try:
                        self.run_simulation()
                        self.logger.info(f"Simulation {counter_1}-{counter_2}-{counter_3} completed successfully.")
                    except Exception as e:
                        self.logger.error(f"Simulation {counter_1}-{counter_2}-{counter_3} failed: {e}")
