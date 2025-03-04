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
        # // MUDOU AQUI:
        # Em vez de staging_{sim_id}, usamos staging_{sim_hash}
        sim_hash = self.params["SimNums"]["sim_hash"]
        staging_folder = self.params["SimNums"]["staging_folder"]  # "staging_<hash>"

        mroot = os.path.join(
            self.params["Paths"]["PUMLE_ROOT"],
            "data_lake",
            "staging",
            staging_folder,
        )
        self._create_directory(mroot)

        # Agora, para cada seção, criamos um .mat com sufixo do "sim_hash"
        for section, content in self.params.items():
            # Exemplo: "Fluid_<hash>.mat", "Schedule_<hash>.mat", ...
            safe_section = section.replace("-", "").replace(" ", "")
            basename = f"{safe_section}_{sim_hash}"
            fname = os.path.join(mroot, f"{basename}.mat")
            try:
                savemat(fname, content, appendmat=True)
            except Exception as e:
                raise FileNotFoundError(
                    f"Failed to export matfile '{basename}.mat': {e}"
                )
