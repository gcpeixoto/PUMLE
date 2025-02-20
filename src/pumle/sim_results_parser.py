import os
import numpy as np

from typing import Tuple
from src.pumle.utils import convert_ndarray, read_json, write_json


class SimResultsParser:
    def __init__(self, result_folder):
        self.result_folder: str = result_folder
        self.field_to_infer_id_max: str = "states"
        self.dimensions_field: str = "g"
        self.max_sim_id = self._get_sim_id_max()

    def _get_json_name(self, sim_type: str, sim_id: int = 1):
        return (
            f"{sim_type}_GCS01_{sim_id}.json"
            if sim_type != self.dimensions_field
            else f"{self.dimensions_field}_GCS01.json"
        )

    def _get_sim_id_max(self):
        sim_id = 0
        while True:
            json_file_name = self._get_json_name(self.field_to_infer_id_max, sim_id + 1)
            json_path = os.path.join(self.result_folder, json_file_name)
            if not os.path.exists(json_path):
                break
            sim_id += 1
        return sim_id

    def get_dimensions(self) -> Tuple[int, int, int]:
        json_path = os.path.join(
            self.result_folder, self._get_json_name(self.dimensions_field)
        )
        i, j, k = read_json(json_path)
        return i, j, k

    def get_active_cells(self):
        active_cels = [
            read_json(
                os.path.join(self.result_folder, self._get_json_name("grdecl", i))
            )
            for i in range(1, self.max_sim_id + 1)
        ]
        idx_to_get = [np.where(active_cel)[0] for active_cel in active_cels]
        return active_cels, idx_to_get

    def get_states(self, parameter):
        all_states = [
            read_json(
                os.path.join(self.result_folder, self._get_json_name("states", i))
            )
            for i in range(1, self._get_sim_id_max() + 1)
        ]
        all_parameters = []
        for states in all_states:
            parameters = [state[parameter] for state in states]
            all_parameters.append(parameters)
        return all_parameters

    def get_all(self, sim_id: int):
        dimensions = self.get_dimensions()
        active_cells, idx_to_get = self.get_active_cells()
        pressure = self.get_states("pressure")
        s = self.get_states("s")  # saturation
        result = {
            "dimensions": dimensions,
            "active_cells": active_cells[sim_id],
            "idx_to_get": idx_to_get[sim_id],
            "pressure": pressure[sim_id],
            "saturation": s[sim_id],
        }
        self.dimensions = dimensions
        return convert_ndarray(result)

    def save_all(self, path):
        os.makedirs(path, exist_ok=True)
        for i in range(1, self.max_sim_id + 1):
            path_consolidated = os.path.join(path, f"GCS01_{i}.json")
            data = self.get_all(i - 1)
            write_json(path_consolidated, data)
