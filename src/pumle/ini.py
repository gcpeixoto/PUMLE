import configparser
import os

from typing import Dict, List, Tuple
from src.pumle.paths import Paths


class Ini:
    def __init__(
        self,
        root_path: str,
        path: str,
        sections_schema: Dict[str, Tuple[List[str], bool]],
        cast_bool_params: bool = False,
    ) -> None:
        self.path: str = path
        self.sections_schema: Dict[str, Tuple[List[str], bool]] = sections_schema
        self.cast_bool_params: bool = cast_bool_params
        self._validate_config_file()
        self.load(root_path)

    def _validate_config_file(self) -> None:
        if not os.path.isfile(self.path):
            raise FileNotFoundError(f"Configuration file '{self.path}' not found.")

    def load(self, root_path: str) -> None:
        config = configparser.ConfigParser()
        config.read(self.path)
        params_aux = {}
        for section, (params, cast_to_float) in self.sections_schema.items():
            if not config.has_section(section):
                params_aux[section] = {}
                continue
            section_params = {}
            for param in params:
                try:
                    value = config.get(section, param)
                    if cast_to_float:
                        value = float(value)
                    elif self.cast_bool_params and param.endswith("_flag"):
                        value = bool(value)
                    section_params[param] = value
                except (configparser.NoOptionError, ValueError) as e:
                    raise ValueError(
                        f"Error reading parameter '{param}' from section '{section}': {e}"
                    )
            params_aux[section] = section_params
        self.params: dict = params_aux
        self.get_paths(root_path)

    def get_paths(self, root_path: str) -> None:
        path = Paths(root_path)

        self.params["Paths"]["PUMLE_ROOT"] = path.get_path()
        self.params["Grid"]["file_path"] = path.get_grid_path()

    def get_params(self) -> dict:
        return self.params

    def __repr__(self):
        return f"Parameters: {self.params}"
