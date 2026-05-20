import zipfile
import tempfile
import os
import uuid
from redis import Redis
import threading
import shutil
import traceback
import requests
import boto3
from typing import Tuple, Dict, Union, Optional, IO, Any, BinaryIO

from .registry_db import CreateRegistryController

class ZipReader:
    @staticmethod
    def extract(zip_file: Union[str, IO[bytes]], filter_dirs: Optional[list] = None) -> Tuple[str, Dict[str, str]]:
       
        if isinstance(zip_file, str):
            zf = zipfile.ZipFile(zip_file, 'r')
        else:
            zf = zipfile.ZipFile(zip_file)

        temp_dir = tempfile.mkdtemp(prefix="registry_zip_")
        file_map = {}

        for member in zf.infolist():
            if member.is_dir():
                continue

            # Optional filtering by root directory (e.g., docs/, sdk/)
            if filter_dirs:
                if not any(member.filename.startswith(prefix) for prefix in filter_dirs):
                    continue

            extracted_path = zf.extract(member, path=temp_dir)
            logical_path = member.filename
            file_map[logical_path] = os.path.abspath(extracted_path)

        zf.close()
        return temp_dir, file_map


class S3UploaderPlugin:
    def __init__(self, bucket_name: str, s3_prefix: str = ""):
        self.bucket = bucket_name
        self.prefix = s3_prefix.rstrip("/")
        self.s3 = boto3.client("s3")

    def upload_files(self, file_map: Dict[str, str]) -> Dict[str, str]:
       
        s3_urls = {}

        for logical_path, local_path in file_map.items():
            s3_key = f"{self.prefix}/{logical_path}".replace("\\", "/")
            try:
                self.s3.upload_file(local_path, self.bucket, s3_key)
                s3_url = f"https://{self.bucket}.s3.amazonaws.com/{s3_key}"
                s3_urls[logical_path] = s3_url
            except Exception as e:
                raise RuntimeError(f"Failed to upload {logical_path} to S3: {e}")

        return s3_urls

class AssetsDBClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def register_assets(self, registry_id: str, s3_links: Dict[str, str], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/assets/register"

        payload = {
            "registry_id": registry_id,
            "assets": [{"path": k, "s3_url": v} for k, v in s3_links.items()],
        }

        if metadata:
            payload["metadata"] = metadata

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to register assets: {e}")


class UploadZipAPI:
    def __init__(self,
                 controller: CreateRegistryController,
                 redis_client: Redis,
                 s3_bucket: str,
                 s3_prefix_root: str,
                 assets_db_url: str):
        self.controller = controller
        self.redis = redis_client
        self.s3_bucket = s3_bucket
        self.s3_prefix_root = s3_prefix_root
        self.assets_db = AssetsDBClient(assets_db_url)

    def upload(self, registry_spec: Dict[str, Any], zip_file: BinaryIO) -> str:
        task_id = str(uuid.uuid4())
        self.redis.set(f"UPLOAD_STATUS:{task_id}", "pending")

        # Background thread
        thread = threading.Thread(target=self._process_upload, args=(task_id, registry_spec, zip_file))
        thread.start()
        return task_id

    def _process_upload(self, task_id: str, registry_spec: Dict[str, Any], zip_file: BinaryIO):
        try:
            registry_id = registry_spec.get("registry_id")
            self.redis.set(f"UPLOAD_STATUS:{task_id}", "validating")

            # Validate spec
            registry_obj = self.controller.create(registry_spec)  # this includes DB write

            # Extract files
            self.redis.set(f"UPLOAD_STATUS:{task_id}", "extracting")
            temp_dir, file_map = ZipReader.extract(zip_file, filter_dirs=["docs/", "sdk/"])

            # Upload to S3
            self.redis.set(f"UPLOAD_STATUS:{task_id}", "uploading")
            uploader = S3UploaderPlugin(bucket_name=self.s3_bucket, s3_prefix=f"{self.s3_prefix_root}/{registry_id}")
            s3_links = uploader.upload_files(file_map)

            # Register to Assets DB
            self.redis.set(f"UPLOAD_STATUS:{task_id}", "registering")
            self.assets_db.register_assets(registry_id, s3_links)

            # Cleanup
            shutil.rmtree(temp_dir)
            self.redis.set(f"UPLOAD_STATUS:{task_id}", "done")

        except Exception as e:
            tb = traceback.format_exc()
            self.redis.set(f"UPLOAD_STATUS:{task_id}", f"error: {str(e)}\n{tb}")