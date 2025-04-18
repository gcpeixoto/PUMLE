"""
Cloud storage operations for PUMLE simulations.
Handles S3 integration for data persistence.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

import boto3
from botocore.exceptions import (
    NoCredentialsError,
    ClientError,
    EndpointConnectionError
)


@dataclass
class S3Config:
    """Configuration for S3 operations."""
    bucket_name: str
    aws_access_key: str
    aws_secret_key: str
    region_name: str = "us-east-1"


class CloudStorageError(Exception):
    """Base exception for cloud storage operations."""
    pass


class CloudStorage:
    """Manages S3 operations for simulation data storage."""
    
    def __init__(
        self,
        bucket_name: str,
        aws_access_key: str,
        aws_secret_key: str,
        region_name: str = "us-east-1",
    ) -> None:
        """Initialize the cloud storage manager.
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key: AWS access key ID
            aws_secret_key: AWS secret access key
            region_name: AWS region name
            
        Raises:
            CloudStorageError: If S3 client initialization fails
        """
        self._setup_logger()
        self.config = S3Config(
            bucket_name=bucket_name,
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            region_name=region_name
        )
        self._init_s3_client()
        
    def _setup_logger(self) -> None:
        """Configure logging for the cloud storage manager."""
        self.logger = logging.getLogger("pumle.cloud_storage")
        self.logger.setLevel(logging.DEBUG)
        
    def _init_s3_client(self) -> None:
        """Initialize the S3 client.
        
        Raises:
            CloudStorageError: If client initialization fails
        """
        try:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.config.aws_access_key,
                aws_secret_access_key=self.config.aws_secret_key,
                region_name=self.config.region_name
            )
            self.logger.info("S3 client initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            raise CloudStorageError(f"S3 client initialization failed: {e}")
            
    def _validate_file(self, file_path: Path) -> None:
        """Validate file existence and permissions.
        
        Args:
            file_path: Path to the file to validate
            
        Raises:
            CloudStorageError: If file validation fails
        """
        if not file_path.exists():
            raise CloudStorageError(f"File not found: {file_path}")
            
        if not file_path.is_file():
            raise CloudStorageError(f"Path is not a file: {file_path}")
            
        if not os.access(file_path, os.R_OK):
            raise CloudStorageError(f"No read permission for file: {file_path}")
            
    def upload_file(
        self,
        file_path: str,
        s3_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Upload a file to S3.
        
        Args:
            file_path: Local path to the file
            s3_path: Destination path in S3
            metadata: Optional metadata to attach to the file
            
        Raises:
            CloudStorageError: If upload fails
        """
        file_path = Path(file_path)
        self._validate_file(file_path)
        
        try:
            extra_args = {"Metadata": metadata} if metadata else {}
            self.s3_client.upload_file(
                str(file_path),
                self.config.bucket_name,
                s3_path,
                ExtraArgs=extra_args
            )
            self.logger.info(
                f"Upload successful: {file_path} -> "
                f"s3://{self.config.bucket_name}/{s3_path}"
            )
        except NoCredentialsError:
            self.logger.error("AWS credentials not available")
            raise CloudStorageError("AWS credentials not available")
        except ClientError as e:
            self.logger.error(f"S3 client error: {e}")
            raise CloudStorageError(f"S3 upload failed: {e}")
        except EndpointConnectionError as e:
            self.logger.error(f"S3 connection error: {e}")
            raise CloudStorageError(f"S3 connection failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            raise CloudStorageError(f"Upload failed: {e}")
            
    def download_file(self, s3_path: str, local_path: str) -> None:
        """Download a file from S3.
        
        Args:
            s3_path: Source path in S3
            local_path: Local destination path
            
        Raises:
            CloudStorageError: If download fails
        """
        local_path = Path(local_path)
        
        try:
            self.s3_client.download_file(
                self.config.bucket_name,
                s3_path,
                str(local_path)
            )
            self.logger.info(
                f"Download successful: s3://{self.config.bucket_name}/{s3_path} -> "
                f"{local_path}"
            )
        except ClientError as e:
            self.logger.error(f"S3 client error: {e}")
            raise CloudStorageError(f"S3 download failed: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {e}")
            raise CloudStorageError(f"Download failed: {e}")
            
    def list_files(self, prefix: str = "") -> list:
        """List files in the S3 bucket.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            list: List of file keys
            
        Raises:
            CloudStorageError: If listing fails
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.bucket_name,
                Prefix=prefix
            )
            files = [obj["Key"] for obj in response.get("Contents", [])]
            self.logger.debug(f"Found {len(files)} files with prefix '{prefix}'")
            return files
        except Exception as e:
            self.logger.error(f"Failed to list files: {e}")
            raise CloudStorageError(f"Failed to list files: {e}")
