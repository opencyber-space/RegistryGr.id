from flask import Flask, request, jsonify, send_file
import zipfile
import io
import tempfile
import os
import json
import logging

from .schema import SpecObject, TemplateObject, WorkflowObject, DSLExecutors
from .k8s import DSLExecutorInitializer
from .executors import ExecutorsDB
from .controllers import SpecDatabase, TemplateDatabase, WorkflowDatabase
from .policy import upload_policy_zip_bytes, onboard_policy_to_server
from .executor_client import WorkflowExecutorClient

logger = logging.getLogger(__name__)
app = Flask(__name__)

spec_db = SpecDatabase()
template_db = TemplateDatabase()
workflow_db = WorkflowDatabase()


@app.route("/upload-spec", methods=["POST"])
def upload_spec():
    try:
        file = request.files["file"]
        if not file or not file.filename.endswith(".zip"):
            return jsonify({"success": False, "error": "Invalid or missing zip file"}), 400

        # Extract zip contents in memory
        zip_bytes = file.read()
        zip_buffer = io.BytesIO(zip_bytes)

        with zipfile.ZipFile(zip_buffer) as z:
            # Read spec.json
            if "spec.json" not in z.namelist():
                return jsonify({"success": False, "error": "Missing spec.json in zip"}), 400

            with z.open("spec.json") as f:
                spec_data = json.load(f)

            spec = SpecObject.from_dict(spec_data)

            # Check backend policy rule logic
            rule_info = spec.backend_policy_rule_ids.get("default", {})
            rule_uri = rule_info.get("policyRuleURI", "")

            # If rule URI is not provided → upload + onboard
            if not rule_uri:
                if "policy.zip" not in z.namelist():
                    return jsonify({"success": False, "error": "Missing policy.zip in zip"}), 400

                with z.open("policy.zip") as pf:
                    policy_bytes = pf.read()

                # Upload ZIP to policy file server
                success, policy_url = upload_policy_zip_bytes(
                    file_bytes=policy_bytes,
                    filename="policy.zip",
                    upload_endpoint="http://<upload-host>:<port>/upload"
                )
                if not success:
                    return jsonify({"success": False, "error": f"Policy upload failed: {policy_url}"}), 500

                # Onboard the policy and get rule URI
                policy_uri = onboard_policy_to_server(
                    name=spec.spec_name,
                    version=spec.spec_version.version,
                    release_tag="stable",
                    description=spec.spec_description,
                    code_url=policy_url,
                    metadata=spec.spec_metadata,
                    tags=",".join(spec.spec_search_tags)
                )
                # Update spec
                spec.backend_policy_rule_ids["default"]["policyRuleURI"] = policy_uri

            # Save to DB
            success, result = spec_db.insert(spec)
            if success:
                return jsonify({"success": True, "spec_uri": spec.spec_uri}), 200
            else:
                return jsonify({"success": False, "error": result}), 500

    except Exception as e:
        logger.exception("Error uploading spec")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/upload-template", methods=["POST"])
def upload_template():
    try:
        file = request.files["file"]
        if not file or not file.filename.endswith(".zip"):
            return jsonify({"success": False, "error": "Invalid or missing zip file"}), 400

        # Read and extract ZIP
        zip_bytes = file.read()
        zip_buffer = io.BytesIO(zip_bytes)

        with zipfile.ZipFile(zip_buffer) as z:
            if "template.json" not in z.namelist():
                return jsonify({"success": False, "error": "Missing template.json in zip"}), 400

            with z.open("template.json") as f:
                template_data = json.load(f)

            template = TemplateObject.from_dict(template_data)

            # Upload policy.zip only if needed
            if not template.template_custom_validation_policy_rule_uri:
                if "policy.zip" not in z.namelist():
                    return jsonify({
                        "success": False,
                        "error": "Missing policy.zip and no policy URI provided"
                    }), 400

                with z.open("policy.zip") as pf:
                    policy_bytes = pf.read()

                # Upload policy.zip
                success, policy_url = upload_policy_zip_bytes(
                    file_bytes=policy_bytes,
                    filename="policy.zip",
                    upload_endpoint="http://<upload-host>:<port>/upload"
                )
                if not success:
                    return jsonify({"success": False, "error": f"Policy upload failed: {policy_url}"}), 500

                # Onboard policy
                policy_uri = onboard_policy_to_server(
                    name=template.template_id,
                    version="1.0",
                    release_tag="stable",
                    description=template.template_description,
                    code_url=policy_url,
                    metadata=template.template_metadata,
                )

                template.template_custom_validation_policy_rule_uri = policy_uri

            # Save to DB
            success, result = template_db.insert(template)
            if success:
                return jsonify({"success": True, "template_id": template.template_id}), 200
            else:
                return jsonify({"success": False, "error": result}), 500

    except Exception as e:
        logger.exception("Error uploading template")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/upload-workflow", methods=["POST"])
