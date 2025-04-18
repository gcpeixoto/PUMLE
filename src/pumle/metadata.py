"""
Metadata handling for PUMLE simulations.
Manages simulation parameters, validation, and storage.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from functools import reduce

import pandas as pd
import pandera as pa
from pandera import DataFrameSchema, Column


@dataclass
class MetadataConfig:
    """Configuration for metadata operations."""
    parameters_id: str = "sim_id"
    output_file: str = "metadata.csv"


class MetadataError(Exception):
    """Base exception for metadata operations."""
    pass


# Base schema for metadata validation
BASE_SCHEMA = DataFrameSchema(
    {
        "sim_id": Column(str, checks=pa.Check.str_matches(r"^\d+$"), nullable=False),
        "fluid__pres_ref": Column(float, checks=pa.Check.gt(0), nullable=False),
        "fluid__temp_ref": Column(float, checks=pa.Check.gt(0), nullable=False),
        "fluid__cp_rock": Column(float, checks=pa.Check.gt(0), nullable=False),
        "fluid__srw": Column(float, checks=pa.Check.in_range(0, 1), nullable=False),
        "fluid__src": Column(float, checks=pa.Check.in_range(0, 1), nullable=False),
        "fluid__pe": Column(float, checks=pa.Check.gt(0), nullable=False),
        "fluid__xnacl": Column(float, checks=pa.Check.ge(0), nullable=False),
        "fluid__rho_h2o": Column(float, checks=pa.Check.gt(0), nullable=False),
        "initial_conditions__sw_0": Column(
            float, checks=pa.Check.in_range(0, 1), nullable=False
        ),
        "boundary_conditions__type": Column(str, nullable=False),
        "wells__co2_inj": Column(float, checks=pa.Check.gt(0), nullable=False),
        "schedule__injection_time": Column(
            int, checks=pa.Check.gt(0), nullable=False
        ),
        "schedule__migration_time": Column(
            int, checks=pa.Check.gt(0), nullable=False
        ),
        "schedule__injection_timesteps": Column(
            int, checks=pa.Check.gt(0), nullable=False
        ),
        "schedule__migration_timesteps": Column(
            int, checks=pa.Check.gt(0), nullable=False
        ),
    }
)


class Metadata:
    """Handles metadata operations for simulation data."""
    
    def __init__(
        self, 
        path: Union[str, Path],
        config: Optional[MetadataConfig] = None
    ) -> None:
        """Initialize Metadata instance.
        
        Args:
            path: Path to store metadata
            config: Optional metadata configuration
            
        Raises:
            MetadataError: If initialization fails
        """
        self.logger = logging.getLogger("pumle.metadata")
        self.path = Path(path)
        self.config = config or MetadataConfig()
        self.schema = BASE_SCHEMA.copy()
        
        # Initialize data attributes
        self.parameters: Optional[pd.DataFrame] = None
        self.base_schema: Optional[Dict[str, Tuple[List[str], Any]]] = None
        self.dimensions: Optional[Tuple[int, int, int]] = None
        self.timestamps: Optional[int] = None
        
        try:
            self.path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create metadata directory: {e}")
            raise MetadataError(f"Metadata directory creation failed: {e}")

    def get_data(self, **kwargs) -> None:
        """Update metadata attributes from keyword arguments.
        
        Args:
            **kwargs: Keyword arguments to update attributes
        """
        self.parameters = kwargs.get("parameters", self.parameters)
        self.base_schema = kwargs.get("base_schema", self.base_schema)
        self.dimensions = kwargs.get("dimensions", self.dimensions)
        self.timestamps = kwargs.get("timestamps", self.timestamps)

    def to_data_frame(self) -> None:
        """Convert parameters to pandas DataFrame.
        
        Raises:
            MetadataError: If conversion fails
        """
        try:
            self.parameters = pd.DataFrame(self.parameters)
        except Exception as e:
            self.logger.error(f"Failed to convert parameters to DataFrame: {e}")
            raise MetadataError(f"DataFrame conversion failed: {e}")

    def _format_column_name(self, *column_name: str) -> str:
        """Format column name by joining with double underscore.
        
        Args:
            *column_name: Column name parts
            
        Returns:
            Formatted column name
        """
        clear = lambda x: x.replace(" ", "_").replace("-", "_").lower()
        return reduce(lambda x, y: clear(x) + "__" + clear(y), column_name)

    def _cast_columns(
        self, 
        df: pd.DataFrame, 
        columns: List[str], 
        dtype: type
    ) -> None:
        """Cast DataFrame columns to specified type.
        
        Args:
            df: DataFrame to modify
            columns: Columns to cast
            dtype: Target data type
            
        Raises:
            MetadataError: If casting fails
        """
        try:
            for column in columns:
                df[column] = df[column].astype(dtype)
        except Exception as e:
            self.logger.error(f"Failed to cast columns: {e}")
            raise MetadataError(f"Column casting failed: {e}")

    def _cast_base_cols(self) -> None:
        """Cast base columns to appropriate types.
        
        Raises:
            MetadataError: If casting fails
        """
        try:
            # Cast string columns
            self._cast_columns(self.parameters, ["sim_id"], str)
            
            # Cast integer columns
            int_columns = [
                "schedule__injection_time",
                "schedule__migration_time",
                "schedule__injection_timesteps",
                "schedule__migration_timesteps",
            ]
            self._cast_columns(self.parameters, int_columns, int)
            
            # Cast float columns
            float_columns = [
                "fluid__pres_ref",
                "fluid__temp_ref",
                "fluid__cp_rock",
                "fluid__srw",
                "fluid__src",
                "fluid__pe",
                "fluid__xnacl",
                "fluid__rho_h2o",
                "initial_conditions__sw_0",
                "wells__co2_inj",
            ]
            self._cast_columns(self.parameters, float_columns, float)
        except Exception as e:
            self.logger.error(f"Failed to cast base columns: {e}")
            raise MetadataError(f"Base column casting failed: {e}")

    def _clean_parameters(self) -> None:
        """Clean and format parameter data.
        
        Raises:
            MetadataError: If cleaning fails
        """
        try:
            columns_to_parse = {
                "Fluid",
                "Initial Conditions",
                "Boundary Conditions",
                "Wells",
                "Schedule",
                "SimNums",
            }
            
            columns_to_drop = [
                "Paths",
                "Pre-Processing",
                "Grid",
                "Fluid",
                "Initial Conditions",
                "Boundary Conditions",
                "Wells",
                "Schedule",
                "EXECUTION",
                "SimNums",
            ]
            
            for main_field, (child_fields, _) in self.base_schema.items():
                if main_field not in columns_to_parse:
                    continue
                    
                values = self.parameters[main_field].values
                values_extracted = (
                    values if isinstance(values[0], dict) 
                    else list(map(eval, values))
                )
                
                for child_field in child_fields:
                    values = [value[child_field] for value in values_extracted]
                    if child_field == self.config.parameters_id:
                        self.parameters[child_field] = values
                    else:
                        self.parameters[
                            self._format_column_name(main_field, child_field)
                        ] = values
                        
            self.parameters.drop(columns=columns_to_drop, inplace=True)
            self._cast_base_cols()
        except Exception as e:
            self.logger.error(f"Failed to clean parameters: {e}")
            raise MetadataError(f"Parameter cleaning failed: {e}")

    def _validate_schema(self) -> None:
        """Validate DataFrame against schema.
        
        Raises:
            MetadataError: If validation fails
        """
        try:
            self.schema.validate(self.parameters)
        except Exception as e:
            self.logger.error(f"Schema validation failed: {e}")
            raise MetadataError(f"Schema validation failed: {e}")

    def _add_dimensions(self) -> None:
        """Add dimension columns to DataFrame.
        
        Raises:
            MetadataError: If dimension addition fails
        """
        try:
            self.parameters["dimension_x"] = self.dimensions[0]
            self.parameters["dimension_y"] = self.dimensions[1]
            self.parameters["dimension_z"] = self.dimensions[2]
            
            self._cast_columns(
                self.parameters, 
                ["dimension_x", "dimension_y", "dimension_z"], 
                int
            )
            
            dimensions_schema = {
                "dimension_x": Column(int, checks=pa.Check.gt(0), nullable=False),
                "dimension_y": Column(int, checks=pa.Check.gt(0), nullable=False),
                "dimension_z": Column(int, checks=pa.Check.gt(0), nullable=False),
            }
            self.schema.add_columns(dimensions_schema)
        except Exception as e:
            self.logger.error(f"Failed to add dimensions: {e}")
            raise MetadataError(f"Dimension addition failed: {e}")

    def _add_timestamps(self) -> None:
        """Add timestamp column to DataFrame.
        
        Raises:
            MetadataError: If timestamp addition fails
        """
        try:
            self.parameters["timestamps"] = self.timestamps
            self._cast_columns(self.parameters, ["timestamps"], int)
            
            timestamps_schema = {
                "timestamps": Column(int, checks=pa.Check.gt(0), nullable=False),
            }
            self.schema.add_columns(timestamps_schema)
        except Exception as e:
            self.logger.error(f"Failed to add timestamps: {e}")
            raise MetadataError(f"Timestamp addition failed: {e}")

    def save_metadata(self) -> Path:
        """Save metadata to CSV file.
        
        Returns:
            Path to saved metadata file
            
        Raises:
            MetadataError: If save operation fails
        """
        try:
            self.to_data_frame()
            self._clean_parameters()
            self._validate_schema()
            self._add_dimensions()
            self._add_timestamps()
            self._validate_schema()
            
            output_path = self.path / self.config.output_file
            self.parameters.to_csv(output_path)
            self.logger.debug(f"Saved metadata to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            raise MetadataError(f"Metadata save failed: {e}")
