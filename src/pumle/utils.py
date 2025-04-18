"""
Utility functions for PUMLE simulations.
Provides common functionality for data handling and processing.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Union, Optional
from dataclasses import dataclass

import numpy as np


@dataclass
class HashConfig:
    """Configuration for hash generation."""
    hash_length: int = 8
    encoding: str = "utf-8"
    hash_algorithm: str = "md5"


class UtilsError(Exception):
    """Base exception for utility operations."""
    pass


def setup_logger(name: str = "pumle.utils") -> logging.Logger:
    """Configure and return a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger


def generate_param_hash(
    params_dict: Dict[str, Any],
    config: Optional[HashConfig] = None
) -> str:
    """Generate a unique hash from parameter dictionary.
    
    Args:
        params_dict: Dictionary of parameters
        config: Optional hash configuration
        
    Returns:
        str: Generated hash string
        
    Raises:
        UtilsError: If hash generation fails
    """
    logger = setup_logger()
    config = config or HashConfig()
    
    try:
        # Ensure consistent key ordering
        param_str = json.dumps(params_dict, sort_keys=True)
        hash_obj = hashlib.new(
            config.hash_algorithm,
            param_str.encode(config.encoding)
        )
        return hash_obj.hexdigest()[:config.hash_length]
    except Exception as e:
        logger.error(f"Failed to generate parameter hash: {e}")
        raise UtilsError(f"Hash generation failed: {e}")


def convert_ndarray(
    obj: Union[np.ndarray, Dict, List, Any]
) -> Union[List, Dict, Any]:
    """Convert numpy arrays to lists recursively.
    
    Args:
        obj: Object to convert (numpy array, dict, list, or other)
        
    Returns:
        Union[List, Dict, Any]: Converted object
        
    Raises:
        UtilsError: If conversion fails
    """
    logger = setup_logger()
    
    try:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert_ndarray(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_ndarray(i) for i in obj]
        return obj
    except Exception as e:
        logger.error(f"Failed to convert numpy array: {e}")
        raise UtilsError(f"Array conversion failed: {e}")


def read_json(
    json_path: Union[str, Path],
    encoding: str = "utf-8"
) -> Dict[str, Any]:
    """Read JSON file and return its contents.
    
    Args:
        json_path: Path to JSON file
        encoding: File encoding
        
    Returns:
        Dict[str, Any]: JSON data
        
    Raises:
        UtilsError: If file reading fails
    """
    logger = setup_logger()
    json_path = Path(json_path)
    
    try:
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_path}")
            
        with open(json_path, "r", encoding=encoding) as file:
            return json.load(file)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {json_path}: {e}")
        raise UtilsError(f"Invalid JSON format: {e}")
    except Exception as e:
        logger.error(f"Failed to read JSON file {json_path}: {e}")
        raise UtilsError(f"JSON file reading failed: {e}")


def write_json(
    json_path: Union[str, Path],
    data: Dict[str, Any],
    encoding: str = "utf-8",
    indent: int = 4
) -> None:
    """Write data to JSON file.
    
    Args:
        json_path: Path to write JSON file
        data: Data to write
        encoding: File encoding
        indent: JSON indentation level
        
    Raises:
        UtilsError: If file writing fails
    """
    logger = setup_logger()
    json_path = Path(json_path)
    
    try:
        # Ensure parent directory exists
        json_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(json_path, "w", encoding=encoding) as file:
            json.dump(data, file, indent=indent)
        logger.debug(f"Successfully wrote JSON file: {json_path}")
    except Exception as e:
        logger.error(f"Failed to write JSON file {json_path}: {e}")
        raise UtilsError(f"JSON file writing failed: {e}")


def validate_path(path: Union[str, Path]) -> Path:
    """Validate and convert path to Path object.
    
    Args:
        path: Path to validate
        
    Returns:
        Path: Validated Path object
        
    Raises:
        UtilsError: If path is invalid
    """
    try:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        return path
    except Exception as e:
        raise UtilsError(f"Path validation failed: {e}")
