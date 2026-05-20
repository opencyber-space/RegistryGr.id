from flask import Flask, request, jsonify
import logging

from .crud import (
    TaskEntryDatabase, SubTaskEntryDatabase, TaskOutputsDatabase, SubTaskOutputsDatabase,
    TaskStatusDatabase, SubTaskStatusDatabase, TaskACLMappingDatabase,
    TaskReviewDataDatabase, SubTaskReviewDataDatabase
)
from .schema import (
    TaskEntry, SubTaskEntry, TaskOutputs, SubTaskOutputs, TaskStatus,
    SubTaskStatus, TaskACLMapping, TaskReviewData, SubTaskReviewData
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Map endpoint name -> (db_instance, data_class, id_field)
db_clients = {
    "task": (TaskEntryDatabase(), TaskEntry, "task_id"),
    "sub_task": (SubTaskEntryDatabase(), SubTaskEntry, "sub_task_id"),
    "task_output": (TaskOutputsDatabase(), TaskOutputs, "task_id"),
    "sub_task_output": (SubTaskOutputsDatabase(), SubTaskOutputs, "sub_task_id"),
    "task_status": (TaskStatusDatabase(), TaskStatus, "task_id"),
    "sub_task_status": (SubTaskStatusDatabase(), SubTaskStatus, "sub_task_id"),
    "task_acl": (TaskACLMappingDatabase(), TaskACLMapping, "task_id"),
    "task_review": (TaskReviewDataDatabase(), TaskReviewData, "task_id"),
    "sub_task_review": (SubTaskReviewDataDatabase(), SubTaskReviewData, "sub_task_id")
}


def register_crud_routes(name, db, cls, id_field):
    base = f"/{name}"

    @app.route(base, methods=["POST"])
    def create_entry():
        try:
            data = request.json
            obj = cls.from_dict(data)
            success, result = db.insert(obj)
            if success:
                return jsonify({"success": True, "data": {"message": f"{name} created", "id": str(result)}}), 201
            else:
                return jsonify({"success": False, "error": result}), 400
        except Exception as e:
            logger.error(f"create_{name} error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route(f"{base}/<string:entry_id>", methods=["GET"])
    def get_entry(entry_id):
        try:
            success, result = db.get_by_id(id_field, entry_id, cls)
            if success:
                return jsonify({"success": True, "data": result.to_dict()}), 200
            else:
                return jsonify({"success": False, "error": result}), 404
        except Exception as e:
            logger.error(f"get_{name} error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route(f"{base}/<string:entry_id>", methods=["PUT"])
    def update_entry(entry_id):
        try:
            update_data = request.json
            success, result = db.update(id_field, entry_id, update_data)
            if success:
                return jsonify({"success": True, "data": {"message": f"{name} updated"}}), 200
            else:
                return jsonify({"success": False, "error": result}), 404
        except Exception as e:
            logger.error(f"update_{name} error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route(f"{base}/<string:entry_id>", methods=["DELETE"])
    def delete_entry(entry_id):
        try:
            success, result = db.delete(id_field, entry_id)
            if success:
                return jsonify({"success": True, "data": {"message": f"{name} deleted"}}), 200
            else:
                return jsonify({"success": False, "error": result}), 404
        except Exception as e:
            logger.error(f"delete_{name} error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route(f"{base}s", methods=["POST"])
    def query_entries():
        try:
            query_filter = request.json
            success, results = db.query(query_filter)
            if success:
                return jsonify({"success": True, "data": results}), 200
            else:
                return jsonify({"success": False, "error": results}), 400
        except Exception as e:
            logger.error(f"query_{name}s error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


# Register all routes dynamically
for name, (db, cls, id_field) in db_clients.items():
    register_crud_routes(name, db, cls, id_field)


if __name__ == "__main__":
    app.run(port=8000)
