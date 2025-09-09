from flask import Flask, request, jsonify
from pymongo import MongoClient
from flask_graphql import GraphQLView
from .ql import AssetQuery, schema
import logging

from .db import AssetDB
from .creator import AssetCreator


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# MongoDB Setup
mongo_client = MongoClient("mongodb://localhost:27017/")
asset_db = AssetDB(external_client=mongo_client)
asset_creator = AssetCreator(asset_db)
asset_query = AssetQuery(asset_db)


@app.route("/assets", methods=["POST"])
def create_asset():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No input JSON provided"}), 400

    success, message = asset_creator.create_asset(data)
    status_code = 201 if success else 400
    return jsonify({"success": success, "message": message}), status_code


@app.route("/assets/<string:asset_id>", methods=["GET"])
def get_asset(asset_id):
    asset = asset_db.find_by_id(asset_id)
    if not asset:
        return jsonify({"success": False, "error": f"Asset '{asset_id}' not found"}), 404
    return jsonify({"success": True, "asset": asset.to_dict()})


@app.route("/assets/<string:asset_id>", methods=["PUT"])
def update_asset(asset_id):
    update_data = request.get_json()
    if not update_data:
        return jsonify({"success": False, "error": "No update data provided"}), 400

    if not isinstance(update_data, dict):
        return jsonify({"success": False, "error": "Update data must be a JSON object"}), 400

    success = asset_db.update(asset_id, update_data)
    if not success:
        return jsonify({"success": False, "error": f"Asset '{asset_id}' update failed"}), 404
    return jsonify({"success": True, "message": f"Asset '{asset_id}' updated successfully"})


@app.route("/assets/<string:asset_id>", methods=["DELETE"])
def delete_asset(asset_id):
    success = asset_db.delete_by_id(asset_id)
    if not success:
        return jsonify({"success": False, "error": f"Asset '{asset_id}' not found"}), 404
    return jsonify({"success": True, "message": f"Asset '{asset_id}' deleted successfully"})


@app.route("/query/by-id/<string:asset_id>")
def rest_get_by_id(asset_id):
    result = asset_query.get_by_id(asset_id)
    if not result:
        return jsonify({"success": False, "error": "Asset not found"}), 404
    return jsonify(result.to_dict())

@app.route("/query/by-type/<string:asset_type>")
def rest_get_by_type(asset_type):
    return jsonify([a.to_dict() for a in asset_query.get_by_type(asset_type)])

@app.route("/query/by-sub-type/<string:sub_type>")
def rest_get_by_sub_type(sub_type):
    return jsonify([a.to_dict() for a in asset_query.get_by_sub_type(sub_type)])

@app.route("/query/by-tag/<string:tag>")
def rest_get_by_tag(tag):
    return jsonify([a.to_dict() for a in asset_query.get_by_tag(tag)])

@app.route("/query/by-api-route/<string:route>")
def rest_get_by_api_route(route):
    return jsonify([a.to_dict() for a in asset_query.get_by_api_route(route)])

# --- GraphQL Endpoint ---
@app.route("/graphql", methods=["GET", "POST"])
def graphql_server():
    view = GraphQLView.as_view("graphql", schema=schema, graphiql=True, context={"query": asset_query})
    return view()


def run_server():
    app.run(host="0.0.0.0", port=8080)
