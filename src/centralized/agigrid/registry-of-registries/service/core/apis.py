from flask import Flask, request, jsonify
from redis import Redis
import json

from registry_db import RegistryDB
from .registry_db import CreateRegistryController
from .registry_db import UpdateRegistryController
from .registry_db import DeleteRegistryController
from .zipper import UploadZipAPI

# Flask setup
app = Flask(__name__)
redis_client = Redis(host="localhost", port=6379, decode_responses=True)

# Shared DB layer
registry_db = RegistryDB()

# Controllers
create_controller = CreateRegistryController(registry_db)
update_controller = UpdateRegistryController(registry_db)
delete_controller = DeleteRegistryController(registry_db)

# Upload handler
upload_handler = UploadZipAPI(
    controller=create_controller,
    redis_client=redis_client,
    s3_bucket="my-assets-bucket",
    s3_prefix_root="registries",
    assets_db_url="http://assets-db-service"
)


@app.route("/registry/create", methods=["POST"])
def create_registry():
    try:
        spec = request.get_json()
        registry_id = create_controller.create(spec)
        return jsonify({"status": "success", "registry_id": registry_id}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/registry/update", methods=["PUT"])
def update_registry():
    try:
        spec = request.get_json()
        success = update_controller.update(spec)
        return jsonify({"status": "success", "updated": success}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/registry/delete/<registry_id>", methods=["DELETE"])
def delete_registry(registry_id):
    try:
        success = delete_controller.delete(registry_id)
        return jsonify({"status": "success", "deleted": success}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route("/registry/upload_zip", methods=["POST"])
def upload_zip():
    try:
        zip_file = request.files.get("zip")
        spec_json = request.form.get("spec")
        if not zip_file or not spec_json:
            return jsonify({"status": "error", "message": "Missing zip or spec"}), 400

        spec = json.loads(spec_json)
        task_id = upload_handler.upload(spec, zip_file)
        return jsonify({"status": "accepted", "task_id": task_id}), 202
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/registry/upload/status/<task_id>", methods=["GET"])
def check_upload_status(task_id):
    status = redis_client.get(f"UPLOAD_STATUS:{task_id}")
    return jsonify({"task_id": task_id, "status": status or "unknown"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


def main():
    app.run(host="0.0.0.0", port=8080, debug=True)
