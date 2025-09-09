import zipfile
import io
import json
import logging
from typing import Dict, Generator, Tuple, IO

logger = logging.getLogger("StreamingZipParser")
logger.setLevel(logging.INFO)

class StreamingZipParser:
    def __init__(self, zip_stream: IO[bytes]):
        self.zip_stream = zip_stream
        self.asset_metadata: Dict = {}

    def parse(self) -> Generator[Tuple[str, IO[bytes]], None, None]:
        
        try:
            with zipfile.ZipFile(self.zip_stream) as zf:
                for entry in zf.infolist():
                    if entry.is_dir():
                        continue

                    filename = entry.filename
                    with zf.open(entry) as file_data:
                        if filename == "asset.json":
                            logger.info("[ZipParser] Found metadata file: asset.json")
                            self.asset_metadata = json.load(file_data)
                        else:
                            logger.info(f"[ZipParser] Yielding file: {filename}")
                            yield filename, io.BytesIO(file_data.read())

        except Exception as e:
            logger.error(f"[ZipParser] Failed to parse ZIP: {e}")
            raise
