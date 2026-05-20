import os
import json
import zipfile
import tempfile
import logging
from typing import Optional
from .schema import FunctionEntry
from .crud import FunctionsRegistryCRUD
from .uploader import FunctionsS3Uploader

logger = logging.getLogger("FunctionPackageParser")
logger.setLevel(logging.INFO)


class FunctionPackageParser:
    def __init__(self, s3_uploader: FunctionsS3Uploader, registry_crud: FunctionsRegistryCRUD):
        self.s3_uploader = s3_uploader
        self.registry_crud = registry_crud

    def process_zip_package(self, zip_path: str) -> Optional[str]:
        if not os.path.exists(zip_path):
            logger.error(f"Provided ZIP file does not exist: {zip_path}")
            return None

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                logger.info(f"Extracted function zip to: {temp_dir}")

                # Locate required files
                spec_path = os.path.join(temp_dir, "spec.json")
                func_bin_path = os.path.join(temp_dir, "function.zip")
                man_page_path = os.path.join(temp_dir, "function.md")

                if not (os.path.exists(spec_path) and os.path.exists(func_bin_path) and os.path.exists(man_page_path)):
                    logger.error("One or more required files are missing in the ZIP archive.")
                    return None

                with open(spec_path, "r") as f:
                    spec_data = json.load(f)

                if "function_id" not in spec_data:
                    logger.error("spec.json must contain 'function_id'.")
                    return None

                function_id = spec_data["function_id"]
                s3_key = f"{function_id}/function.zip"

                # Upload function.zip
                public_url = self.s3_uploader.upload_function_file(func_bin_path, s3_key)
                if not public_url:
                    logger.error("Failed to upload function.zip to S3.")
                    return None

                spec_data["function_source_code_link"] = public_url

                with open(man_page_path, "r") as f:
                    spec_data["function_man_page_doc"] = f.read()

                function_entry = FunctionEntry.from_dict(spec_data)
                inserted = self.registry_crud.create_function(function_entry)

                if inserted:
                    logger.info(f"Function '{function_id}' registered successfully.")
                    return function_id
                else:
                    logger.warning(f"Function '{function_id}' already exists or failed to insert.")
                    return None

        except Exception as e:
            logger.error(f"Exception while processing function ZIP: {e}")
            return None
