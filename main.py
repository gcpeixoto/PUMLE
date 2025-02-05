import os

from src.pumle.pumle import Pumle


def set_root_path():
    return os.path.dirname(os.path.abspath(__file__))


config = {
    "root_path": set_root_path(),
    "selected_parameters": ["pres_ref", "temp_ref"],
    "variation_delta": 0.2,
    "saving_method": "zarr",
}


def main():
    pumle = Pumle(config=config)
    pumle.run(clean_older_files=True)


if __name__ == "__main__":
    main()
