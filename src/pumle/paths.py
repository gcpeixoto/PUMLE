"""
Path management for PUMLE simulations.
Handles file paths and directory structure for simulation data.
"""

import logging
from pathlib import Path
from typing import Optional, Union
from dataclasses import dataclass


@dataclass
class PathsConfig:
    """Configuration for path operations."""
    default_grid_path: str = "benchmark/unisim-1-d/UNISIM_I_D_ECLIPSE.DATA"


class PathsError(Exception):
    """Base exception for path operations."""
    pass


class Paths:
    """Handles path operations for simulation data.
    
    This class manages file paths and directory structure for PUMLE simulations,
    ensuring consistent path handling across different operating systems.
    """
    
    def __init__(
        self, 
        path: Union[str, Path],
        grid_path: Optional[str] = None,
        config: Optional[PathsConfig] = None
    ) -> None:
        """Initialize Paths instance.
        
        Args:
            path: Base path for simulation data
            grid_path: Optional path to grid file
            config: Optional path configuration
            
        Raises:
            PathsError: If initialization fails
        """
        self.logger = logging.getLogger("pumle.paths")
        self.config = config or PathsConfig()
        
        try:
            self.path = Path(path).resolve()
            self.grid_path = self.set_grid_path(
                grid_path or self.config.default_grid_path
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize paths: {e}")
            raise PathsError(f"Path initialization failed: {e}")

    def set_grid_path(self, grid_path: str) -> Path:
        """Set and validate grid file path.
        
        Args:
            grid_path: Path to grid file
            
        Returns:
            Resolved grid file path
            
        Raises:
            PathsError: If grid path is invalid
        """
        try:
            # Convert to Path and resolve relative to base path
            grid_path = Path(grid_path)
            if not grid_path.is_absolute():
                grid_path = self.path / grid_path
            
            # Validate grid file exists
            if not grid_path.exists():
                self.logger.error(f"Grid file not found: {grid_path}")
                raise PathsError(f"Grid file not found: {grid_path}")
                
            return grid_path.resolve()
        except Exception as e:
            self.logger.error(f"Failed to set grid path: {e}")
            raise PathsError(f"Grid path setting failed: {e}")

    def get_path(self) -> Path:
        """Get base simulation path.
        
        Returns:
            Base simulation path
        """
        return self.path

    def get_grid_path(self) -> Path:
        """Get grid file path.
        
        Returns:
            Grid file path
        """
        return self.grid_path
