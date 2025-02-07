import zarr
import numpy as np
import pandas as pd


class Tabular:
    def __init__(self):
        self.file_structure = "zarr"

    def read_data(self, path):
        if self.file_structure == "zarr":
            data = zarr.open(path, mode="r")
        elif self.file_structure == "npy":
            data = np.load(path)
        self.data = data

    def structute_data(self, data):
        first_iteration = True

        for sim_id in range(data.shape[4]):
            for i in range(data.shape[3]):
                x, y, z = data[:, :, :, i, sim_id].nonzero()
                values = data[x, y, z, i, sim_id]

                data = {
                    "simulation": sim_id,
                    "timestamp": i,
                    "x": x,
                    "y": y,
                    "z": z,
                    "values": values,
                }

                if first_iteration:
                    df = pd.DataFrame(data)
                    first_iteration = False
                else:
                    df = pd.concat([df, pd.DataFrame(data)], ignore_index=True)

        self.data = df

    def save_data(self, path):
        self.data.to_parquet(path)

    def save_to_postgress(self, table_name, connection):
        self.data.to_sql(table_name, connection, if_exists="replace")
