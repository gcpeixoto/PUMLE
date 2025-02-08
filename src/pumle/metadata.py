import pandas as pd
import os

from functools import reduce

import pandera as pa

base_chema = pa.DataFrameSchema(
    {
        "sim_id": pa.Column(str, checks=pa.Check.str_matches(r"^\d+$"), nullable=False),
        "fluid__pres_ref": pa.Column(float, checks=pa.Check.gt(0), nullable=False),
        "fluid__temp_ref": pa.Column(float, checks=pa.Check.gt(0), nullable=False),
        "fluid__cp_rock": pa.Column(float, checks=pa.Check.gt(0), nullable=False),
        "fluid__srw": pa.Column(float, checks=pa.Check.in_range(0, 1), nullable=False),
        "fluid__src": pa.Column(float, checks=pa.Check.in_range(0, 1), nullable=False),
        "fluid__pe": pa.Column(float, checks=pa.Check.gt(0), nullable=False),
        "fluid__xnacl": pa.Column(float, checks=pa.Check.ge(0), nullable=False),
        "fluid__rho_h2o": pa.Column(float, checks=pa.Check.gt(0), nullable=False),
        "initial_conditions__sw_0": pa.Column(
            float, checks=pa.Check.in_range(0, 1), nullable=False
        ),
        "boundary_conditions__type": pa.Column(str, nullable=False),
        "wells__co2_inj": pa.Column(float, checks=pa.Check.gt(0), nullable=False),
        "schedule__injection_time": pa.Column(
            int, checks=pa.Check.gt(0), nullable=False
        ),
        "schedule__migration_time": pa.Column(
            int, checks=pa.Check.gt(0), nullable=False
        ),
        "schedule__injection_timesteps": pa.Column(
            int, checks=pa.Check.gt(0), nullable=False
        ),
        "schedule__migration_timesteps": pa.Column(
            int, checks=pa.Check.gt(0), nullable=False
        ),
    }
)


class Metadata:
    def __init__(self, path):
        self.path = path
        self.parameters_id = "sim_id"
        self.schema = base_chema
        self.parameters = None
        self.base_schema = None
        self.dimensions = None
        self.timestamps = None

    def get_data(self, **kwargs) -> None:
        self.parameters = (
            kwargs.get("parameters") if self.parameters is None else self.parameters
        )
        self.base_schema = (
            kwargs.get("base_schema") if self.base_schema is None else self.base_schema
        )
        self.dimensions = (
            kwargs.get("dimensions") if self.dimensions is None else self.dimensions
        )
        self.timestamps = (
            kwargs.get("timestamps") if self.timestamps is None else self.timestamps
        )

    def to_data_frame(self) -> None:
        self.parameters = pd.DataFrame(self.parameters)

    def save_bronze_data(self) -> None:
        self.to_data_frame()
        self.parameters.reset_index().to_csv(
            os.path.join(self.path, "bronze_metadata.csv")
        )

    def _format_column_name(self, *column_name):
        clear = lambda x: x.replace(" ", "_").replace("-", "_").lower()

        return reduce(lambda x, y: clear(x) + "__" + clear(y), column_name)

    def _cast_columns(self, df, columns, dtype):
        for column in columns:
            df[column] = df[column].astype(dtype)

    def _cast_base_cols(self):
        self._cast_columns(self.parameters, ["sim_id"], str)
        self._cast_columns(
            self.parameters,
            [
                "schedule__injection_time",
                "schedule__migration_time",
                "schedule__injection_timesteps",
                "schedule__migration_timesteps",
            ],
            int,
        )
        self._cast_columns(
            self.parameters,
            [
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
            ],
            float,
        )

    def clean_parameters(self) -> None:
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
                values if isinstance(values[0], dict) else list(map(eval, values))
            )

            for child_field in child_fields:
                values = [value[child_field] for value in values_extracted]
                if child_field == self.parameters_id:
                    self.parameters[child_field] = values
                else:
                    self.parameters[
                        self._format_column_name(main_field, child_field)
                    ] = values

        self.parameters.drop(columns=columns_to_drop, inplace=True)
        self._cast_base_cols()

    def validate_schema(self) -> None:
        self.schema.validate(self.parameters)

    def add_dimensions(self) -> None:
        self.parameters["dimension_x"] = self.dimensions[0]
        self.parameters["dimension_y"] = self.dimensions[1]
        self.parameters["dimension_z"] = self.dimensions[2]

        self._cast_columns(
            self.parameters, ["dimension_x", "dimension_y", "dimension_z"], int
        )

        dimensions_schema = {
            "dimension_x": pa.Column(int, checks=pa.Check.gt(0), nullable=False),
            "dimension_y": pa.Column(int, checks=pa.Check.gt(0), nullable=False),
            "dimension_z": pa.Column(int, checks=pa.Check.gt(0), nullable=False),
        }

        self.schema.add_columns(dimensions_schema)

    def add_timestamps(self) -> None:
        self.parameters["timestamps"] = self.timestamps

        self._cast_columns(self.parameters, ["timestamps"], int)

        timestamps_schema = {
            "timestamps": pa.Column(int, checks=pa.Check.gt(0), nullable=False),
        }

        self.schema.add_columns(timestamps_schema)

    def save_silver_data(self) -> None:
        self.clean_parameters()
        self.validate_schema()
        self.parameters.to_csv(os.path.join(self.path, "silver_metadata.csv"))

    def save_golden_data(self) -> None:
        self.add_dimensions()
        self.add_timestamps()
        self.validate_schema()
        self.parameters.to_csv(os.path.join(self.path, "golden_metadata.csv"))
