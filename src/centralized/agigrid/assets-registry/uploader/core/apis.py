import uuid
import threading
import logging
from flask import Flask, request, jsonify, Response
from werkzeug.utils import secure_filename
from io import BytesIO
import redis
import os

from .writer import ZipUploadProcessor
from .s3 import S3UploaderPlugin
from .writer import WriteAPIClient
from .reader import StreamingZipArchiver, ReadAPIClient
from .s3 import S3DownloaderPlugin

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Configure clients
s3_uploader = S3UploaderPlugin(bucket_name="my-assets", prefix="uploaded", public=True)
processor = ZipUploadProcessor(s3_uploader)
writer = WriteAPIClient(base_url=os.getenv("ASSETS_DB_SERVICE"))

reader = ReadAPIClient(base_url=os.getenv("ASSETS_DB_SERVICE"))
s3 = S3DownloaderPlugin()
archiver = StreamingZipArchiver()

STATUS_PREFIX = "UPLOAD_STATUS"


def set_status(upload_id: str, status: str):
    redis_client.set(f"{STATUS_PREFIX}:{upload_id}", status)


def get_status(upload_id: str) -> str:
    return redis_client.get(f"{STATUS_PREFIX}:{upload_id}") or "unknown"


def background_worker(upload_id: str, zip_data: bytes):
    try:
        set_status(upload_id, "processing")
        stream = BytesIO(zip_data)
        metadata = processor.process(stream)
        result = writer.submit_asset(metadata)
        status = "success" if result.get("success") else f"failed: {result.get('error')}"
        set_status(upload_id, status)
    except Exception as e:
        set_status(upload_id, f"failed: {str(e)}")


@app.route("/zip/upload", methods=["POST"])
def upload_zip():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400

    zip_data = file.read()
    upload_id = str(uuid.uuid4())

    threading.Thread(target=background_worker, args=(upload_id, zip_data), daemon=True).start()
    set_status(upload_id, "queued")

    return jsonify({"success": True, "upload_id": upload_id}), 202


@app.route("/zip/status/<string:upload_id>")
def get_upload_status(upload_id):
    status = get_status(upload_id)
    return jsonify({"upload_id": upload_id, "status": status})


@app.route("/zip/download/<string:asset_id>", methods=["GET"])
def download_zip(asset_id):
    asset = reader.fetch_asset_metadata(asset_id)
    if not asset:
        return jsonify({"success": False, "error": "Asset not found"}), 404

    files_meta = asset.get("files", [])
    def generate():
        file_streams = ((f["asset_file_id"], s3.download_file(f["asset_file_url"])) for f in files_meta)
        return archiver.archive(file_streams)

    headers = {
        "Content-Disposition": f"attachment; filename={asset_id}.zip",
        "Content-Type": "application/zip"
    }

    return Response(generate(), headers=headers)
