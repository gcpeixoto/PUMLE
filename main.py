import os

from src.pumle.pumle import Pumle


def set_root_path():
    return os.path.dirname(os.path.abspath(__file__))


CONFIG = {
    "root_path": set_root_path(),
    "selected_parameters": ["pres_ref", "temp_ref"],
    "variation_delta": 0.3,
    "save_metadata": True,
    "num_threads": 4,
    "saving_method": "numpy",  # or "zarr"
    "upload_to_s3": False,  # enable S3 upload
    "s3_config": {
        "bucket_name": "your-bucket-name",
        "aws_access_key": "YOUR_ACCESS_KEY",
        "aws_secret_key": "YOUR_SECRET_KEY",
        "region_name": "us-east-1",
    },
    "cache_path": "resources/cache",
    "clear_cache": True,
}


def main():
    pumle = Pumle(config=CONFIG)
    pumle.run(
        should_clean_older_files=True,
        layers_to_keep={
            "staging",
            "bronze_data",
            "silver_data",
            "golden_data",
        },
    )


if __name__ == "__main__":
    main()
