import os
from scipy.io import savemat


class MatFiles:
    def __init__(self, params: dict):
        self.params: dict = params
        self._validate_params()

    def _validate_params(self) -> None:
        required_keys = ["Paths", "EXECUTION", "Fluid", "Pre-Processing", "SimNums"]
        for key in required_keys:
            if key not in self.params:
                raise ValueError(f"Missing required parameter: {key}")

    def _create_directory(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)

    def write(self):
        sim_id = int(self.params["SimNums"]["sim_id"])
        mroot = os.path.join(
            self.params["Paths"]["PUMLE_ROOT"],
            "data_lake",
            "pre_bronze",
            f"pre_bronze_{sim_id}",
        )
        self._create_directory(mroot)
        for section, content in self.params.items():
            basename = (
                f"{section.replace('-', '').replace(' ', '')}ParamsPUMLE_{sim_id}"
            )
            fname = os.path.join(mroot, f"{basename}.mat")
            try:
                savemat(fname, content, appendmat=True)
            except Exception as e:
                raise FileNotFoundError(
                    f"Failed to export matfile '{basename}.mat': {e}"
                )
