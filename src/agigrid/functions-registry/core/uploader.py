import os
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional, Callable
from uuid import uuid4

from .schema import FunctionEntry
from .policy import upload_policy_zip_bytes, onboard_policy_to_server

# Setup logger
logger = logging.getLogger("FunctionsS3Uploader")
logger.setLevel(logging.INFO)


class FunctionPolicyUploader:
  

    def __init__(
        self,
        assets_server_url: str,
        policy_server_url: str,
        save_function_callback: Callable[[FunctionEntry], None],
        remote_path: str = ".",                     
        timeout: Tuple[int, int] = (5, 60)       
    ):
        self.assets_server_url = assets_server_url.rstrip("/")
        self.policy_server_url = policy_server_url.rstrip("/")
        self.save_function_callback = save_function_callback
        self.remote_path = remote_path
        self.timeout = timeout

    def process_directory(self, function_dir: str) -> FunctionEntry:
      
        fn_json = os.path.join(function_dir, "function.json")
        fn_zip = os.path.join(function_dir, "function.zip")

        if not os.path.exists(fn_json):
            raise FileNotFoundError(f"Missing function.json at: {fn_json}")
        if not os.path.exists(fn_zip):
            raise FileNotFoundError(f"Missing function.zip at: {fn_zip}")

        # 1) Load function.json
        with open(fn_json, "r", encoding="utf-8") as f:
            raw = json.load(f)
        function = FunctionEntry.from_dict(raw)

        # Validate required fields
        if not function.function_name:
            raise ValueError("function_name is required in function.json")
        if not function.function_version:
            raise ValueError("function_version is required in function.json")
        if not function.function_release_tag:
            raise ValueError("function_release_tag is required in function.json")

        # 2) Generate function_id per spec (<name>:<version>-<release_tag>)
        function.generate_function_id()
        logger.info(f"Generated function_id: {function.function_id}")

        # 3) Upload function.zip with filename = uuid4().zip
        with open(fn_zip, "rb") as zf:
            file_bytes = zf.read()

        upload_filename = f"{uuid4()}.zip"
        ok, code_url_or_err = upload_policy_zip_bytes(
            file_bytes=file_bytes,
            filename=upload_filename,
            upload_endpoint=self.assets_server_url,
            remote_path=self.remote_path,
        )
        if not ok:
            raise RuntimeError(f"Upload failed: {code_url_or_err}")

        code_url = code_url_or_err
        logger.info(f"Assets server code URL: {code_url}")

        # Optionally store this on the function (not required but handy)
        function.function_code = code_url

        # 4) Onboard policy using function fields
        description = function.function_man_page_doc or function.function_search_description or ""
        policy_uri = onboard_policy_to_server(
            name=function.function_name,
            version=function.function_version,
            release_tag=function.function_release_tag,
            description=description,
            code_url=code_url,
            code_type="zip",
            policy_type="policy",
            metadata=function.function_metadata,
            tags=",".join(function.function_tags or []),
            policy_input_schema=function.function_input_schema,
            policy_output_schema=function.function_output_schema,
            policy_settings_schema=function.function_settings_schema,
            policy_parameters_schema=function.function_parameters_schema,
            policy_settings=function.function_settings,
            policy_parameters=function.function_parameters,
            functionality_data=function.function_api_spec or {},
            resource_estimates={},  # not present in FunctionEntry
            endpoint=self.policy_server_url,
        )

        logger.info(f"Onboarded policy URI: {policy_uri}")

        # 5) Update function with policy URI
        function.function_policy_rule_uri = policy_uri

        # 6) Persist function to DB
        try:
            self.save_function_callback(function)
            logger.info(f"Function saved: {function.function_id}")
        except Exception as e:
            logger.error(f"Failed to save function to DB: {e}")
            raise

        return function

