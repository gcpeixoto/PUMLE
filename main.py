import os

from src.pumle.pumle import Pumle


def set_root_path():
    return os.path.dirname(os.path.abspath(__file__))


config = {
    "root_path": set_root_path(),
    "selected_parameters": ["pres_ref"],
    "variation_delta": 0.3,
    "save_metadata": False,
    "num_threads": 4,
}


def main():
    pumle = Pumle(config=config)
    pumle.run(should_clean_older_files=True, layers_to_keep={"golden_data"})


if __name__ == "__main__":
    main()
