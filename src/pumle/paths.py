import os


class Paths:
    def __init__(
        self, path: str, grid_path: str = "benchmark/unisim-1-d/UNISIM_I_D_ECLIPSE.DATA"
    ):
        self.path: str = path
        self.grid_path: str = self.set_grid_path(grid_path)

    def set_grid_path(self, grid_path):
        grid_path_consolidated = (
            grid_path.replace("\\", "/") if os.name == "nt" else grid_path
        )
        return os.path.join(self.path, grid_path_consolidated.strip("/"))

    def get_path(self):
        return self.path

    def get_grid_path(self):
        return self.grid_path
