from flask import Flask, request, jsonify
import logging

from .db import SubjectsDB, RuntimeSubjectsDB
from .db import update_orgs_for_subject, create_runtime_version_of_subject
from .search import run_search_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def response(success, data=None, message=None):
    if success:
        return jsonify({"success": True, "data": data})
    else:
        return jsonify({"success": False, "message": message})


subjects_db = SubjectsDB()
runtime_subjects_db = RuntimeSubjectsDB()

# Subject APIs


@app.route('/subjects/<string:subject_id>', methods=['GET'])
def get_subject(subject_id):
    try:
        subject = subjects_db.get_subject(subject_id)
        if subject:
            return response(True, subject.to_dict())
        return response(False, message="Subject not found")
    except Exception as e:
        return response(False, message=str(e))


@app.route('/subjects/<string:subject_id>', methods=['PUT'])
def update_subject(subject_id):
    try:
        updated_data = request.json
        if subjects_db.update_subject(subject_id, updated_data):
            return response(True, data="Subject updated successfully")
        return response(False, message="Subject not found")
    except Exception as e:
        return response(False, message=str(e))


@app.route('/subjects/<string:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    try:
        if subjects_db.delete_subject(subject_id):
            return response(True, data="Subject deleted successfully")
        return response(False, message="Subject not found")
    except Exception as e:
        return response(False, message=str(e))


@app.route('/subjects', methods=['GET'])
def list_subjects():
    try:
        subjects = subjects_db.list_subjects()
        return response(True, [subject.to_dict() for subject in subjects])
    except Exception as e:
        return response(False, message=str(e))


@app.route('/subjects/query', methods=['POST'])
def query_subjects():
    try:
        query = request.json
        subjects = subjects_db.query_subjects(query)
        return response(True, [subject.to_dict() for subject in subjects])
    except Exception as e:
        return response(False, message=str(e))


# RuntimeSubject APIs
@app.route('/runtime_subjects/<string:subject_id>', methods=['GET'])
def get_runtime_subject(subject_id):
    try:
        runtime_subject = runtime_subjects_db.get_runtime_subject(subject_id)
        if runtime_subject:
            return response(True, runtime_subject.to_dict())
        return response(False, message="RuntimeSubject not found")
    except Exception as e:
        return response(False, message=str(e))


@app.route('/runtime_subjects/<string:subject_id>', methods=['PUT'])
def update_runtime_subject(subject_id):
    try:
        updated_data = request.json
        if runtime_subjects_db.update_runtime_subject(subject_id, updated_data):
            return response(True, data="RuntimeSubject updated successfully")
        return response(False, message="RuntimeSubject not found")
    except Exception as e:
        return response(False, message=str(e))


@app.route('/runtime_subjects/<string:subject_id>', methods=['DELETE'])
def delete_runtime_subject(subject_id):
    try:
        if runtime_subjects_db.delete_runtime_subject(subject_id):
            return response(True, data="RuntimeSubject deleted successfully")
        return response(False, message="RuntimeSubject not found")
    except Exception as e:
        return response(False, message=str(e))


@app.route('/runtime_subjects', methods=['GET'])
def list_runtime_subjects():
    try:
        runtime_subjects = runtime_subjects_db.list_runtime_subjects()
        return response(True, [runtime_subject.to_dict() for runtime_subject in runtime_subjects])
    except Exception as e:
        return response(False, message=str(e))


@app.route('/runtime_subjects/query', methods=['POST'])
def query_runtime_subjects():
    try:
        query = request.json
        runtime_subjects = runtime_subjects_db.query_runtime_subjects(query)
        return response(True, [runtime_subject.to_dict() for runtime_subject in runtime_subjects])
    except Exception as e:
        return response(False, message=str(e))


@app.route('/runtime_subjects/create', methods=['POST'])
def create_runtime_version():
    try:
        data = request.json
        subject_id = data.get('subject_id')
        runtime_data = data.get('runtime_data', {})
        if not subject_id:
            return response(False, message="subject_id is required")
        if create_runtime_version_of_subject(subject_id, runtime_data):
            return response(True, message="Runtime version of subject created successfully")
        return response(False, message="Failed to create runtime version of subject")
    except Exception as e:
        return response(False, message=str(e))


# API to Update Orgs for Runtime Subject
@app.route('/runtime_subjects/<string:subject_id>/orgs', methods=['PUT'])
def update_orgs(subject_id):
    try:
        data = request.json
        orgs_to_add = data.get('orgs_to_add', [])
        orgs_to_remove = data.get('orgs_to_remove', [])
        if update_orgs_for_subject(subject_id, orgs_to_add, orgs_to_remove):
            return response(True, message="Organizations updated successfully")
        return response(False, message="Failed to update organizations")
    except Exception as e:
        return response(False, message=str(e))


def run_server():
    run_search_server()
    logger.info("starting REST API server on port 5000")
    app.run(host='0.0.0.0', port=5000)
