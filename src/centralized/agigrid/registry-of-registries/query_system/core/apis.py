from flask import Flask, request, jsonify
from flask_graphql import GraphQLView
from .controller import QueryController
from .ql import schema

app = Flask(__name__)
query_controller = QueryController()


@app.route("/registry/query/by-id/<registry_id>", methods=["GET"])
def query_by_id(registry_id):
    try:
        result = query_controller.get_registry_by_id(registry_id)
        return jsonify({"status": "success", "result": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/registry/query/by-type/<registry_type>", methods=["GET"])
def query_by_type(registry_type):
    try:
        result = query_controller.find_registries_by_type(registry_type)
        return jsonify({"status": "success", "count": len(result), "results": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/registry/query/by-tags", methods=["POST"])
def query_by_tags():
    try:
        data = request.get_json()
        tags = data.get("tags", [])
        result = query_controller.find_registries_by_tags(tags)
        return jsonify({"status": "success", "count": len(result), "results": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500




@app.route("/registry/query/by-url", methods=["GET"])
def query_by_url():
    try:
        fragment = request.args.get("fragment", "")
        result = query_controller.find_registries_by_url(fragment)
        return jsonify({"status": "success", "count": len(result), "results": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/registry/query/partial", methods=["POST"])
def query_partial():
    try:
        data = request.get_json()
        field = data["field"]
        fragment = data["fragment"]
        result = query_controller.find_partial_match(field, fragment)
        return jsonify({"status": "success", "count": len(result), "results": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/registry/query", methods=["POST"])
def query_raw():
    try:
        query = request.get_json()
        filter_dict = query.get("filter", {})
        limit = query.get("limit", 100)
        result = query_controller.query_raw(filter_dict, limit)
        return jsonify({"status": "success", "count": len(result), "results": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True)
)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


def main():
    app.run(host="0.0.0.0", port=8090, debug=True)
