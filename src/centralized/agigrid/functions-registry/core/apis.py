from flask import Flask, request, jsonify
import requests
from typing import Any, Dict, Tuple, Optional
import time
import logging
from werkzeug.utils import secure_filename
import os
import zipfile
import tempfile

from .crud import FunctionsRegistryCRUD
from .uploader import FunctionPolicyUploader
from .schema import FunctionEntry
from .ql import schema  

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FunctionsAPI")

HTTP_TIMEOUT: Tuple[int, int] = (5, 60)

POLICY_DB_URL = os.getenv("POLICY_DB_URL", "http://policies:9000").rstrip("/")
crud = FunctionsRegistryCRUD()


def _save_function_to_db(fn_entry: "FunctionEntry") -> None:
    crud.create_function(fn_entry)
    return fn_entry

uploader = FunctionPolicyUploader(
    assets_server_url=os.getenv("ASSETS_SERVER_URL", ""),
    policy_server_url=os.getenv("POLICY_DB_URL", ""),
    save_function_callback=_save_function_to_db,
    remote_path='.',
)

def _find_bundle_root(extracted_dir: str) -> str:
    for root, _, files in os.walk(extracted_dir):
        if "function.json" in files and "function.zip" in files:
            return root
    return ""

@app.route("/functions/upload", methods=["POST"])
def upload_function_bundle():
    if "file" not in request.files:
        return jsonify({"error": "Missing file part"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    safe_name = secure_filename(file.filename)

    if not safe_name.lower().endswith(".zip"):
        return jsonify({"error": "Uploaded file must be a .zip bundle containing function.json and function.zip"}), 400

    try:
        with tempfile.TemporaryDirectory(prefix="fn_bundle_") as tmpdir:
            bundle_path = os.path.join(tmpdir, safe_name)
            file.save(bundle_path)

            # Extract bundle
            if not zipfile.is_zipfile(bundle_path):
                return jsonify({"error": "Invalid zip file"}), 400

            with zipfile.ZipFile(bundle_path, "r") as zf:
                zf.extractall(tmpdir)

            root_dir = _find_bundle_root(tmpdir)
            if not root_dir:
                return jsonify({"error": "Bundle must contain function.json and function.zip"}), 400

            fn_entry = uploader.process_directory(root_dir)

            resp = {
                "message": "Function uploaded & onboarded successfully",
                "function_id": fn_entry.function_id,
                "policy_uri": fn_entry.function_policy_rule_uri,
                "code_url": fn_entry.function_code,  # URL returned by assets server (zip upload)
                "function": fn_entry.to_dict(),
            }
            return jsonify(resp), 200

    except Exception as e:
        logger.exception(f"Function upload failed: {e}")
        return jsonify({"error": f"Function upload failed: {e}"}), 500


@app.route("/functions/<function_id>", methods=["GET"])
def get_function(function_id):
    function = crud.get_function(function_id)
    if function:
        return jsonify(function.to_dict()), 200
    return jsonify({"error": "Function not found"}), 404


@app.route("/functions/<function_id>", methods=["PUT"])
def update_function(function_id):
    updates = request.json
    if not updates:
        return jsonify({"error": "Missing update payload"}), 400

    success = crud.update_function(function_id, updates)
    if success:
        return jsonify({"message": "Function updated successfully"}), 200
    return jsonify({"error": "Function not found"}), 404


@app.route("/functions/<function_id>", methods=["DELETE"])
def delete_function(function_id):
    success = crud.delete_function(function_id)
    if success:
        return jsonify({"message": "Function deleted successfully"}), 200
    return jsonify({"error": "Function not found"}), 404


@app.route("/functions/query/by-type", methods=["GET"])
def query_function_by_type():
    function_type = request.args.get("type")
    return jsonify([f.to_dict() for f in crud.get_functions_by_type(function_type)]), 200


@app.route("/functions/query/by-tag", methods=["GET"])
def query_function_by_tag():
    tag = request.args.get("tag")
    return jsonify([f.to_dict() for f in crud.get_functions_by_tag(tag)]), 200


@app.route("/functions/query/by-keyword", methods=["GET"])
def query_function_by_keyword():
    keyword = request.args.get("keyword")
    return jsonify([f.to_dict() for f in crud.get_functions_by_search_text(keyword)]), 200


@app.route("/functions/query/by-system-flag", methods=["GET"])
def query_function_by_system_flag():
    is_system = request.args.get("is_system", "false").lower() == "true"
    return jsonify([f.to_dict() for f in crud.get_functions_by_system_flag(is_system)]), 200


@app.route("/functions/query/generic", methods=["POST"])
def query_function_generic():
    mongo_query = request.json
    return jsonify([f.to_dict() for f in crud.query_functions(mongo_query)]), 200


'''app.add_url_rule(
    "/functions/graphql",
    view_func=GraphQLView.as_view(
        "functions_graphql",
        schema=schema,
        graphiql=True,
        get_context=lambda: {"crud": crud}
    )
)'''

def _load_function_or_404(function_id: str) -> Optional[FunctionEntry]:
    fn =  crud.get_function(function_id)
    if not fn:
        return None
    return fn


@app.route("/function/deployments/create/<deployment_id>", methods=["POST"])
def create_function_deployment(deployment_id: str):
    
    try:
        payload_in = request.get_json(force=True, silent=False) or {}
        function_id = payload_in.get("function_id")
        if not function_id:
            return jsonify({"error": "function_id is required in the request body"}), 400

        fn = _load_function_or_404(function_id)
        if not fn:
            return jsonify({"error": f"Function '{function_id}' not found"}), 404

        if not fn.function_policy_rule_uri:
            return jsonify({"error": f"Function '{function_id}' has no function_policy_rule_uri set"}), 400

        outbound = {
            "name": payload_in.get("name") or f"{fn.function_name or 'function'}-deployment",
            "policy_rule_uri": fn.function_policy_rule_uri,
            "policy_rule_parameters": payload_in.get("policy_rule_parameters", fn.function_parameters or {}),
            "replicas": int(payload_in.get("replicas", 1)),
            "autoscaling": bool(payload_in.get("autoscaling", False)),
            "function_metadata": payload_in.get("function_metadata", fn.function_metadata or {}),
            "function_tags": payload_in.get("function_tags", fn.function_tags or []),
        }

        url = f"{POLICY_DB_URL}/function/deployments/create/{deployment_id}"

        session = requests.Session()
        resp = session.post(url, json=outbound, timeout=HTTP_TIMEOUT)
        if resp.status_code >= 400:
            return jsonify({"error": "Upstream error", "status": resp.status_code, "body": _safe_text(resp)}), resp.status_code

        return jsonify({
            "message": "Deployment created",
            "deployment_id": deployment_id,
            "function_id": function_id,
            "policy_rule_uri": fn.function_policy_rule_uri,
            "request_payload": outbound,
            "upstream": _safe_json(resp)
        }), 200

    except Exception as e:
        logger.exception("create_function_deployment failed")
        return jsonify({"error": str(e)}), 500


@app.route("/function/call_function/<call_id>", methods=["POST"])
def call_function(call_id: str):
   
    try:
        body = request.get_json(force=True, silent=False) or {}
        url = f"{POLICY_DB_URL}/function/call_function/{call_id}"

        session = requests.Session()
        resp = session.post(url, json=body, timeout=HTTP_TIMEOUT)
        if resp.status_code >= 400:
            return jsonify({"error": "Upstream error", "status": resp.status_code, "body": _safe_text(resp)}), resp.status_code

        return jsonify(resp.json()), 200

    except Exception as e:
        logger.exception("call_function failed")
        return jsonify({"error": str(e)}), 500


@app.route("/function/deployments/remove/<deployment_id>", methods=["DELETE"])
def remove_function_deployment(deployment_id: str):
   
    try:
        body = request.get_json(force=True, silent=True) or {}
        function_id = body.get("function_id")
        if not function_id:
            return jsonify({"error": "function_id is required in the request body"}), 400

        fn = _load_function_or_404(function_id)
        if not fn:
            return jsonify({"error": f"Function '{function_id}' not found"}), 404

        url = f"{POLICY_DB_URL}/function/deployments/remove/{deployment_id}"
        resp = session.delete(url, timeout=HTTP_TIMEOUT)

        session = requests.Session()
        if resp.status_code >= 400:
            return jsonify({"error": "Upstream error", "status": resp.status_code, "body": _safe_text(resp)}), resp.status_code

        return jsonify({
            "message": "Deployment removed",
            "deployment_id": deployment_id,
            "function_id": function_id,
            "upstream": _safe_json(resp)
        }), 200

    except Exception as e:
        logger.exception("remove_function_deployment failed")
        return jsonify({"error": str(e)}), 500


@app.route("/function/call_as_job/<executor_id>", methods=["POST"])
def call_function_as_job(executor_id: str):
    """
    POST /function/call_as_job/<executor_id>
    Body:
    {
      "function_id": "<required>",
      "job_name": "my-job",             # optional; defaults to "<function_name>-job"
      "inputs": {...},                  # required; forwarded to job "inputs"
      "parameters": {...},              # optional; defaults to function.function_parameters
      "policy_rule_parameters": {...},  # optional alias of "parameters"
      "node_selector": {...},           # optional; defaults to {}
      "poll_interval": 2,               # optional
      "max_retries": 30,                # optional
      "endpoint": "http://...",         # optional; defaults to POLICY_DB_URL
    }
    """
    try:
        body: Dict[str, Any] = request.get_json(force=True, silent=False) or {}
        function_id = body.get("function_id")
        if not function_id:
            return jsonify({"error": "function_id is required"}), 400

        fn = _load_function_or_404(function_id)
        if not fn:
            return jsonify({"error": f"Function '{function_id}' not found"}), 404

        if not fn.function_policy_rule_uri:
            return jsonify({"error": f"Function '{function_id}' has no function_policy_rule_uri"}), 400

        job_name = body.get("job_name") or f"{fn.function_name or 'function'}-job"
        inputs = body.get("inputs")
        if inputs is None or not isinstance(inputs, dict):
            return jsonify({"error": "inputs (object) is required"}), 400

        # Allow either "parameters" or "policy_rule_parameters"
        parameters = body.get("parameters")
        if parameters is None:
            parameters = body.get("policy_rule_parameters", fn.function_parameters or {})

        node_selector = body.get("node_selector", {})
        poll_interval = int(body.get("poll_interval", 2))
        max_retries = int(body.get("max_retries", 30))
        endpoint = (body.get("endpoint") or POLICY_DB_URL).rstrip("/")

        # --- Copy of JobType4Executor.execute() logic (inline) ---

        # 1) Submit job
        submit_url = f"{endpoint}/jobs/submit/{executor_id}"
        submit_payload = {
            "name": job_name,
            "policy_rule_uri": fn.function_policy_rule_uri,
            "policy_rule_parameters": parameters,
            "node_selector": node_selector,
            "inputs": inputs,
        }
        logger.info(f"[submit] {submit_url}")
        submit_resp = requests.Session().post(submit_url, json=submit_payload, timeout=10)
        submit_resp.raise_for_status()
        submit_json = submit_resp.json()
        if not submit_json.get("success", False):
            return jsonify({"error": "Job submission failed", "upstream": submit_json}), 502

        job_id = submit_json.get("job_id")
        if not job_id:
            return jsonify({"error": "Upstream did not return job_id", "upstream": submit_json}), 502

        # 2) Poll status
        status_url = f"{endpoint}/jobs/{job_id}"
        logger.info(f"[poll] {status_url}")

        session = requests.Session()

        for attempt in range(max_retries):
            try:

                status_resp = session.get(status_url, timeout=10)
                status_resp.raise_for_status()
                status_json = status_resp.json()

                #if not status_json.get("success", False):
                #    return jsonify({"error": "Job status check failed", "upstream": status_json}), 502

                job_data = status_json.get("data", {}) or {}
                job_status = job_data.get("job_status")
                logger.debug(f"Attempt {attempt + 1}/{max_retries}: job_status={job_status}")

                if job_status == "completed":
                    return jsonify({
                        "message": "Job completed",
                        "executor_id": executor_id,
                        "function_id": function_id,
                        "policy_rule_uri": fn.function_policy_rule_uri,
                        "job_id": job_id,
                        "job_name": job_name,
                        "job_output_data": job_data.get("job_output_data"),
                        "upstream": status_json
                    }), 200

            except Exception as e:
                logger.warning(f"Polling attempt {attempt + 1} failed: {e}")

            time.sleep(poll_interval)

        # Timed out
        return jsonify({
            "error": "Job did not complete within timeout window",
            "executor_id": executor_id,
            "function_id": function_id,
            "job_id": job_id,
            "poll_interval": poll_interval,
            "max_retries": max_retries
        }), 504

    except requests.HTTPError as e:
        body = getattr(e.response, "text", None) if hasattr(e, "response") else None
        logger.exception("HTTP error in call_function_as_job")
        return jsonify({"error": str(e), "body": body}), 502
    except Exception as e:
        logger.exception("call_function_as_job failed")
        return jsonify({"error": str(e)}), 500



def _safe_json(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"text": resp.text}

def _safe_text(resp: requests.Response) -> str:
    try:
        return resp.text
    except Exception:
        return "<no-body>"

def run_functions_server():
    app.run(host='0.0.0.0', port=6000)
