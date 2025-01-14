import os
import logging
import numpy as np

from scipy.io import loadmat
from typing import List, Tuple, Dict


class SimulationDataset:
    def __init__(self, data_path: str, co2_state: str = "SW") -> None:
        """Initialize the SimulationDataset class.

        Parameters
        ----------
        data_path : str
            Path to the directory containing simulation data files.
        """
        self.co2_state = co2_state
        self.data_path = data_path
        self.logger = self._setup_logger()
        self._validate_data_path()

    def _setup_logger(self) -> logging.Logger:
        """Set up the logger for the class."""
        logger = logging.getLogger("SimulationDatasetLogger")
        logger.setLevel(logging.DEBUG)

        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create a file handler
        log_file = os.path.join(os.getcwd(), "simulation_dataset.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Create a formatter and attach it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def _validate_data_path(self) -> None:
        """Validate that the data path exists and is a directory."""
        if not os.path.exists(self.data_path):
            self.logger.error(f"Data path does not exist: {self.data_path}")
            raise FileNotFoundError(f"Data path does not exist: {self.data_path}")

        if not os.path.isdir(self.data_path):
            self.logger.error(f"Data path is not a directory: {self.data_path}")
            raise NotADirectoryError(f"Data path is not a directory: {self.data_path}")

    def read_file(self, file_name: str) -> np.ndarray:
        """Read simulation data from a Matlab file.

        Parameters
        ----------
        file_name : str
            Name of the Matlab file to read.

        Returns
        -------
        Tuple[np.ndarray, np.ndarray, np.ndarray]
            Pressure (P), brine saturation (SW), and CO2 saturation (SG) arrays.
        """
        file_path = os.path.join(self.data_path, file_name)

        try:
            self.logger.info(f"Reading file: {file_path}")
            s = loadmat(file_path)

            # Extract grid dimensions
            I, J, K = (s['G'][0][0][3][0][0], s['G'][0][0][3][0][1], s['G'][0][0][3][0][2])
            ncells_total = I * J * K

            # Extract number of timesteps
            ts = s['states'].shape[0]

            # Extract active cells
            actnum = s['grdecl'][0][0][3]
            indices_to_get = np.where(actnum)[0]

            # Initialize arrays
            P = np.zeros((ncells_total, ts))
            SW = np.zeros((ncells_total, ts))
            SG = np.zeros((ncells_total, ts))

            # Populate arrays
            for ti in range(ts):
                p = s['states'][ti][0][0][0][0]
                sw = s['states'][ti][0][0][0][1][:, 0]
                sg = s['states'][ti][0][0][0][1][:, 1]

                P[indices_to_get, ti] = p.ravel()
                SW[indices_to_get, ti] = sw.ravel()
                SG[indices_to_get, ti] = sg.ravel()

            # Reshape arrays
            states = {
                "P"  : P.reshape((I, J, K, ts), order='F'),
                "SW" : SW.reshape((I, J, K, ts), order='F'),
                "SG" : SG.reshape((I, J, K, ts), order='F')
            }
            self.logger.info(f"Successfully read file: {file_path}")
            
            choosen_state = states.get(self.co2_state)
            if choosen_state is None:
                raise ValueError(f"Invalid CO2 state: {self.co2_state}")
            
            return choosen_state

        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise

    def read_files(self) -> np.ndarray:
        """
        Read all simulation data files in the data path and combine them into a single NumPy array.

        Returns
        -------
        np.ndarray
            Combined array where the first dimension corresponds to different files.
            Shape: (num_files, ...) where `...` is the shape of the data from each file.
        """
        self.logger.info(f"Reading all files in directory: {self.data_path}")

        data = []
        for file_name in os.listdir(self.data_path):
            if file_name.endswith('.mat'):
                try:
                    data.append(self.read_file(file_name))
                except Exception as e:
                    self.logger.warning(f"Skipping file {file_name} due to error: {e}")

        if not data:
            self.logger.error("No valid files found in the directory.")
            raise ValueError("No valid simulation data files to read.")

        # Combine data into a single NumPy array
        combined_data = np.stack(data)
        self.logger.info(f"Finished reading files. Combined data shape: {combined_data.shape}")
        return combined_data
    
    def save_as_numpy(self, data: np.ndarray, save_file_name: str) -> None:
        """Save simulation data as numpy arrays.

        Parameters
        ----------
        data : List[Tuple[np.ndarray, np.ndarray, np.ndarray]]
            List of tuples containing Pressure (P), brine saturation (SW), and CO2 saturation (SG) arrays.
        """
        self.logger.info(f"Saving simulation data as numpy arrays.")

        try:
            np.savez_compressed(os.path.join(self.data_path, f"{save_file_name}.npz"), {self.co2_state:data})
        except Exception as e:
            self.logger.error(f"Failed to save simulation data as numpy array: {e}")

        self.logger.info(f"Finished saving simulation data.")

    def read_numpy(self, file_name: str) -> np.ndarray:
        """Read simulation data from a numpy file.

        Parameters
        ----------
        file_name : str
            Name of the numpy file to read.

        Returns
        -------
        np.ndarray
            Pressure (P), brine saturation (SW), and CO2 saturation (SG) arrays.
        """
        file_path = os.path.join(self.data_path, file_name)

        try:
            self.logger.info(f"Reading file: {file_path}")
            data = np.load(file_path)
            self.logger.info(f"Successfully read file: {file_path}")
            return data[self.co2_state]

        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise
    
