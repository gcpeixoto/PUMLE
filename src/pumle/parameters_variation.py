"""
Parameter variation generator for PUMLE simulations.
Handles generation of parameter combinations for sensitivity analysis.
"""

import logging
from copy import deepcopy
from typing import Dict, List, Any, Optional, Union
import numpy as np
from dataclasses import dataclass

from .parameters import Parameters


@dataclass
class VariationConfig:
    """Configuration for parameter variations."""
    min_points: int = 2
    max_points: int = 100
    default_class: str = "Fluid"
    min_delta: float = 0.01
    max_delta: float = 1.0


class ParameterVariationError(Exception):
    """Base exception for parameter variation operations."""
    pass


class ParametersVariation:
    """Generator for parameter variations in simulations.
    
    This class handles the generation of parameter combinations for
    sensitivity analysis and parameter sweeps.
    """
    
    def __init__(
        self,
        base_parameters: Dict[str, Dict[str, Any]],
        selected_parameters: List[str],
        variation_delta: float = 0.2,
        class_of_parameters: str = "Fluid",
        config: Optional[VariationConfig] = None
    ) -> None:
        """Initialize the parameter variation generator.
        
        Args:
            base_parameters: Base parameter set to vary from
            selected_parameters: List of parameters to vary
            variation_delta: Relative variation range (0.0 to 1.0)
            class_of_parameters: Parameter class to vary
            config: Optional configuration settings
            
        Raises:
            ParameterVariationError: If initialization fails
        """
        self.logger = logging.getLogger("pumle.parameter_variation")
        self.config = config or VariationConfig()
        
        try:
            # Validate inputs
            if not base_parameters:
                raise ValueError("Base parameters cannot be empty")
            if not selected_parameters:
                raise ValueError("Selected parameters cannot be empty")
            if not self.config.min_delta <= variation_delta <= self.config.max_delta:
                raise ValueError(
                    f"Variation delta must be between {self.config.min_delta} "
                    f"and {self.config.max_delta}"
                )
                
            self.base_parameters = base_parameters
            self.selected_parameters = selected_parameters
            self.variation_delta = variation_delta
            self.class_of_parameters = class_of_parameters
            
            # Calculate number of points for each parameter
            self.points_in_each_parameter = max(
                min(
                    int(1 / variation_delta) if variation_delta > 0 else 1,
                    self.config.max_points
                ),
                self.config.min_points
            )
            
            # Initialize combinations
            self.parameters_combinations = None
            self._generate_combinations()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize parameter variation: {e}")
            raise ParameterVariationError(f"Initialization failed: {e}")

    def get_parameters(self) -> List[Parameters]:
        """Get parameter objects for selected parameters.
        
        Returns:
            List of Parameter objects
            
        Raises:
            ParameterVariationError: If parameter creation fails
        """
        try:
            parameters = []
            for parameter in self.selected_parameters:
                try:
                    base_value = self.base_parameters[self.class_of_parameters][parameter]
                    parameters.append(
                        Parameters(
                            name=parameter,
                            base_value=base_value,
                            description=f"Variation of {parameter}",
                            variation_delta=self.variation_delta,
                        )
                    )
                except KeyError as e:
                    raise ValueError(f"Parameter {parameter} not found in {self.class_of_parameters}")
                    
            return parameters
            
        except Exception as e:
            self.logger.error(f"Failed to get parameters: {e}")
            raise ParameterVariationError(f"Parameter creation failed: {e}")

    def _format_combinations(self, combinations: List[List[float]]) -> np.ndarray:
        """Format parameter combinations into a matrix.
        
        Args:
            combinations: List of parameter value lists
            
        Returns:
            Array of parameter combinations
        """
        return np.array(np.meshgrid(*combinations)).T.reshape(
            -1, len(self.selected_parameters)
        )

    def _generate_combinations(self) -> None:
        """Generate all parameter value combinations.
        
        Raises:
            ParameterVariationError: If combination generation fails
        """
        try:
            parameters = self.get_parameters()
            parameters_combinations = []
            
            for parameter in parameters:
                range_of_values = np.linspace(
                    parameter.min_value,
                    parameter.max_value,
                    self.points_in_each_parameter
                )
                parameters_combinations.append(list(range_of_values))
                
            self.parameters_combinations = self._format_combinations(
                parameters_combinations
            )
            
            self.logger.info(
                f"Generated {len(self.parameters_combinations)} parameter combinations"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate parameter combinations: {e}")
            raise ParameterVariationError(f"Combination generation failed: {e}")

    def generate_variations(self) -> List[Dict[str, Any]]:
        """Generate parameter variations for all combinations.
        
        Returns:
            List of parameter sets with varied values
            
        Raises:
            ParameterVariationError: If variation generation fails
        """
        if self.parameters_combinations is None:
            raise ParameterVariationError(
                "No parameter combinations available. Call _generate_combinations first."
            )
            
        try:
            variations = []
            for sim_id, combination in enumerate(self.parameters_combinations):
                variation = deepcopy(self.base_parameters)
                
                # Update parameter values
                for i, parameter in enumerate(self.selected_parameters):
                    variation[self.class_of_parameters][parameter] = float(combination[i])
                
                # Set simulation ID
                variation["SimNums"]["sim_id"] = sim_id + 1
                variations.append(variation)
                
            self.logger.info(f"Generated {len(variations)} parameter variations")
            return variations
            
        except Exception as e:
            self.logger.error(f"Failed to generate parameter variations: {e}")
            raise ParameterVariationError(f"Variation generation failed: {e}")

    def get_variation_summary(self) -> Dict[str, Any]:
        """Get summary of parameter variations.
        
        Returns:
            Dictionary containing variation summary
        """
        return {
            "class": self.class_of_parameters,
            "parameters": self.selected_parameters,
            "delta": self.variation_delta,
            "points_per_parameter": self.points_in_each_parameter,
            "total_combinations": len(self.parameters_combinations)
        }
