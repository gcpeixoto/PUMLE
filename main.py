import os
from pumle import Pumle


def set_root_path():
    return os.path.dirname(os.path.abspath(__file__))


CONFIG = {
    "root_path": set_root_path(),
    "selected_parameters": ["pres_ref"],
    "variation_delta": 0.3,
    "save_metadata": False,
    "num_threads": 4,
    "saving_method": "numpy",  # or "zarr"
    "upload_to_s3": False,  # enable S3 upload
    "s3_config": {
        "bucket_name": "your-bucket-name",
        "aws_access_key": "YOUR_ACCESS_KEY",
        "aws_secret_key": "YOUR_SECRET_KEY",
        "region_name": "us-east-1",
    },
    "parameters_variation_cache": os.path.join(
        set_root_path(), "resources/parameters_cache.json"
    ),
}


def main():
    pumle = Pumle(config=CONFIG)
    pumle.run(
        should_clean_older_files=True, layers_to_keep={"golden_data", "tabular_data"}
    )


if __name__ == "__main__":
    main()
