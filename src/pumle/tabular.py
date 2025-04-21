"""
Tabular data handling for PUMLE simulations.
Manages reading, structuring, and saving simulation data in various formats.
"""

import logging
from pathlib import Path
from typing import Optional, Union, Literal, Dict, Any
import numpy as np
import pandas as pd
import zarr
from dataclasses import dataclass


@dataclass
class TabularConfig:
    """Configuration for tabular data operations."""
    default_attr: str = "sg"
    supported_structures: tuple = ("zarr", "numpy", None)


class TabularError(Exception):
    """Base exception for tabular data operations."""
    pass


class Tabular:
    """Handles tabular data operations for simulation results.
    
    This class manages reading, structuring, and saving simulation data
    in various formats (Zarr, NumPy, CSV).
    """
    
    def __init__(
        self,
        input_data_path: Union[str, Path],
        output_data_path: Union[str, Path],
        input_structure: Optional[Literal["zarr", "numpy"]] = None,
        attr: str = "sg",
        config: Optional[TabularConfig] = None
    ) -> None:
        """Initialize Tabular instance.
        
        Args:
            input_data_path: Path to input data directory
            output_data_path: Path to output data directory
            input_structure: Input data structure type ("zarr" or "numpy")
            attr: Attribute name for data files
            config: Optional configuration
            
        Raises:
            TabularError: If initialization fails
        """
        self.logger = logging.getLogger("pumle.tabular")
        self.config = config or TabularConfig()
        
        try:
            self.input_data_path = Path(input_data_path)
            self.output_data_path = Path(output_data_path)
            self.input_structure = input_structure
            self.attr = attr or self.config.default_attr
            self.data: Optional[Union[np.ndarray, pd.DataFrame]] = None
            
            # Validate input structure
            if self.input_structure not in self.config.supported_structures:
                raise ValueError(
                    f"Invalid input structure: {self.input_structure}. "
                    f"Must be one of {self.config.supported_structures}"
                )
        except Exception as e:
            self.logger.error(f"Failed to initialize Tabular: {e}")
            raise TabularError(f"Tabular initialization failed: {e}")

    def read_data(self) -> None:
        """Read simulation data from input path.
        
        Raises:
            TabularError: If reading fails or file not found
        """
        try:
            file_path = self.input_data_path / f"{self.attr}"
            
            if self.input_structure == "zarr":
                data = zarr.open(str(file_path.with_suffix(".zarr")), mode="r")
            elif self.input_structure == "numpy" or self.input_structure is None:
                data = np.load(str(file_path.with_suffix(".npy")))
            else:
                raise ValueError(f"Unsupported input structure: {self.input_structure}")
                
            self.data = data
            self.logger.info(f"Successfully read data from {file_path}")
            
        except FileNotFoundError as e:
            self.logger.error(f"Data file not found: {e}")
            raise TabularError(f"Data file not found: {e}")
        except Exception as e:
            self.logger.error(f"Failed to read data: {e}")
            raise TabularError(f"Data reading failed: {e}")

    def structure_data(self) -> None:
        """Structure simulation data into a pandas DataFrame.
        
        Raises:
            TabularError: If data is not loaded or structuring fails
        """
        if self.data is None:
            raise TabularError("No data loaded. Call read_data() first.")
            
        try:
            if not isinstance(self.data, np.ndarray):
                raise ValueError("Data must be a numpy array for structuring")
                
            first_iteration = True
            number_of_simulations = self.data.shape[4]
            number_of_times = self.data.shape[3]
            
            for sim_id in range(number_of_simulations):
                for i in range(number_of_times):
                    x, y, z = self.data[:, :, :, i, sim_id].nonzero()
                    values = self.data[x, y, z, i, sim_id]
                    
                    data_df = {
                        "simulation": sim_id,
                        "timestamp": i,
                        "x": x,
                        "y": y,
                        "z": z,
                        "values": values,
                    }
                    
                    if first_iteration:
                        df = pd.DataFrame(data_df)
                        first_iteration = False
                    else:
                        df = pd.concat([df, pd.DataFrame(data_df)], ignore_index=True)
                        
            self.data = df
            self.logger.info("Successfully structured data into DataFrame")
            
        except Exception as e:
            self.logger.error(f"Failed to structure data: {e}")
            raise TabularError(f"Data structuring failed: {e}")

    def save_data(self) -> None:
        """Save structured data to CSV file.
        
        Raises:
            TabularError: If data is not structured or saving fails
        """
        if self.data is None:
            raise TabularError("No data loaded. Call read_data() first.")
            
        if not isinstance(self.data, pd.DataFrame):
            raise TabularError("Data must be structured before saving. Call structure_data() first.")
            
        try:
            # Ensure output directory exists
            self.output_data_path.mkdir(parents=True, exist_ok=True)
            
            # Save to CSV
            output_file = self.output_data_path / f"{self.attr}.csv"
            self.data.to_csv(output_file, index=False)
            self.logger.info(f"Successfully saved data to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")
            raise TabularError(f"Data saving failed: {e}")
