import os
import asyncio
import json
import websockets
from websockets.exceptions import WebSocketException
import threading
import logging

from dsl_executor import new_dsl_workflow_executor, parse_dsl_output
from .db import RuntimeSubjectsDB, SubjectsDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def query_translator(query):
    def translate_condition(condition):
        if "logicalOperator" in condition:
            return translate_logical_operator(condition)
        else:
            return translate_simple_condition(condition)

    def translate_simple_condition(condition):
        variable = condition["variable"]
        operator = condition["operator"]
        value = condition["value"]

        if operator == "LIKE":
            # MongoDB uses regex for LIKE operations
            regex_value = value.replace(".", r"\.").replace("*", ".*")
            return {variable: {"$regex": regex_value}}
        elif operator == "==":
            return {variable: value}
        elif operator == "IN":
            return {variable: {"$in": value}}
        elif operator == "<":
            return {variable: {"$lt": value}}
        elif operator == "<=":
            return {variable: {"$lte": value}}
        elif operator == ">":
            return {variable: {"$gt": value}}
        elif operator == ">=":
            return {variable: {"$gte": value}}
        else:
            raise ValueError(f"Unsupported operator: {operator}")

    def translate_logical_operator(condition):
        logical_operator = condition["logicalOperator"]
        sub_conditions = condition["conditions"]
        translated_conditions = [translate_condition(
            cond) for cond in sub_conditions]

        if logical_operator == "AND":
            return {"$and": translated_conditions}
        elif logical_operator == "OR":
            return {"$or": translated_conditions}
        else:
            raise ValueError(
                f"Unsupported logical operator: {logical_operator}")

    return translate_condition(query)


class Search:

    def __init__(self, workflow_id: str, search_query: dict) -> None:
        self.workflow_id = workflow_id
        self.search_query = search_query
        self.subjects_db = SubjectsDB()
        self.runtime_db = RuntimeSubjectsDB()
        self.dsl_workflow = new_dsl_workflow_executor(
            workflow_id,
            workflows_base_uri=os.getenv("DSL_DB_URL")
        )

    def filter_runtime_db(self):
        try:

            translated_query = query_translator(self.search_query)
            results = self.runtime_db.query_subjects(translated_query)

            return results

        except Exception as e:
            raise e

    def filter_db(self):
        try:
            translated_query = query_translator(self.search_query)
            results = self.subjects_db.query_subjects(translated_query)

            return results
        except Exception as e:
            raise e

    def search_runtime_db(self):
        try:

            filter_results = self.filter_runtime_db()

            full_result = self.dsl_workflow.execute({
                "data": filter_results
            })

            return parse_dsl_output(full_result, "")

        except Exception as e:
            raise e

    def search_db(self):
        try:
            filter_results = self.filter_db()

            full_result = self.dsl_workflow.execute({
                "data": filter_results
            })

            return parse_dsl_output(full_result, "")
        except Exception as e:
            raise e


async def handle_client(websocket, path):
    try:
        async for message in websocket:
            try:
                payload = json.loads(message)
                search_type = payload.get("search_type")
                workflow_id = payload.get("workflow_id", "")
                search_query = payload.get("query", {})

                if search_type not in {"registry", "runtime_db"}:
                    await websocket.send(
                        json.dumps(
                            {"success": False, "error": "Invalid search_type"})
                    )
                    continue

                search = Search(workflow_id, search_query)

                if workflow_id:
                    if search_type == "registry":
                        result = search.search_db()
                    else:
                        result = search.search_runtime_db()
                else:
                    if search_type == "registry":
                        result = search.filter_db()
                    else:
                        result = search.filter_runtime_db()

                await websocket.send(json.dumps({"success": True, "data": result}))

            except Exception as e:
                error_message = str(e)
                await websocket.send(
                    json.dumps({"success": False, "error": error_message})
                )

    except WebSocketException as ws_error:
        print(f"WebSocket error: {ws_error}")
    except Exception as e:
        print(f"Unexpected error: {e}")


async def run_server():
    server = await websockets.serve(handle_client, "0.0.0.0", 5001)
    logger.info("WebSocket server started on ws://0.0.0.0:5001")
    await server.wait_closed()


def run_search_server():
    def start_server():
        asyncio.run(run_server())

    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    logger.info("WebSocket server started in a separate thread.")
