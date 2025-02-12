import os
import zarr
import numpy as np
import pandas as pd


class Tabular:
    def __init__(self, input_data_path, output_data_path, input_structure, attr="sg"):
        self.input_data_path: str = input_data_path
        self.output_data_path: str = output_data_path
        self.input_structure = input_structure
        self.attr = attr

    def read_data(self):
        if self.input_structure == "zarr":
            data = zarr.open(
                os.path.join(self.input_data_path, self.attr + ".zarr"), mode="r"
            )
        elif self.input_structure == "numpy" or self.input_structure is None:
            data = np.load(os.path.join(self.input_data_path, self.attr + ".npy"))
        else:
            raise ValueError("Invalid input structure")
        self.data = data

    def structute_data(self):
        first_iteration = True
        number_of_simulations = self.data.shape[4]
        number_of_times = self.data.shape[3]
        for sim_id in range(number_of_simulations):
            for i in range(number_of_times):
                x, y, z = self.data[:, :, :, i, sim_id].nonzero()
                values = self.data[x, y, z, i, sim_id]
                data_df = {
                    "simulation": sim_id,
                    "timestamp": i,
                    "x": x,
                    "y": y,
                    "z": z,
                    "values": values,
                }
                if first_iteration:
                    df = pd.DataFrame(data_df)
                    first_iteration = False
                else:
                    df = pd.concat([df, pd.DataFrame(data_df)], ignore_index=True)
        self.data = df

    def save_data(self):
        if not os.path.exists(self.output_data_path):
            os.makedirs(self.output_data_path)
        self.data.to_csv(os.path.join(self.output_data_path, self.attr + ".csv"))
