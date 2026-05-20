import boto3
import logging
from typing import IO, Dict
import requests

logger = logging.getLogger("S3UploaderPlugin")
logger.setLevel(logging.INFO)

class S3UploaderPlugin:
    def __init__(self, bucket_name: str, prefix: str = "", region_name: str = "us-east-1", public: bool = False):
        self.bucket = bucket_name
        self.prefix = prefix.strip("/")
        self.public = public
        self.s3 = boto3.client("s3", region_name=region_name)

    def upload_file(self, filename: str, file_obj: IO[bytes]) -> str:
        
        key = f"{self.prefix}/{filename}" if self.prefix else filename
        try:
            logger.info(f"[S3Uploader] Uploading to bucket={self.bucket}, key={key}")
            self.s3.upload_fileobj(file_obj, self.bucket, key)

            if self.public:
                url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
            else:
                url = f"s3://{self.bucket}/{key}"

            logger.info(f"[S3Uploader] Uploaded: {url}")
            return url

        except Exception as e:
            logger.error(f"[S3Uploader] Upload failed: {e}")
            raise


class S3DownloaderPlugin:
    def download_file(self, url: str) -> IO[bytes]:
        logger.info(f"[S3Downloader] Downloading: {url}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        return response.raw 