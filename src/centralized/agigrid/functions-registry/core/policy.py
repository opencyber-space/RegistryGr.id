import requests
import logging
import os
from typing import Tuple

logger = logging.getLogger(__name__)

POLICY_SERVER_URL=os.getenv("POLICY_DB_URL", "http://34.58.1.86:30102")
ASSETS_SERVER_URL=os.getenv("ASSETS_SERVER_URL", "http://34.68.117.250:30186")


def upload_policy_zip_bytes(
    file_bytes: bytes,
    filename: str,
    upload_endpoint: str = ASSETS_SERVER_URL,
    remote_path: str = "."
) -> Tuple[bool, str]:
 
    try:
        files = {
            "file": (filename, file_bytes, "application/zip"),
            "path": (None, remote_path)
        }
        response = requests.post(upload_endpoint + "/upload", files=files)

        response.raise_for_status()

        # Expecting JSON with uploaded URL
        result = response.json()
        code_url = result.get("url") or result.get("path") or response.text
        logger.info(f"Uploaded {filename} successfully to {code_url}")
        return True, code_url

    except Exception as e:
        logger.error(f"Upload failed for {filename}: {e}")
        return False, str(e)


def onboard_policy_to_server(
    name: str,
    version: str,
    release_tag: str,
    description: str,
    code_url: str,
    code_type: str = "tar.xz",
    policy_type: str = "policy",
    metadata: dict = None,
    tags: str = "",
    policy_input_schema: dict = None,
    policy_output_schema: dict = None,
    policy_settings_schema: dict = None,
    policy_parameters_schema: dict = None,
    policy_settings: dict = None,
    policy_parameters: dict = None,
    functionality_data: dict = None,
    resource_estimates: dict = None,
    endpoint: str = POLICY_SERVER_URL
) -> str:

    payload = {
        "name": name,
        "version": version,
        "release_tag": release_tag,
        "metadata": metadata or {},
        "tags": tags,
        "code": code_url,
        "code_type": code_type,
        "type": policy_type,
        "policy_input_schema": policy_input_schema or {},
        "policy_output_schema": policy_output_schema or {},
        "policy_settings_schema": policy_settings_schema or {},
        "policy_parameters_schema": policy_parameters_schema or {},
        "policy_settings": policy_settings or {},
        "policy_parameters": policy_parameters or {},
        "description": description,
        "functionality_data": functionality_data or {},
        "resource_estimates": resource_estimates or {}
    }

    try:
        response = requests.post(endpoint + "/policy", json=payload)
        response.raise_for_status()
        logger.info(f"Policy onboarded: {name}:{version}-{release_tag}")
        return f"{name}:{version}-{release_tag}"
    except Exception as e:
        logger.error(f"Failed to onboard policy: {e}")
        raise

