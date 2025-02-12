import boto3
from botocore.exceptions import NoCredentialsError

class CloudStorage:
    def __init__(self, bucket_name: str, aws_access_key: str, aws_secret_key: str, region_name: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=region_name,
        )

    def upload_file(self, file_path: str, s3_path: str) -> None:
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_path)
            print(f"Upload successful: {file_path} -> s3://{self.bucket_name}/{s3_path}")
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except NoCredentialsError:
            print("AWS credentials not available.")