def upload_workflow():
    try:
        file = request.files["file"]
        if not file or not file.filename.endswith(".zip"):
            return jsonify({"success": False, "error": "Invalid or missing zip file"}), 400

        zip_bytes = file.read()
        zip_buffer = io.BytesIO(zip_bytes)

        with zipfile.ZipFile(zip_buffer) as z:
            # Parse workflow.json
            if "workflow.json" not in z.namelist():
                return jsonify({"success": False, "error": "Missing workflow.json"}), 400

            with z.open("workflow.json") as f:
                workflow_data = json.load(f)
            workflow = WorkflowObject.from_dict(workflow_data)

            # For collecting all generated spec URIs
            spec_uris = []

            # Process each folder entry in the zip
            for folder in set(name.split('/')[0] for name in z.namelist() if '/' in name):
                logger.info(f"Processing folder: {folder}")

                spec_path = f"{folder}/spec.json"
                if spec_path not in z.namelist():
                    logger.warning(
                        f"Skipping folder {folder}: missing spec.json")
                    continue

                with z.open(spec_path) as f:
                    spec_data = json.load(f)
                spec = SpecObject.from_dict(spec_data)

                # Onboard policy if needed
                rule_info = spec.backend_policy_rule_ids.get("default", {})
                if not rule_info.get("policyRuleURI"):
                    policy_zip_path = f"{folder}/policy.zip"
                    if policy_zip_path not in z.namelist():
                        return jsonify({"success": False, "error": f"Missing policy.zip for {folder}"}), 400
                    with z.open(policy_zip_path) as pf:
                        policy_bytes = pf.read()

                    success, policy_url = upload_policy_zip_bytes(
                        policy_bytes, "policy.zip")
                    if not success:
                        return jsonify({"success": False, "error": f"Policy upload failed for {folder}"}), 500

                    policy_uri = onboard_policy_to_server(
                        name=spec.spec_name,
                        version=spec.spec_version.version,
                        release_tag="stable",
                        description=spec.spec_description,
                        code_url=policy_url,
                        metadata=spec.spec_metadata,
                        tags=",".join(spec.spec_search_tags)
                    )
                    spec.backend_policy_rule_ids["default"]["policyRuleURI"] = policy_uri

                # Onboard template if present and needed
                template_path = f"{folder}/template.json"
                if template_path in z.namelist():
                    with z.open(template_path) as tf:
                        template_data = json.load(tf)
                    template = TemplateObject.from_dict(template_data)

                    if not template.template_custom_validation_policy_rule_uri:
                        template_zip_path = f"{folder}/template.zip"
                        if template_zip_path not in z.namelist():
                            return jsonify({"success": False, "error": f"Missing template.zip for {folder}"}), 400
                        with z.open(template_zip_path) as tpf:
                            template_bytes = tpf.read()

                        success, template_url = upload_policy_zip_bytes(
                            template_bytes, "template.zip")
                        if not success:
                            return jsonify({"success": False, "error": f"Template upload failed for {folder}"}), 500

                        policy_uri = onboard_policy_to_server(
                            name=template.template_id,
                            version="1.0",
                            release_tag="stable",
                            description=template.template_description,
                            code_url=template_url,
                            metadata=template.template_metadata
                        )
                        template.template_custom_validation_policy_rule_uri = policy_uri

                    # Save template
                    t_success, t_result = template_db.insert(template)
                    if not t_success:
                        return jsonify({"success": False, "error": t_result}), 500

                    # Link template to spec
                    spec.template_id = template.template_id

                # Save spec
                s_success, s_result = spec_db.insert(spec)
                if not s_success:
                    return jsonify({"success": False, "error": s_result}), 500

                spec_uris.append(spec.spec_uri)

            # Fill the spec URIs into the workflow object
            workflow.workflow_spec_ids = spec_uris

            # Save workflow
            w_success, w_result = workflow_db.insert(workflow)
            if not w_success:
                return jsonify({"success": False, "error": w_result}), 500

            return jsonify({
                "success": True,
                "workflow_uri": workflow.workflow_uri,
                "specs_uploaded": spec_uris
            })

    except Exception as e:
        logger.exception("Workflow upload failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/onboard-spec", methods=["POST"])
