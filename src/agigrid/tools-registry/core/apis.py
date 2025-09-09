from flask import Flask, request, jsonify
import logging

from .crud import ToolsRegistryCRUD
from .uploader import S3Uploader
from .parser import ToolPackageParser
from .schema import ToolEntry
from .ql import schema

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ToolsAPI")

# Initialize services
crud = ToolsRegistryCRUD()

s3_uploader = S3Uploader()

zip_parser = ToolPackageParser(s3_uploader=s3_uploader, registry_crud=crud)


@app.route("/tools/upload", methods=["POST"])
def upload_tool_bundle():
    if "file" not in request.files:
        return jsonify({"error": "Missing file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    file_path = f"/tmp/{file.filename}"
    file.save(file_path)
    tool_id = zip_parser.process_zip_package(file_path)

    if not tool_id:
        return jsonify({"error": "Failed to process tool package"}), 500

    return jsonify({"message": "Tool uploaded successfully", "tool_id": tool_id}), 200


@app.route("/tools/<tool_id>", methods=["GET"])
def get_tool(tool_id):
    tool = crud.get_tool(tool_id)
    if tool:
        return jsonify(tool.to_dict()), 200
    return jsonify({"error": "Tool not found"}), 404


@app.route("/tools/<tool_id>", methods=["PUT"])
def update_tool(tool_id):
    updates = request.json
    if not updates:
        return jsonify({"error": "Missing update payload"}), 400

    success = crud.update_tool(tool_id, updates)
    if success:
        return jsonify({"message": "Tool updated successfully"}), 200
    return jsonify({"error": "Tool not found"}), 404


@app.route("/tools/<tool_id>", methods=["DELETE"])
def delete_tool(tool_id):
    success = crud.delete_tool(tool_id)
    if success:
        return jsonify({"message": "Tool deleted successfully"}), 200
    return jsonify({"error": "Tool not found"}), 404


@app.route("/tools/query/by-type", methods=["GET"])
def query_by_type():
    tool_type = request.args.get("type")
    return jsonify([t.to_dict() for t in crud.get_tools_by_type(tool_type)]), 200


@app.route("/tools/query/by-tag", methods=["GET"])
def query_by_tag():
    tag = request.args.get("tag")
    return jsonify([t.to_dict() for t in crud.get_tools_by_tag(tag)]), 200


@app.route("/tools/query/by-keyword", methods=["GET"])
def query_by_keyword():
    keyword = request.args.get("keyword")
    return jsonify([t.to_dict() for t in crud.get_tools_by_search_text(keyword)]), 200


@app.route("/tools/query/by-execution-mode", methods=["GET"])
def query_by_execution_mode():
    mode = request.args.get("mode")
    return jsonify([t.to_dict() for t in crud.get_tools_by_execution_mode(mode)]), 200


@app.route("/tools/query/by-policy-uri", methods=["GET"])
def query_by_policy_uri():
    uri = request.args.get("uri")
    return jsonify([t.to_dict() for t in crud.get_tools_by_policy_rule(uri)]), 200


@app.route("/tools/query/generic", methods=["POST"])
def query_generic():
    mongo_query = request.json
    return jsonify([t.to_dict() for t in crud.query_tools(mongo_query)]), 200


'''app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view(
        "graphql",
        schema=schema,
        graphiql=True,
        get_context=lambda: {"crud": crud}
    )
)'''


def run_server():
    app.run(host='0.0.0.0', port=6000)
