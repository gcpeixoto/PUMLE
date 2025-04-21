"""
Simulation results parser for PUMLE.
Handles parsing and processing of simulation output data.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple, ClassVar
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from functools import lru_cache

from src.pumle.utils import convert_ndarray, read_json, write_json


@dataclass
class SimulationResults:
    """Container for simulation results with validation.
    
    Attributes:
        states: List of state dictionaries containing simulation data
        grid_dims: NumPy array containing grid dimensions
        active_cells: NumPy array indicating active cells
        metadata: Dictionary containing simulation metadata
    """
    states: List[Dict[str, Any]]
    grid_dims: np.ndarray
    active_cells: np.ndarray
    metadata: Dict[str, Any]
    
    def __post_init__(self) -> None:
        """Validate the simulation results data."""
        if not self.states:
            raise ValueError("States list cannot be empty")
        if len(self.grid_dims) != 3:
            raise ValueError("Grid dimensions must be a 3D array")
        if not isinstance(self.metadata, dict):
            raise ValueError("Metadata must be a dictionary")
        
    @property
    def num_states(self) -> int:
        """Get the number of states."""
        return len(self.states)
    
    @property
    def active_cell_count(self) -> int:
        """Get the number of active cells."""
        return np.sum(self.active_cells)


class SimResultsParserError(Exception):
    """Base exception for simulation results parsing."""
    pass


class SimResultsParser:
    """Parser for simulation results.
    
    This class handles the parsing and processing of simulation output data,
    including state data, grid dimensions, and active cell information.
    
    Attributes:
        REQUIRED_FILES: Set of required file patterns for parsing
        VALID_PARAMETERS: Set of valid state parameters
    """
    
    REQUIRED_FILES: ClassVar[set] = {
        "g_{case_name}.json",
        "grdecl_{case_name}_{sim_hash}.json",
        "states_{case_name}_{sim_hash}.json"
    }
    
    VALID_PARAMETERS: ClassVar[set] = {
        "pressure",
        "s",
        "temperature",
        "composition"
    }
    
    def __init__(
        self,
        results_path: Union[str, Path],
        sim_hash: str,
        case_name: str = "GCS01"
    ) -> None:
        """Initialize the results parser.
        
        Args:
            results_path: Path to results directory
            sim_hash: Simulation hash identifier
            case_name: Name of the simulation case (default: "GCS01")
            
        Raises:
            SimResultsParserError: If initialization fails or required files are missing
        """
        self.logger = logging.getLogger("pumle.sim_results_parser")
        
        try:
            self.results_path = Path(results_path)
            if not self.results_path.exists():
                raise SimResultsParserError(f"Results path does not exist: {results_path}")
                
            if not sim_hash:
                raise SimResultsParserError("Simulation hash cannot be empty")
            self.sim_hash = sim_hash
            
            if not case_name:
                raise SimResultsParserError("Case name cannot be empty")
            self.case_name = case_name
            
            self._validate_required_files()
            
            self.results: Optional[SimulationResults] = None
            self.dimensions: Optional[Tuple[int, int, int]] = None
            
        except Exception as e:
            self.logger.error(f"Failed to initialize SimResultsParser: {e}")
            raise SimResultsParserError(f"Parser initialization failed: {e}")
    
    def _validate_required_files(self) -> None:
        """Validate that all required files exist.
        
        Raises:
            SimResultsParserError: If any required file is missing
        """
        missing_files = []
        for file_pattern in self.REQUIRED_FILES:
            file_name = file_pattern.format(
                case_name=self.case_name,
                sim_hash=self.sim_hash
            )
            if not (self.results_path / file_name).exists():
                missing_files.append(file_name)
        
        if missing_files:
            raise SimResultsParserError(
                f"Missing required files: {', '.join(missing_files)}"
            )

    @lru_cache(maxsize=32)
    def _read_json_file(self, filename: str) -> Dict[str, Any]:
        """Read and parse a JSON file with caching.
        
        Args:
            filename: Name of the JSON file
            
        Returns:
            Dict containing parsed JSON data
            
        Raises:
            SimResultsParserError: If file reading fails
        """
        try:
            file_path = self.results_path / filename
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
                
            with open(file_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            self.logger.error(f"Failed to read JSON file {filename}: {e}")
            raise SimResultsParserError(f"JSON file reading failed: {e}")

    def get_dimensions(self) -> Tuple[int, int, int]:
        """Get grid dimensions from simulation results.
        
        Returns:
            Tuple of (i, j, k) dimensions
            
        Raises:
            SimResultsParserError: If dimensions cannot be read or are invalid
        """
        if self.dimensions is not None:
            return self.dimensions
            
        try:
            grid_file = f"g_{self.case_name}.json"
            dims = self._read_json_file(grid_file)
            
            if not isinstance(dims, list) or len(dims) != 3:
                raise ValueError("Invalid grid dimensions format")
                
            i, j, k = map(int, dims)
            if any(d <= 0 for d in (i, j, k)):
                raise ValueError("Grid dimensions must be positive")
                
            self.dimensions = (i, j, k)
            return self.dimensions
            
        except Exception as e:
            self.logger.error(f"Failed to get grid dimensions: {e}")
            raise SimResultsParserError(f"Grid dimensions reading failed: {e}")

    def get_active_cells(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get active cells information.
        
        Returns:
            Tuple of (active_cells, idx_to_get)
            
        Raises:
            SimResultsParserError: If active cells cannot be read or are invalid
        """
        try:
            grdecl_file = f"grdecl_{self.case_name}_{self.sim_hash}.json"
            active_cells = np.array(self._read_json_file(grdecl_file))
            
            if active_cells.size == 0:
                raise ValueError("Active cells array is empty")
                
            if not np.issubdtype(active_cells.dtype, np.bool_):
                active_cells = active_cells.astype(bool)
                
            idx_to_get = np.where(active_cells)[0]
            if idx_to_get.size == 0:
                raise ValueError("No active cells found")
                
            return active_cells, idx_to_get
            
        except Exception as e:
            self.logger.error(f"Failed to get active cells: {e}")
            raise SimResultsParserError(f"Active cells reading failed: {e}")

    def get_states(self, parameter: str) -> List[Any]:
        """Get state parameter values.
        
        Args:
            parameter: Name of the parameter to extract
            
        Returns:
            List of parameter values for each state
            
        Raises:
            SimResultsParserError: If states cannot be read or parameter is invalid
        """
        if parameter not in self.VALID_PARAMETERS:
            raise SimResultsParserError(
                f"Invalid parameter: {parameter}. "
                f"Valid parameters are: {', '.join(sorted(self.VALID_PARAMETERS))}"
            )
            
        try:
            states_file = f"states_{self.case_name}_{self.sim_hash}.json"
            states = self._read_json_file(states_file)
            
            if not states:
                raise ValueError("No states found in simulation results")
                
            if not all(parameter in state for state in states):
                raise ValueError(f"Parameter '{parameter}' not found in all states")
                
            return [state[parameter] for state in states]
            
        except Exception as e:
            self.logger.error(f"Failed to get states for parameter {parameter}: {e}")
            raise SimResultsParserError(f"States reading failed: {e}")

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all simulation data.
        
        Returns:
            List of dictionaries containing simulation data for each state
            
        Raises:
            SimResultsParserError: If data cannot be read
        """
        try:
            dimensions = self.get_dimensions()
            active_cells, idx_to_get = self.get_active_cells()
            
            # Get all states
            states_file = f"states_{self.case_name}_{self.sim_hash}.json"
            states = self._read_json_file(states_file)
            
            if not states:
                raise ValueError("No states found in simulation results")
                
            # Process each state
            processed_states = []
            for state in states:
                # Convert to numpy arrays for easier handling
                pressure = np.array(state.get("pressure", []))
                saturation = np.array(state.get("s", []))
                
                # Validate array sizes
                if len(pressure) != len(saturation):
                    raise ValueError(f"Pressure and saturation arrays have different sizes: {len(pressure)} vs {len(saturation)}")
                
                if len(pressure) < len(idx_to_get):
                    raise ValueError(f"State arrays ({len(pressure)}) smaller than active cells ({len(idx_to_get)})")
                
                # Only get data for valid indices
                valid_indices = idx_to_get[idx_to_get < len(pressure)]
                if len(valid_indices) < len(idx_to_get):
                    self.logger.warning(
                        f"Some active cell indices ({len(idx_to_get) - len(valid_indices)}) "
                        f"are out of bounds for state arrays of size {len(pressure)}"
                    )
                
                # Get data only for valid indices
                pressure_data = pressure[valid_indices]
                saturation_data = saturation[valid_indices]
                
                processed_state = {
                    "pressure": pressure_data.tolist(),
                    "saturation": saturation_data.tolist(),
                    "metadata": {
                        "case_name": self.case_name,
                        "sim_hash": self.sim_hash,
                        "dimensions": dimensions,
                        "total_cells": np.prod(dimensions),
                        "active_cells": int(np.sum(active_cells)),
                        "active_cell_indices": valid_indices.tolist(),
                        "timestamp": pd.Timestamp.now().isoformat()
                    }
                }
                processed_states.append(processed_state)
            
            self.logger.info(
                f"Successfully retrieved all simulation data for case {self.case_name}"
            )
            return processed_states
            
        except Exception as e:
            self.logger.error(f"Failed to get all simulation data: {e}")
            raise SimResultsParserError(f"Simulation data retrieval failed: {e}")

    def save_all(self, output_path: Union[str, Path]) -> None:
        """Save all simulation data to JSON files.
        
        Args:
            output_path: Path to save the data
            
        Raises:
            SimResultsParserError: If saving fails
        """
        try:
            output_path = Path(output_path)
            output_path.mkdir(parents=True, exist_ok=True)
            
            data = self.get_all()
            output_file = output_path / f"{self.case_name}_{self.sim_hash}.json"
            
            # Convert NumPy arrays to lists for JSON serialization
            data = convert_ndarray(data)
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Successfully saved data to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save simulation data: {e}")
            raise SimResultsParserError(f"Data saving failed: {e}")