def onboard_spec():
    try:
        data = request.json
        spec = SpecObject.from_dict(data)

        # Onboard policy if missing
        rule_info = spec.backend_policy_rule_ids.get("default", {})
        if not rule_info.get("policyRuleURI"):
            # Requires: `code_url` in request
            code_url = data.get("policy_code_url")
            if not code_url:
                return jsonify({"success": False, "error": "Missing policy_code_url"}), 400

            policy_uri = onboard_policy_to_server(
                name=spec.spec_name,
                version=spec.spec_version.version,
                release_tag="stable",
                description=spec.spec_description,
                code_url=code_url,
                metadata=spec.spec_metadata,
                tags=",".join(spec.spec_search_tags)
            )
            spec.backend_policy_rule_ids["default"]["policyRuleURI"] = policy_uri

        success, result = spec_db.insert(spec)
        if success:
            return jsonify({"success": True, "spec_uri": spec.spec_uri}), 200
        else:
            return jsonify({"success": False, "error": result}), 500

    except Exception as e:
        logger.exception("Spec onboarding failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/onboard-template", methods=["POST"])
def onboard_template():
    try:
        data = request.json
        template = TemplateObject.from_dict(data)

        # Onboard template validation policy if missing
        if not template.template_custom_validation_policy_rule_uri:
            code_url = data.get("policy_code_url")
            if not code_url:
                return jsonify({"success": False, "error": "Missing policy_code_url"}), 400

            policy_uri = onboard_policy_to_server(
                name=template.template_id,
                version="1.0",
                release_tag="stable",
                description=template.template_description,
                code_url=code_url,
                metadata=template.template_metadata
            )
            template.template_custom_validation_policy_rule_uri = policy_uri

        success, result = template_db.insert(template)
        if success:
            return jsonify({"success": True, "template_id": template.template_id}), 200
        else:
            return jsonify({"success": False, "error": result}), 500

    except Exception as e:
        logger.exception("Template onboarding failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/onboard-workflow", methods=["POST"])
def onboard_workflow():
    try:
        data = request.json
        workflow_data = data.get("workflow")
        specs_data = data.get("specs", [])

        if not workflow_data or not specs_data:
            return jsonify({"success": False, "error": "Missing workflow or specs"}), 400

        spec_uris = []

        for spec_dict in specs_data:
            spec = SpecObject.from_dict(spec_dict)

            # Onboard policy if needed
            rule_info = spec.backend_policy_rule_ids.get("default", {})
            if not rule_info.get("policyRuleURI"):
                code_url = spec_dict.get("policy_code_url")
                if not code_url:
                    return jsonify({"success": False, "error": f"Missing policy_code_url for spec {spec.spec_name}"}), 400

                policy_uri = onboard_policy_to_server(
                    name=spec.spec_name,
                    version=spec.spec_version.version,
                    release_tag="stable",
                    description=spec.spec_description,
                    code_url=code_url,
                    metadata=spec.spec_metadata,
                    tags=",".join(spec.spec_search_tags)
                )
                spec.backend_policy_rule_ids["default"]["policyRuleURI"] = policy_uri

            # Onboard template if inline
            if "template" in spec_dict:
                template = TemplateObject.from_dict(spec_dict["template"])

                if not template.template_custom_validation_policy_rule_uri:
                    code_url = spec_dict["template"].get("policy_code_url")
                    if not code_url:
                        return jsonify({"success": False, "error": f"Missing template policy_code_url for {template.template_id}"}), 400

                    policy_uri = onboard_policy_to_server(
                        name=template.template_id,
                        version="1.0",
                        release_tag="stable",
                        description=template.template_description,
                        code_url=code_url,
                        metadata=template.template_metadata
                    )
                    template.template_custom_validation_policy_rule_uri = policy_uri

                t_success, t_result = template_db.insert(template)
                if not t_success:
                    return jsonify({"success": False, "error": t_result}), 500

                spec.template_id = template.template_id

            # Save spec
            s_success, s_result = spec_db.insert(spec)
            if not s_success:
                return jsonify({"success": False, "error": s_result}), 500

            spec_uris.append(spec.spec_uri)

        workflow = WorkflowObject.from_dict(workflow_data)
        workflow.workflow_spec_ids = spec_uris

        w_success, w_result = workflow_db.insert(workflow)
        if not w_success:
            return jsonify({"success": False, "error": w_result}), 500

        return jsonify({
            "success": True,
            "workflow_uri": workflow.workflow_uri,
            "specs_uploaded": spec_uris
        })

    except Exception as e:
        logger.exception("Workflow onboarding failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/export-workflow/<workflow_uri>", methods=["GET"])
