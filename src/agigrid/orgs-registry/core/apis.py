from flask import request, jsonify
from flask import Flask, request, jsonify
from flask_graphql import GraphQLView
import logging
from .schema import OrgObject
from .ql import schema
from .db import OrgStoreDatabase
from .db import OrgStoreQueries

logger = logging.getLogger(__name__)
org_db = OrgStoreDatabase()
org_queries = OrgStoreQueries(org_db.collection)


def register_org_routes(app):

    @app.route('/org', methods=['POST'])
    def create_org():
        try:
            org_data = request.json
            org = OrgObject.from_dict(org_data)
            success, result = org_db.insert(org)
            if success:
                return jsonify({"success": True, "data": {"message": "Org created", "id": str(result)}}), 201
            else:
                return jsonify({"success": False, "error": result}), 400
        except Exception as e:
            logger.error(f"create_org error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/org/<string:org_uri>', methods=['GET'])
    def get_org(org_uri):
        try:
            success, result = org_db.get_by_org_uri(org_uri)
            if success:
                return jsonify({"success": True, "data": result.to_dict()}), 200
            else:
                return jsonify({"success": False, "error": result}), 404
        except Exception as e:
            logger.error(f"get_org error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/org/<string:org_uri>', methods=['PUT'])
    def update_org(org_uri):
        try:
            update_data = request.json
            success, result = org_db.update(org_uri, update_data)
            if success:
                return jsonify({"success": True, "data": {"message": "Org updated"}}), 200
            else:
                return jsonify({"success": False, "error": result}), 404
        except Exception as e:
            logger.error(f"update_org error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/org/<string:org_uri>', methods=['DELETE'])
    def delete_org(org_uri):
        try:
            success, result = org_db.delete(org_uri)
            if success:
                return jsonify({"success": True, "data": {"message": "Org deleted"}}), 200
            else:
                return jsonify({"success": False, "error": result}), 404
        except Exception as e:
            logger.error(f"delete_org error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs', methods=['POST'])
    def query_orgs():
        try:
            query_filter = request.json
            success, results = org_db.query(query_filter)
            if success:
                return jsonify({"success": True, "data": results}), 200
            else:
                return jsonify({"success": False, "error": results}), 400
        except Exception as e:
            logger.error(f"query_orgs error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    # ----- Specialized Query APIs -----

    @app.route('/orgs/by-id/<string:org_id>', methods=['GET'])
    def get_org_by_id(org_id):
        try:
            success, result = org_queries.find_by_org_id(org_id)
            if success:
                return jsonify({"success": True, "data": result.to_dict()}), 200
            else:
                return jsonify({"success": False, "error": result}), 404
        except Exception as e:
            logger.error(f"get_org_by_id error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs/by-spec-id/<string:spec_id>', methods=['GET'])
    def get_orgs_by_spec_id(spec_id):
        try:
            success, results = org_queries.find_by_spec_id(spec_id)
            if success:
                return jsonify({"success": True, "data": [r.to_dict() for r in results]}), 200
            else:
                return jsonify({"success": False, "error": results}), 404
        except Exception as e:
            logger.error(f"get_orgs_by_spec_id error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs/by-tag/<string:tag>', methods=['GET'])
    def get_orgs_by_tag(tag):
        try:
            success, results = org_queries.find_by_tag(tag)
            if success:
                return jsonify({"success": True, "data": [r.to_dict() for r in results]}), 200
            else:
                return jsonify({"success": False, "error": results}), 404
        except Exception as e:
            logger.error(f"get_orgs_by_tag error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs/by-group/<string:group_id>', methods=['GET'])
    def get_orgs_by_group(group_id):
        try:
            success, results = org_queries.find_by_group_id(group_id)
            if success:
                return jsonify({"success": True, "data": [r.to_dict() for r in results]}), 200
            else:
                return jsonify({"success": False, "error": results}), 404
        except Exception as e:
            logger.error(f"get_orgs_by_group error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs/by-registry/<string:registry_id>', methods=['GET'])
    def get_orgs_by_registry(registry_id):
        try:
            success, results = org_queries.find_by_asset_registry(registry_id)
            if success:
                return jsonify({"success": True, "data": [r.to_dict() for r in results]}), 200
            else:
                return jsonify({"success": False, "error": results}), 404
        except Exception as e:
            logger.error(f"get_orgs_by_registry error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs/search-by-name', methods=['GET'])
    def search_orgs_by_name():
        try:
            keyword = request.args.get('q', '')
            success, results = org_queries.search_by_name_keyword(keyword)
            if success:
                return jsonify({"success": True, "data": [r.to_dict() for r in results]}), 200
            else:
                return jsonify({"success": False, "error": results}), 404
        except Exception as e:
            logger.error(f"search_orgs_by_name error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs/with-url-prefix', methods=['GET'])
    def get_orgs_with_url_prefix():
        try:
            prefix = request.args.get("prefix", "")
            success, results = org_queries.find_with_url_prefix(prefix)
            if success:
                return jsonify({"success": True, "data": [r.to_dict() for r in results]}), 200
            else:
                return jsonify({"success": False, "error": results}), 404
        except Exception as e:
            logger.error(f"get_orgs_with_url_prefix error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs/by-metadata', methods=['POST'])
    def get_orgs_by_metadata():
        try:
            data = request.json
            key = data.get("key")
            value = data.get("value")
            success, results = org_queries.find_by_metadata_key_value(
                key, value)
            if success:
                return jsonify({"success": True, "data": [r.to_dict() for r in results]}), 200
            else:
                return jsonify({"success": False, "error": results}), 404
        except Exception as e:
            logger.error(f"get_orgs_by_metadata error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route('/orgs/has-spec-key/<string:key>', methods=['GET'])
    def get_orgs_by_spec_key(key):
        try:
            success, results = org_queries.find_by_spec_data_key(key)
            if success:
                return jsonify({"success": True, "data": [r.to_dict() for r in results]}), 200
            else:
                return jsonify({"success": False, "error": results}), 404
        except Exception as e:
            logger.error(f"get_orgs_by_spec_key error: {e}")
            return jsonify({"success": False, "error": str(e)}), 500


def register_graphql_route(app):
    app.add_url_rule(
        "/graphql",
        view_func=GraphQLView.as_view(
            "graphql",
            schema=schema,
            graphiql=True
        )
    )


def start_server():
    app = Flask(__name__)
    register_org_routes(app)
    register_graphql_route(app)
    app.run(host="0.0.0.0", port=5000)
