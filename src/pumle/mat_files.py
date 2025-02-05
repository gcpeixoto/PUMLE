import os
from scipy.io import savemat


class MatFiles:
    def __init__(self, params: dict):
        self.params: dict = params
        self._validate_params()

    def _validate_params(self) -> None:
        """Validate required parameters are present."""
        required_keys = ["Paths", "EXECUTION", "Fluid", "Pre-Processing", "SimNums"]
        for key in required_keys:
            if key not in self.params:
                raise ValueError(f"Missing required parameter: {key}")

    def _create_directory(self, path: str) -> None:
        """Create a directory if it does not exist."""
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            raise FileNotFoundError(f"Failed to create directory '{path}': {e}")

    def write(
        self,
    ):
        """Export dict of simulation parameters to matfile to be read individually."""
        sim_id = int(self.params["SimNums"]["sim_id"])

        mroot = os.path.join(
            self.params["Paths"]["PUMLE_ROOT"],
            "data_lake",
            "mat_files",
            f"mat_files_{sim_id}",
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
                    "Failed to export matfile file '{basename}.mat': {e}"
                )
