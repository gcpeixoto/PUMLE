"""
Parameter management for PUMLE simulations.
Handles physical parameter validation and value ranges.
"""

from typing import Any, Dict, Tuple, Optional
from dataclasses import dataclass
import logging
from enum import Enum


class ParameterType(Enum):
    """Enumeration of parameter types with their units."""
    PRESSURE = "MPa"
    TEMPERATURE = "°C"
    COMPRESSIBILITY = "1/bar"
    SATURATION = "fraction"
    ENTRY_PRESSURE = "kPa"
    MASS_FRACTION = "fraction"
    DENSITY = "kg/m³"


@dataclass
class ParameterLimits:
    """Data class for parameter physical limits."""
    min_value: float
    max_value: float
    unit: str
    description: str


class Parameters:
    """Manages simulation parameters with physical constraints."""
    
    # Physical limits for parameters with units and descriptions
    PHYSICAL_LIMITS: Dict[str, ParameterLimits] = {
        "pres_ref": ParameterLimits(1, 100, ParameterType.PRESSURE.value, "Reference pressure"),
        "temp_ref": ParameterLimits(0, 200, ParameterType.TEMPERATURE.value, "Reference temperature"),
        "cp_rock": ParameterLimits(1e-6, 1e-3, ParameterType.COMPRESSIBILITY.value, "Rock compressibility"),
        "srw": ParameterLimits(0, 0.3, ParameterType.SATURATION.value, "Residual water saturation"),
        "src": ParameterLimits(0, 0.3, ParameterType.SATURATION.value, "Residual CO2 saturation"),
        "pe": ParameterLimits(0.1, 10, ParameterType.ENTRY_PRESSURE.value, "Entry pressure"),
        "xnacl": ParameterLimits(0, 0.2, ParameterType.MASS_FRACTION.value, "NaCl mass fraction"),
        "rho_h2o": ParameterLimits(900, 1200, ParameterType.DENSITY.value, "Water density"),
    }

    def __init__(
        self,
        name: str,
        base_value: float,
        variation_delta: float,
        description: str = ""
    ) -> None:
        """Initialize a parameter with physical constraints.
        
        Args:
            name: Parameter name
            base_value: Base value for the parameter
            variation_delta: Allowed variation from base value (fraction)
            description: Optional parameter description
            
        Raises:
            ValueError: If parameter name is invalid or values are out of bounds
        """
        self._setup_logger()
        
        if not isinstance(base_value, (int, float)):
            raise ValueError(f"Base value must be numeric, got {type(base_value)}")
            
        if not 0 <= variation_delta <= 1:
            raise ValueError(f"Variation delta must be between 0 and 1, got {variation_delta}")
            
        self.name = name
        self.base_value = float(base_value)
        self.description = description
        self.variation_delta = variation_delta
        
        self._validate_parameter()
        self._calculate_limits()
        
    def _setup_logger(self) -> None:
        """Configure logging for the parameter manager."""
        self.logger = logging.getLogger("pumle.parameters")
        self.logger.setLevel(logging.DEBUG)
        
    def _validate_parameter(self) -> None:
        """Validate parameter name and base value against physical limits."""
        if self.name not in self.PHYSICAL_LIMITS:
            self.logger.warning(f"Parameter {self.name} has no physical limits defined")
            return
            
        limits = self.PHYSICAL_LIMITS[self.name]
        if not limits.min_value <= self.base_value <= limits.max_value:
            raise ValueError(
                f"Base value {self.base_value} for {self.name} is outside physical limits "
                f"[{limits.min_value}, {limits.max_value}] {limits.unit}"
            )
            
    def _calculate_limits(self) -> None:
        """Calculate min and max values considering physical limits."""
        if self.name in self.PHYSICAL_LIMITS:
            limits = self.PHYSICAL_LIMITS[self.name]
            self.min_value = max(
                limits.min_value,
                self.base_value * (1 - self.variation_delta)
            )
            self.max_value = min(
                limits.max_value,
                self.base_value * (1 + self.variation_delta)
            )
            self.unit = limits.unit
        else:
            self.min_value = self.base_value * (1 - self.variation_delta)
            self.max_value = self.base_value * (1 + self.variation_delta)
            self.unit = "unitless"
            
    def get_limits(self) -> Tuple[float, float]:
        """Get the parameter's value range.
        
        Returns:
            Tuple[float, float]: Minimum and maximum allowed values
        """
        return self.min_value, self.max_value
        
    def is_valid(self, value: float) -> bool:
        """Check if a value is within the parameter's valid range.
        
        Args:
            value: Value to check
            
        Returns:
            bool: True if value is within valid range
        """
        return self.min_value <= value <= self.max_value
        
    def __str__(self) -> str:
        """String representation of the parameter.
        
        Returns:
            str: Formatted parameter information
        """
        limits = self.PHYSICAL_LIMITS.get(self.name)
        if limits:
            return (
                f"{self.name}: {self.base_value} {limits.unit} "
                f"({self.description})\n"
                f"Range: [{self.min_value}, {self.max_value}] {limits.unit}"
            )
        return f"{self.name}: {self.base_value} ({self.description})"
