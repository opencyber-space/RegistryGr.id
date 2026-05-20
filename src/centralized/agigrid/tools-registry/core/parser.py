import os
import json
import zipfile
import tempfile
import logging
from typing import Optional
from .schema import ToolEntry
from .crud import ToolsRegistryCRUD
from .uploader import S3Uploader

logger = logging.getLogger("ToolPackageParser")
logger.setLevel(logging.INFO)


class ToolPackageParser:
    def __init__(self, s3_uploader: S3Uploader, registry_crud: ToolsRegistryCRUD):
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
                logger.info(f"Extracted zip to: {temp_dir}")

                # Locate required files
                spec_path = os.path.join(temp_dir, "spec.json")
                tool_bin_path = os.path.join(temp_dir, "tool.zip")
                man_page_path = os.path.join(temp_dir, "tool.md")

                if not (os.path.exists(spec_path) and os.path.exists(tool_bin_path) and os.path.exists(man_page_path)):
                    logger.error(
                        "One or more required files are missing in the ZIP archive.")
                    return None

                with open(spec_path, "r") as f:
                    spec_data = json.load(f)

                if "tool_id" not in spec_data:
                    logger.error("spec.json must contain 'tool_id'.")
                    return None

                tool_id = spec_data["tool_id"]
                s3_key = f"{tool_id}/tool.zip"

                # Upload tool.zip
                public_url = self.s3_uploader.upload_file(
                    tool_bin_path, s3_key)
                if not public_url:
                    logger.error("Failed to upload tool.zip to S3.")
                    return None

                spec_data["tool_source_code_link"] = public_url

                with open(man_page_path, "r") as f:
                    spec_data["tool_man_page_doc"] = f.read()

                tool_entry = ToolEntry.from_dict(spec_data)
                inserted = self.registry_crud.create_tool(tool_entry)

                if inserted:
                    logger.info(f"Tool '{tool_id}' registered successfully.")
                    return tool_id
                else:
                    logger.warning(
                        f"Tool '{tool_id}' already exists or failed to insert.")
                    return None

        except Exception as e:
            logger.error(f"Exception while processing tool ZIP: {e}")
            return None
