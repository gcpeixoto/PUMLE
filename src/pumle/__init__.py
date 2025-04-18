"""
PUMLE - Python-based Unified Machine Learning Environment
A framework for managing and analyzing CO2 injection simulations.

This package provides tools for:
- Managing simulation parameters and configurations
- Handling MATLAB file operations
- Processing and analyzing simulation results
- Managing data storage and persistence
- Cloud storage integration
"""

__version__ = "0.1.0"

# Core components
from .pumle import Pumle
from .db import DBManager
from .parameters import Parameters
from .mat_files import MatFiles
from .tabular import Tabular
from .paths import Paths
from .cloud_storage import CloudStorage
from .metadata import Metadata

__all__ = [
    # Core components
    "Pumle",
    "DBManager",
    "Parameters",
    "MatFiles",
    "Tabular",
    "Paths",
    "CloudStorage",
    "Metadata",
    "SimResultsParser",
    "SimulationResults",
    "ParametersVariation",
    
    # Error classes
    "DBError",
    "ParameterError",
    "MatFilesError",
    "TabularError",
    "PathsError",
    "CloudStorageError",
    "MetadataError",
    "SimResultsParserError"
]
