"""
Configuration file parser for PUMLE.
Handles reading and validation of INI configuration files.
"""

import logging
import configparser
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass

from .paths import Paths


@dataclass
class IniConfig:
    """Configuration for INI file parsing."""
    cast_bool_params: bool = False
    required_sections: List[str] = None
    default_values: Dict[str, Dict[str, Any]] = None


class IniError(Exception):
    """Base exception for INI file operations."""
    pass


class Ini:
    """Parser for INI configuration files.
    
    This class handles reading and validation of INI configuration files,
    supporting type casting and parameter validation.
    """
    
    def __init__(
        self,
        root_path: Union[str, Path],
        config_path: Union[str, Path],
        sections_schema: Dict[str, Tuple[List[str], bool]],
        config: Optional[IniConfig] = None
    ) -> None:
        """Initialize the INI file parser.
        
        Args:
            root_path: Root path for resolving relative paths
            config_path: Path to the INI configuration file
            sections_schema: Schema defining sections and their parameters
                Key: section name
                Value: Tuple of (parameter list, cast_to_float flag)
            config: Optional configuration settings
            
        Raises:
            IniError: If initialization fails
        """
        self.logger = logging.getLogger("pumle.ini")
        self.config = config or IniConfig()
        
        try:
            self.root_path = Path(root_path).resolve()
            self.config_path = Path(config_path).resolve()
            self.sections_schema = sections_schema
            self.params: Dict[str, Dict[str, Any]] = {}
            
            self._validate_config_file()
            self._load_config()
            self._setup_paths()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize INI parser: {e}")
            raise IniError(f"INI initialization failed: {e}")

    def _validate_config_file(self) -> None:
        """Validate that the configuration file exists and is readable.
        
        Raises:
            IniError: If file validation fails
        """
        if not self.config_path.is_file():
            raise IniError(f"Configuration file not found: {self.config_path}")
            
        if not os.access(self.config_path, os.R_OK):
            raise IniError(f"Configuration file not readable: {self.config_path}")

    def _cast_value(self, value: str, cast_to_float: bool, param: str) -> Any:
        """Cast a value to the appropriate type.
        
        Args:
            value: Value to cast
            cast_to_float: Whether to cast to float
            param: Parameter name for bool detection
            
        Returns:
            Casted value
            
        Raises:
            ValueError: If casting fails
        """
        try:
            if cast_to_float:
                return float(value)
            elif self.config.cast_bool_params and param.endswith("_flag"):
                return value.lower() in ("true", "1", "yes", "on")
            return value
        except ValueError as e:
            raise ValueError(f"Failed to cast value '{value}': {e}")

    def _load_config(self) -> None:
        """Load and parse the INI configuration file.
        
        Raises:
            IniError: If loading or parsing fails
        """
        try:
            config = configparser.ConfigParser()
            config.read(self.config_path)
            
            # Process each section in the schema
            for section, (params, cast_to_float) in self.sections_schema.items():
                section_params = {}
                
                # If section exists, process its parameters
                if config.has_section(section):
                    for param in params:
                        try:
                            value = config.get(section, param)
                            section_params[param] = self._cast_value(
                                value, cast_to_float, param
                            )
                        except (configparser.NoOptionError, ValueError) as e:
                            self.logger.error(
                                f"Error reading parameter '{param}' from section '{section}': {e}"
                            )
                            raise IniError(f"Parameter reading failed: {e}")
                
                # Store section parameters
                self.params[section] = section_params
                
            # Validate required sections
            if self.config.required_sections:
                missing = [s for s in self.config.required_sections if not self.params.get(s)]
                if missing:
                    raise IniError(f"Missing required sections: {', '.join(missing)}")
                    
            # Apply default values
            if self.config.default_values:
                for section, defaults in self.config.default_values.items():
                    if section not in self.params:
                        self.params[section] = {}
                    for param, value in defaults.items():
                        if param not in self.params[section]:
                            self.params[section][param] = value
                            
            self.logger.info(f"Successfully loaded configuration from {self.config_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise IniError(f"Configuration loading failed: {e}")

    def _setup_paths(self) -> None:
        """Set up paths using the Paths class.
        
        Raises:
            IniError: If path setup fails
        """
        try:
            paths = Paths(self.root_path)
            
            if "Paths" not in self.params:
                self.params["Paths"] = {}
            if "Grid" not in self.params:
                self.params["Grid"] = {}
                
            self.params["Paths"]["PUMLE_ROOT"] = str(paths.get_path())
            self.params["Grid"]["file_path"] = str(paths.get_grid_path())
            
        except Exception as e:
            self.logger.error(f"Failed to setup paths: {e}")
            raise IniError(f"Path setup failed: {e}")

    def get_params(self) -> Dict[str, Dict[str, Any]]:
        """Get all parsed parameters.
        
        Returns:
            Dictionary containing all parsed parameters
        """
        return self.params

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get parameters for a specific section.
        
        Args:
            section: Name of the section
            
        Returns:
            Dictionary containing section parameters
            
        Raises:
            IniError: If section does not exist
        """
        if section not in self.params:
            raise IniError(f"Section not found: {section}")
        return self.params[section]

    def __repr__(self) -> str:
        """Get string representation of the configuration.
        
        Returns:
            String representation of parameters
        """
        return f"Configuration parameters: {self.params}"