def export_full_workflow(workflow_uri):
    try:
        # Fetch workflow
        success, workflow_obj = workflow_db.get_by_workflow_uri(workflow_uri)
        if not success:
            return jsonify({"success": False, "error": workflow_obj}), 404

        # Prepare temporary directory
        temp_dir = tempfile.TemporaryDirectory()
        zip_path = os.path.join(temp_dir.name, "workflow_export.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add workflow.json
            workflow_json = workflow_obj.to_dict()
            zipf.writestr("workflow.json", json.dumps(workflow_json, indent=2))

            # Process each spec
            for spec_uri in workflow_obj.workflow_spec_ids:
                s_success, spec_obj = spec_db.get_by_spec_uri(spec_uri)
                if not s_success:
                    continue  # skip on failure

                folder = spec_obj.spec_name.replace(" ", "_")
                zipf.writestr(f"{folder}/spec.json", json.dumps(spec_obj.to_dict(), indent=2))

                # Check for template
                if spec_obj.template_id:
                    t_success, template_obj = template_db.get_by_template_id(spec_obj.template_id)
                    if t_success:
                        zipf.writestr(f"{folder}/template.json", json.dumps(template_obj.to_dict(), indent=2))

        # Send in-memory file
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"{workflow_uri.replace(':', '_')}.zip",
            mimetype="application/zip"
        )

    except Exception as e:
        logger.exception("Workflow export failed")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/workflow/full/<workflow_uri>", methods=["GET"])
def get_full_workflow_json(workflow_uri):
    try:
        # Fetch the workflow
        success, workflow_obj = workflow_db.get_by_workflow_uri(workflow_uri)
        if not success:
            return jsonify({"success": False, "error": workflow_obj}), 404

        # Prepare full structure
        full_output = {
            "workflow": workflow_obj.to_dict(),
            "specs": []
        }

        # Loop through each spec URI
        for spec_uri in workflow_obj.workflow_spec_ids:
            s_success, spec_obj = spec_db.get_by_spec_uri(spec_uri)
            if not s_success:
                continue  # Skip if spec not found

            spec_dict = spec_obj.to_dict()

            # Attach template if specified
            template_data = None
            if spec_obj.template_id:
                t_success, template_obj = template_db.get_by_template_id(spec_obj.template_id)
                if t_success:
                    template_data = template_obj.to_dict()

            if template_data:
                spec_dict["template"] = template_data

            full_output["specs"].append(spec_dict)

        return jsonify({"success": True, "data": full_output}), 200

    except Exception as e:
        logger.exception("Failed to fetch full workflow JSON")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/spec/<spec_uri>", methods=["GET"])
def get_spec(spec_uri):
    success, result = spec_db.get_by_spec_uri(spec_uri)
    return jsonify({"success": success, "data": result if success else None, "error": None if success else result})


