from src.pumle.utils import read_json
import os
import numpy as np
import zarr
from typing import Tuple, List


class Arrays:
    def __init__(self, input_data_path, output_data_path):
        self.input_data_path: str = input_data_path
        self.output_data_path: str = output_data_path
        self.number_of_inputs: int = self._get_number_of_inputs()

    def _get_number_of_inputs(self):
        return len(os.listdir(self.input_data_path))

    def read_jsons(self) -> List:
        structures = [
            read_json(os.path.join(self.input_data_path, f"GCS01_{sim_id}.json"))
            for sim_id in range(1, self.number_of_inputs + 1)
        ]
        return structures

    def consolidate_data(self, structure) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        i, j, k = structure["dimensions"]
        ts = len(structure["saturation"])
        idx_to_get = structure["idx_to_get"]
        ncells_total = np.prod([i, j, k])
        p = np.zeros((ncells_total, ts))
        sw = np.zeros((ncells_total, ts))
        sg = np.zeros((ncells_total, ts))

        for t in range(ts):
            p[idx_to_get, t] = np.array(structure["pressure"][t]).reshape(
                -1,
            )
            sw[idx_to_get, t] = np.array(structure["saturation"][t])[:, 0].reshape(
                -1,
            )
            sg[idx_to_get, t] = np.array(structure["saturation"][t])[:, 1].reshape(
                -1,
            )

        p = p.reshape((i, j, k, ts))
        sw = sw.reshape((i, j, k, ts))
        sg = sg.reshape((i, j, k, ts))

        self.timestamps = ts

        return p, sw, sg

    def consolidate_all_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Consolidate all data from the json files in the input_data_path

        """
        structures = self.read_jsons()

        p_list = []
        sw_list = []
        sg_list = []
        for structure in structures:
            p, sw, sg = self.consolidate_data(structure)
            p_list.append(p)
            sw_list.append(sw)
            sg_list.append(sg)

        return (
            np.stack(p_list, axis=4),
            np.stack(sw_list, axis=4),
            np.stack(sg_list, axis=4),
        )

    def save_npy(self, name, data) -> None:
        np.save(os.path.join(self.output_data_path, f"{name}.npy"), data)

    def save_zarr(self, name, data) -> None:
        z = zarr.open(
            os.path.join(self.output_data_path, f"{name}.zarr"),
            mode="w",
            shape=data.shape,
            dtype=data.dtype,
        )
        z[:] = data

    def save_golden_data(self, saving_method="default"):
        """
        Save consolidated data to the output_data_path

        Parameters:
        saving_method (str): The method to save the data. Options are "numpy" or "json".
        """
        if saving_method == "default":
            saving_method = "numpy"

        p, sw, sg = self.consolidate_all_data()

        to_save = {
            "pressure": p,
            "sw": sw,
            "sg": sg,
        }

        save_engine = {
            "numpy": self.save_npy,
            "zarr": self.save_zarr,
        }

        fn = save_engine.get(saving_method.strip().lower())

        if fn:
            if not os.path.exists(self.output_data_path):
                os.makedirs(self.output_data_path)
            for name, data in to_save.items():
                fn(name, data)
        else:
            raise ValueError("saving_method must be 'numpy' or 'zarr'")
