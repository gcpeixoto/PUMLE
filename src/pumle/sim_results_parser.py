import os
import numpy as np

from typing import Tuple
from src.pumle.utils import convert_ndarray, read_json, write_json


class SimResultsParser:
    def __init__(self, result_folder, sim_hash):
        self.result_folder: str = result_folder
        self.sim_hash: str = sim_hash
        self.field_to_infer_id_max: str = "states"
        self.dimensions_field: str = "g"

    def _get_json_name(self, sim_type: str, sim_id: int = 1):
        return (
            f"{sim_type}_GCS01_{sim_id}.json"
            if sim_type != self.dimensions_field
            else f"{self.dimensions_field}_GCS01.json"
        )

    def get_dimensions(self) -> Tuple[int, int, int]:
        json_path = os.path.join(
            self.result_folder, self._get_json_name(self.dimensions_field)
        )
        i, j, k = read_json(json_path)
        return i, j, k

    def get_active_cells(self):
        active_cel = read_json(
            os.path.join(
                self.result_folder, self._get_json_name("grdecl", self.sim_hash)
            )
        )

        idx_to_get = np.where(active_cel)[0]
        return active_cel, idx_to_get

    def get_states(self, parameter):
        states = read_json(
            os.path.join(
                self.result_folder, self._get_json_name("states", self.sim_hash)
            )
        )
        parameters = [state[parameter] for state in states]
        return parameters

    def get_all(self):
        dimensions = self.get_dimensions()
        active_cells, idx_to_get = self.get_active_cells()
        pressure = self.get_states("pressure")
        s = self.get_states("s")  # saturation
        result = {
            "dimensions": dimensions,
            "active_cells": active_cells,
            "idx_to_get": idx_to_get,
            "pressure": pressure,
            "saturation": s,
        }
        self.dimensions = dimensions
        return convert_ndarray(result)

    def all_data(self):
        all_data = []
        for i in range(1, self.max_sim_id + 1):
            data = self.get_all(i - 1)
            all_data.append(data)
        return all_data

    def save_all(self, path):
        os.makedirs(path, exist_ok=True)
        for i in range(1, self.max_sim_id + 1):
            path_consolidated = os.path.join(path, f"GCS01_{i}.json")
            data = self.get_all(i - 1)
            write_json(path_consolidated, data)
