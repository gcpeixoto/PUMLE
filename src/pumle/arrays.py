"""
Array operations for PUMLE simulations.
Handles data consolidation, storage, and cloud upload functionality.
"""

import os
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional, Union, Any
from dataclasses import dataclass

import numpy as np
import zarr

from src.pumle.utils import read_json, setup_logger
from src.pumle.cloud_storage import CloudStorage


@dataclass
class ArrayConfig:
    """Configuration for array operations."""
    saving_method: str = "numpy"
    upload_to_s3: bool = False
    s3_config: Optional[Dict[str, str]] = None


class ArraysError(Exception):
    """Base exception for array operations."""
    pass


class Arrays:
    """Handles array operations for simulation data."""
    
    def __init__(self, output_data_path: Union[str, Path]) -> None:
        """Initialize Arrays instance.
        
        Args:
            output_data_path: Path to store output data
            
        Raises:
            ArraysError: If output directory cannot be created
        """
        self.logger = setup_logger("pumle.arrays")
        self.output_data_path = Path(output_data_path)
        # Store timestamps, initialized to None or 0
        self.timestamps = 0
        
        try:
            self.output_data_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create output directory: {e}")
            raise ArraysError(f"Output directory creation failed: {e}")

    def consolidate_all_data(
        self, 
        result: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Consolidate multiple simulation results (states over time).
        
        Args:
            result: List of processed state dictionaries, one per timestep,
                    as returned by SimResultsParser.get_all().
            
        Returns:
            Tuple of (pressure, water_saturation, gas_saturation) 
            arrays, each with shape (i, j, k, num_timesteps).
            
        Raises:
            ArraysError: If consolidation fails.
        """
        if not result:
            raise ArraysError("Input result list is empty, cannot consolidate.")

        try:
            # Get dimensions and total cell count from the first state's metadata
            first_metadata = result[0].get("metadata", {})
            dimensions = first_metadata.get("dimensions")
            if not dimensions or len(dimensions) != 3:
                raise ValueError("Missing or invalid dimensions in metadata")
            i, j, k = dimensions
            ncells_total = np.prod([i, j, k])
            
            num_ts = len(result)
            self.timestamps = num_ts # Store the number of timesteps

            # Initialize placeholder arrays for all cells over all timesteps
            # Using NaN or another placeholder might be better than zero if distinguishing missing data is important
            p_all = np.full((ncells_total, num_ts), np.nan) 
            sw_all = np.full((ncells_total, num_ts), np.nan)
            sg_all = np.full((ncells_total, num_ts), np.nan)

            # Fill arrays timestep by timestep
            for t, state_structure in enumerate(result):
                metadata = state_structure.get("metadata", {})
                # Get the active cell indices for this specific timestep
                idx_to_get = metadata.get("active_cell_indices", [])
                if not idx_to_get:
                    self.logger.warning(f"No active cell indices found for timestep {t}. Skipping.")
                    continue
                
                idx_to_get_np = np.array(idx_to_get)

                # Validate indices against total cells
                if np.any(idx_to_get_np >= ncells_total):
                    self.logger.warning(
                        f"Timestep {t}: Filtering out active cell indices >= {ncells_total}"
                    )
                    idx_to_get_np = idx_to_get_np[idx_to_get_np < ncells_total]

                if len(idx_to_get_np) == 0:
                     self.logger.warning(f"Timestep {t}: No valid active cell indices after filtering. Skipping.")
                     continue

                # Extract pressure and saturation data for the current timestep
                pressure_data = np.array(state_structure.get("pressure", []))
                # Saturation data from parser should already be (N_active, 2) list of lists
                saturation_data = np.array(state_structure.get("saturation", [])) 

                # --- Data Validation ---
                if pressure_data.size != len(idx_to_get_np):
                     self.logger.error(f"Timestep {t}: Pressure data size ({pressure_data.size}) mismatch with filtered active indices ({len(idx_to_get_np)}).")
                     raise ValueError(f"Pressure data size mismatch at timestep {t}")
                if saturation_data.shape[0] != len(idx_to_get_np):
                     self.logger.error(f"Timestep {t}: Saturation data rows ({saturation_data.shape[0]}) mismatch with filtered active indices ({len(idx_to_get_np)}).")
                     raise ValueError(f"Saturation data size mismatch at timestep {t}")    
                if saturation_data.ndim != 2 or saturation_data.shape[1] != 2:
                    raise ValueError(f"Timestep {t}: Expected saturation data shape (N, 2), but got {saturation_data.shape}")
                # --- End Validation ---

                # Assign data for the current timestep t using the active indices
                p_all[idx_to_get_np, t] = pressure_data
                sw_all[idx_to_get_np, t] = saturation_data[:, 0]
                sg_all[idx_to_get_np, t] = saturation_data[:, 1]

            # Reshape the final arrays to 4D: (i, j, k, num_timesteps)
            p_final = p_all.reshape((i, j, k, num_ts), order="F")
            sw_final = sw_all.reshape((i, j, k, num_ts), order="F")
            sg_final = sg_all.reshape((i, j, k, num_ts), order="F")
            
            self.logger.info(f"Successfully consolidated data into shape: {(i, j, k, num_ts)}")
            return p_final, sw_final, sg_final
            
        except Exception as e:
            self.logger.error(f"Data consolidation failed: {e}", exc_info=True) # Log traceback
            raise ArraysError(f"Data consolidation failed: {e}")

    def save_npy(self, name: str, data: np.ndarray) -> Path:
        """Save array to .npy file.
        
        Args:
            name: Name of the file
            data: Array data to save
            
        Returns:
            Path to saved file
            
        Raises:
            ArraysError: If save operation fails
        """
        try:
            file_path = self.output_data_path / f"{name}.npy"
            np.save(file_path, data)
            self.logger.debug(f"Saved numpy array to {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"Failed to save numpy array: {e}")
            raise ArraysError(f"Failed to save numpy array: {e}")

    def save_zarr(self, name: str, data: np.ndarray) -> Path:
        """Save array to zarr file.
        
        Args:
            name: Name of the file
            data: Array data to save
            
        Returns:
            Path to saved file
            
        Raises:
            ArraysError: If save operation fails
        """
        try:
            file_path = self.output_data_path / f"{name}.zarr"
            z = zarr.open(
                file_path,
                mode="w",
                shape=data.shape,
                dtype=data.dtype
            )
            z[:] = data
            self.logger.debug(f"Saved zarr array to {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"Failed to save zarr array: {e}")
            raise ArraysError(f"Failed to save zarr array: {e}")

    def format_name(self, name: str) -> str:
        """Format name by removing suffix.
        
        Args:
            name: Name to format
            
        Returns:
            Formatted name
        """
        return name.split("_")[0]

    def save_golden_data(
        self,
        sim_id: str,
        result: Optional[List[Dict[str, Any]]] = None,
        config: Optional[ArrayConfig] = None
    ) -> List[Tuple[str, Path]]:
        """Consolidate, save simulation data, and optionally upload to S3.
        
        Args:
            sim_id: Simulation hash identifier
            result: List of processed state dictionaries from SimResultsParser
            config: Array configuration
            
        Returns:
            List of tuples containing (name, file_path) for saved files
            
        Raises:
            ArraysError: If save operation fails
        """
        config = config or ArrayConfig()
        if result is None:
             raise ArraysError("Result data cannot be None for saving.")
             
        try:
            # Consolidate data using the refactored method
            p_final, sw_final, sg_final = self.consolidate_all_data(result)
            
            # Prepare data for saving
            to_save = {
                f"pressure_{sim_id}": p_final,
                f"water_saturation_{sim_id}": sw_final,
                f"gas_saturation_{sim_id}": sg_final,
            }
            
            # Select save engine
            save_engine = {
                "numpy": self.save_npy,
                "zarr": self.save_zarr
            }
            save_fn = save_engine.get(config.saving_method.strip().lower())
            
            if not save_fn:
                raise ValueError(f"Invalid saving method: {config.saving_method}")
            
            # Save files
            saved_files = []
            for name, data in to_save.items():
                file_path = save_fn(name, data)
                saved_files.append((name, file_path))
                self.logger.info(f"Saved {config.saving_method} data to {file_path}")
            
            # Upload to S3 if enabled
            if config.upload_to_s3:
                if not config.s3_config:
                    raise ValueError("s3_config required for S3 upload")
                    
                storage = CloudStorage(**config.s3_config)
                for name, file_path in saved_files:
                    # Example S3 path structure: consolidated/<type>/<filename>
                    s3_key = f"consolidated/{self.format_name(name)}/{file_path.name}"
                    self.logger.info(f"Uploading {file_path} to s3://{storage.bucket_name}/{s3_key}")
                    storage.upload_file(str(file_path), s3_key)
                    self.logger.info(f"Successfully uploaded to {s3_key}")
            
            return saved_files
            
        except Exception as e:
            self.logger.error(f"Failed to save golden data for sim_id {sim_id}: {e}", exc_info=True)
            # Re-raise as ArraysError for consistent error handling upstream
            raise ArraysError(f"Failed to save golden data: {e}")