@app.route("/spec/<spec_uri>", methods=["PUT"])
def update_spec(spec_uri):
    try:
        update_fields = request.json
        success, result = spec_db.update(spec_uri, update_fields)
        return jsonify({"success": success, "updated": result if success else None, "error": None if success else result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/spec/<spec_uri>", methods=["DELETE"])
def delete_spec(spec_uri):
    success, result = spec_db.delete(spec_uri)
    return jsonify({"success": success, "deleted": result if success else None, "error": None if success else result})


@app.route("/spec/query", methods=["POST"])
def query_specs():
    try:
        query_filter = request.json
        success, result = spec_db.query(query_filter)
        return jsonify({"success": success, "results": result if success else None, "error": None if success else result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/template/<template_id>", methods=["GET"])
def get_template(template_id):
    success, result = template_db.get_by_template_id(template_id)
    return jsonify({"success": success, "data": result if success else None, "error": None if success else result})


@app.route("/template/<template_id>", methods=["PUT"])
def update_template(template_id):
    try:
        update_fields = request.json
        success, result = template_db.update(template_id, update_fields)
        return jsonify({"success": success, "updated": result if success else None, "error": None if success else result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/template/<template_id>", methods=["DELETE"])
def delete_template(template_id):
    success, result = template_db.delete(template_id)
    return jsonify({"success": success, "deleted": result if success else None, "error": None if success else result})


@app.route("/template/query", methods=["POST"])
def query_templates():
    try:
        query_filter = request.json
        success, result = template_db.query(query_filter)
        return jsonify({"success": success, "results": result if success else None, "error": None if success else result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/workflow/<workflow_uri>", methods=["GET"])
def get_workflow(workflow_uri):
    success, result = workflow_db.get_by_workflow_uri(workflow_uri)
    return jsonify({"success": success, "data": result if success else None, "error": None if success else result})


@app.route("/workflow/<workflow_uri>", methods=["PUT"])
def update_workflow(workflow_uri):
    try:
        update_fields = request.json
        success, result = workflow_db.update(workflow_uri, update_fields)
        return jsonify({"success": success, "updated": result if success else None, "error": None if success else result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/workflow/<workflow_uri>", methods=["DELETE"])
def delete_workflow(workflow_uri):
    success, result = workflow_db.delete(workflow_uri)
    return jsonify({"success": success, "deleted": result if success else None, "error": None if success else result})


@app.route("/workflow/query", methods=["POST"])
def query_workflows():
    try:
        query_filter = request.json
        success, result = workflow_db.query(query_filter)
        return jsonify({"success": success, "results": result if success else None, "error": None if success else result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



@app.route("/dsl-executor", methods=["POST"])
def create_dsl_executor():
    try:
        data = request.json
        if "cluster_public_ip" not in data:
            return jsonify({"success": False, "message": "cluster_public_ip is required"}), 400

        data["executor_host_uri"] = f"http://{data['cluster_public_ip']}:31080"
        executor = DSLExecutors.from_dict(data)
        success = ExecutorsDB().create(executor)
        if success:
            return jsonify({"success": True, "data": "DSL Executor created successfully."})
        return jsonify({"success": False, "message": "Failed to create DSL Executor."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/<executor_id>", methods=["GET"])
def read_dsl_executor(executor_id):
    try:
        executor = ExecutorsDB().read(executor_id)
        if executor:
            return jsonify({"success": True, "data": executor.to_dict()})
        return jsonify({"success": False, "message": "DSL Executor not found."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/<executor_id>", methods=["PUT"])
def update_dsl_executor(executor_id):
    try:
        data = request.json
        updated_executor = DSLExecutors.from_dict(data)
        success = ExecutorsDB().update(executor_id, updated_executor)
        if success:
            return jsonify({"success": True, "data": "DSL Executor updated successfully."})
        return jsonify({"success": False, "message": "Failed to update DSL Executor."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/<executor_id>", methods=["DELETE"])
def delete_dsl_executor(executor_id):
    try:
        success = ExecutorsDB().delete(executor_id)
        if success:
            return jsonify({"success": True, "data": "DSL Executor deleted successfully."})
        return jsonify({"success": False, "message": "Failed to delete DSL Executor."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/query", methods=["POST"])
def query_dsl_executors():
    try:
        query_filter = request.json or {}
        executors = ExecutorsDB().query(query_filter)
        return jsonify({"success": True, "data": [e.to_dict() for e in executors]})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/<executor_id>/create-infra", methods=["POST"])
def create_dsl_executor_infra(executor_id):
   
    try:
        data = request.json or {}
        initializer = DSLExecutorInitializer(**data, executor_id=executor_id)
        initializer.create_executor()
        return jsonify({"success": True, "message": "DSL executor infra created successfully."})
    except Exception as e:
        logger.error(f"Error creating DSL executor infra: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/<executor_id>/remove-infra", methods=["DELETE"])
def remove_dsl_executor_infra(executor_id):
   
    try:
        data = request.json or {}
        initializer = DSLExecutorInitializer(**data, executor_id=executor_id)
        initializer.remove_executor()
        return jsonify({"success": True, "message": "DSL executor infra removed successfully."})
    except Exception as e:
        logger.error(f"Error removing DSL executor infra: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


def _get_workflow_client_for_executor(executor_id: str) -> WorkflowExecutorClient:
   
    executor = ExecutorsDB().read(executor_id)
    if not executor:
        raise ValueError("DSL Executor not found")

    if not getattr(executor, "executor_host_uri", None):
        raise ValueError("executor_host_uri is missing for this DSL Executor")

    return WorkflowExecutorClient(base_url=executor.executor_host_uri)


@app.route("/dsl-executor/<executor_id>/workflow/execute", methods=["POST"])
def dsl_executor_workflow_execute(executor_id):
   
    try:
        data = request.json or {}
        workflow_uri = data.get("workflow_uri")
        if not workflow_uri:
            return jsonify({"success": False, "message": "workflow_uri is required"}), 400

        input_data = data.get("input_data") or {}
        wait = bool(data.get("wait", False))
        pin_id = data.get("pin_id")

        client = _get_workflow_client_for_executor(executor_id)
        result = client.execute(workflow_uri=workflow_uri, input_data=input_data, wait=wait, pin_id=pin_id)
        return jsonify({"success": True, "data": result})
    except ValueError as ve:
        logger.error(f"[workflow/execute] {ve}")
        return jsonify({"success": False, "message": str(ve)}), 404
    except Exception as e:
        logger.error(f"[workflow/execute] error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/<executor_id>/workflow/slots/update", methods=["POST"])
def dsl_executor_workflow_slots_update(executor_id):
   
    try:
        data = request.json or {}
        free_slots = data.get("free_slots", None)
        pinned_slots = data.get("pinned_slots", None)

        if free_slots is None and pinned_slots is None:
            return jsonify({"success": False, "message": "Provide at least one of free_slots or pinned_slots."}), 400

        client = _get_workflow_client_for_executor(executor_id)
        msg = client.update_slots(
            free_slots=int(free_slots) if free_slots is not None else None,
            pinned_slots=int(pinned_slots) if pinned_slots is not None else None,
        )
        return jsonify({"success": True, "message": msg or "Slots updated"})
    except ValueError as ve:
        # includes executor not found and validation errors
        logger.error(f"[workflow/slots/update] {ve}")
        # if it's executor not found -> 404, else 400; to keep simple, 400 unless "not found"
        status = 404 if "not found" in str(ve).lower() else 400
        return jsonify({"success": False, "message": str(ve)}), status
    except Exception as e:
        logger.error(f"[workflow/slots/update] error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/<executor_id>/workflow/slots/pin", methods=["POST"])
def dsl_executor_workflow_slots_pin(executor_id):
   
    try:
        data = request.json or {}
        pin_id = data.get("pin_id", None)

        client = _get_workflow_client_for_executor(executor_id)
        generated_pin_id = client.create_pinned_slot(pin_id=pin_id)
        return jsonify({"success": True, "pin_id": generated_pin_id})
    except ValueError as ve:
        logger.error(f"[workflow/slots/pin] {ve}")
        return jsonify({"success": False, "message": str(ve)}), 404
    except Exception as e:
        logger.error(f"[workflow/slots/pin] error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/dsl-executor/<executor_id>/workflow/track/<input_id>", methods=["GET"])
def dsl_executor_workflow_track(executor_id, input_id):
   
    try:
        client = _get_workflow_client_for_executor(executor_id)
        data = client.get_tracking_data(input_id=input_id)
        return jsonify({"success": True, "data": data})
    except ValueError as ve:
        logger.error(f"[workflow/track] {ve}")
        return jsonify({"success": False, "message": str(ve)}), 404
    except Exception as e:
        logger.error(f"[workflow/track] error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


def run_app():
    app.run(host='0.0.0.0', port=9000)
