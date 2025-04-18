"""
MATLAB file operations for PUMLE simulations.
Handles creation and management of MATLAB data files for simulation input.
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from scipy.io import savemat
import logging
from dataclasses import dataclass


@dataclass
class MatFileConfig:
    """Configuration for MATLAB file operations."""
    pumle_root: str
    staging_folder: str
    sim_hash: str
    params: Dict[str, Any]


class MatFiles:
    """Manages MATLAB file operations for simulation input."""
    
    # Required parameter sections
    REQUIRED_SECTIONS: List[str] = [
        "Paths",
        "EXECUTION",
        "Fluid",
        "Pre-Processing",
        "SimNums"
    ]
    
    def __init__(self, params: Dict[str, Any]) -> None:
        """Initialize the MATLAB file manager.
        
        Args:
            params: Dictionary containing simulation parameters
            
        Raises:
            ValueError: If required parameters are missing
        """
        self._setup_logger()
        self.config = self._create_config(params)
        self._validate_params()
        
    def _setup_logger(self) -> None:
        """Configure logging for the MATLAB file manager."""
        self.logger = logging.getLogger("pumle.mat_files")
        self.logger.setLevel(logging.DEBUG)
        
    def _create_config(self, params: Dict[str, Any]) -> MatFileConfig:
        """Create configuration from parameters.
        
        Args:
            params: Dictionary containing simulation parameters
            
        Returns:
            MatFileConfig: Configuration object
            
        Raises:
            ValueError: If required fields are missing
        """
        try:
            return MatFileConfig(
                pumle_root=params["Paths"]["PUMLE_ROOT"],
                staging_folder=params["SimNums"]["staging_folder"],
                sim_hash=params["SimNums"]["sim_hash"],
                params=params
            )
        except KeyError as e:
            raise ValueError(f"Missing required field in parameters: {e}")
            
    def _validate_params(self) -> None:
        """Validate that all required parameter sections are present.
        
        Raises:
            ValueError: If any required section is missing
        """
        missing_sections = [
            section for section in self.REQUIRED_SECTIONS
            if section not in self.config.params
        ]
        
        if missing_sections:
            raise ValueError(
                f"Missing required parameter sections: {', '.join(missing_sections)}"
            )
            
    def _create_directory(self, path: Path) -> None:
        """Create directory if it doesn't exist.
        
        Args:
            path: Path to create
            
        Raises:
            OSError: If directory creation fails
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {path}")
        except OSError as e:
            self.logger.error(f"Failed to create directory {path}: {e}")
            raise
            
    def _get_safe_section_name(self, section: str) -> str:
        """Convert section name to safe filename.
        
        Args:
            section: Original section name
            
        Returns:
            str: Safe filename without special characters
        """
        return section.replace("-", "").replace(" ", "")
        
    def _get_mat_file_path(self, section: str) -> Path:
        """Get path for MATLAB file.
        
        Args:
            section: Parameter section name
            
        Returns:
            Path: Full path to MATLAB file
        """
        safe_section = self._get_safe_section_name(section)
        return (
            Path(self.config.pumle_root) /
            "data_lake" /
            "staging" /
            self.config.staging_folder /
            f"{safe_section}_{self.config.sim_hash}.mat"
        )
        
    def write(self) -> None:
        """Write all parameter sections to MATLAB files.
        
        Raises:
            FileNotFoundError: If file writing fails
        """
        staging_path = (
            Path(self.config.pumle_root) /
            "data_lake" /
            "staging" /
            self.config.staging_folder
        )
        self._create_directory(staging_path)
        
        for section, content in self.config.params.items():
            mat_file = self._get_mat_file_path(section)
            try:
                savemat(str(mat_file), content, appendmat=True)
                self.logger.info(f"Created MATLAB file: {mat_file}")
            except Exception as e:
                self.logger.error(f"Failed to create MATLAB file {mat_file}: {e}")
                raise FileNotFoundError(
                    f"Failed to export MATLAB file '{mat_file.name}': {e}"
                )
