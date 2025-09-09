from flask import Flask, request, jsonify
import logging

from .schema import Exchange
from .crud import ExchangeDatabase 
from .exchange_infra import collect_and_sanitize_config, bad_request, build_infra_creator, get_or_create_exchange

app = Flask(__name__)
logger = logging.getLogger(__name__)

exchange_db = ExchangeDatabase()

REQUIRED_CREATE_FIELDS = [
    "exchange_id",
    "kubeconfig",         
    "namespace",
    "deployment_name",
    "storage_size",       
    "node_port",        
    "public_url",  
]


@app.route('/exchange', methods=['POST'])
def create_exchange():
    try:
        data = request.json or {}
        exchange = Exchange.from_dict(data)

        success, result = exchange_db.insert(exchange)
        if success:
            return jsonify({
                "success": True,
                "data": {"message": "Exchange created", "id": str(result)}
            }), 201
        else:
            return jsonify({"success": False, "error": result}), 400
    except Exception as e:
        logger.error(f"Error in create_exchange: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/exchange/<string:exchange_id>', methods=['GET'])
def get_exchange(exchange_id):
    try:
        success, result = exchange_db.get_by_exchange_id(exchange_id)
        if success:
            return jsonify({"success": True, "data": result.to_dict()}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in get_exchange: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/exchange/<string:exchange_id>', methods=['PUT'])
def update_exchange(exchange_id):
    try:
        update_data = request.json or {}
        success, result = exchange_db.update(exchange_id, update_data)
        if success:
            return jsonify({"success": True, "data": {"message": "Exchange updated"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in update_exchange: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/exchange/<string:exchange_id>', methods=['DELETE'])
def delete_exchange(exchange_id):
    try:
        success, result = exchange_db.delete(exchange_id)
        if success:
            return jsonify({"success": True, "data": {"message": "Exchange deleted"}}), 200
        else:
            return jsonify({"success": False, "error": result}), 404
    except Exception as e:
        logger.error(f"Error in delete_exchange: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/exchanges', methods=['POST'])
def query_exchanges():
    try:
        query_filter = request.json or {}
        success, results = exchange_db.query(query_filter)
        if success:
            return jsonify({"success": True, "data": results}), 200
        else:
            return jsonify({"success": False, "error": results}), 400
    except Exception as e:
        logger.error(f"Error in query_exchanges: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/create-exchange-infra", methods=["POST"])
def create_exchange_infra():
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return bad_request("Invalid JSON payload")

    # Validate required fields
    missing = [k for k in REQUIRED_CREATE_FIELDS if k not in payload]
    if missing:
        return bad_request("Missing required fields", {"missing": missing})

    exchange_id = str(payload["exchange_id"])
    public_url = str(payload["public_url"])

    # Load or create doc
    exchange = get_or_create_exchange(exchange_id)

    # Prevent re-create when already live
    is_live = bool(exchange.exchange_config.get("is_infra_live", False))
    if is_live:
        # Still update URLs/config (excluding kubeconfig) if caller changed metadata
        new_cfg = collect_and_sanitize_config(payload)
        new_cfg["is_infra_live"] = True
        update_fields = {
            "exchange_config": new_cfg,
            "exchange_urls.public_url": public_url,
        }
        exchange_db.update(exchange_id, update_fields)
        return jsonify({
            "success": True,
            "message": "Infra already live; configuration/URL updated.",
            "exchange_id": exchange_id,
            "public_url": public_url,
        }), 200

    # Build and run infra creator
    try:
        creator = build_infra_creator(payload)
        creator.create()
    except Exception as e:
        return jsonify({"success": False, "error": f"Infra creation failed: {str(e)}"}), 500

    # Persist config/URL (excluding kubeconfig), set is_infra_live true
    cfg_to_store = collect_and_sanitize_config(payload)
    cfg_to_store["is_infra_live"] = True

    ok, res = exchange_db.update(exchange_id, {
        "exchange_config": cfg_to_store,
        "exchange_urls.public_url": public_url,
    })
    if not ok:
        return jsonify({"success": False, "error": f"DB update failed: {res}"}), 500

    return jsonify({
        "success": True,
        "message": "Exchange infra created and configuration saved.",
        "exchange_id": exchange_id,
        "public_url": public_url,
    }), 201


@app.route("/remove-exchange-infra", methods=["POST"])
def remove_exchange_infra():
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        return bad_request("Invalid JSON payload")

    if "exchange_id" not in payload:
        return bad_request("Missing required field: exchange_id")

    exchange_id = str(payload["exchange_id"])
    public_url = str(payload.get("public_url", ""))  # keep if provided

    # We allow removal to be called even if infra is not live; idempotent behavior
    # If kubeconfig is present, we'll try actual teardown; otherwise just flip the flag.
    has_kubeconfig = "kubeconfig" in payload

    if has_kubeconfig:
        try:
            creator = build_infra_creator(payload)
            creator.remove()
        except Exception as e:
            logger.warning(f"Infra removal encountered an error: {e}")

    # Update DB: mark is_infra_live = False, persist config sans kubeconfig, keep public_url if provided
    existing_ok, existing = exchange_db.get_by_exchange_id(exchange_id)
    if existing_ok:
        merged_cfg = existing.exchange_config.copy()
        merged_cfg.update(collect_and_sanitize_config(payload))
        merged_cfg["is_infra_live"] = False
    else:
        merged_cfg = {"is_infra_live": False}
        existing = Exchange(exchange_id=exchange_id, exchange_name="", exchange_description="")

    updates = {"exchange_config": merged_cfg}
    if public_url:
        updates["exchange_urls.public_url"] = public_url

    ok, res = exchange_db.update(exchange_id, updates)
    if not ok:
        return jsonify({"success": False, "error": f"DB update failed: {res}"}), 500

    return jsonify({
        "success": True,
        "message": "Exchange infra removed (idempotent) and configuration updated.",
        "exchange_id": exchange_id,
        "public_url": public_url or existing.exchange_urls.get("public_url", ""),
    }), 200



def run_server():
    app.run(host='0.0.0.0', port=6000) 
