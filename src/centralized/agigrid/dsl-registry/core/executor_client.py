import os
import uuid
import logging
from typing import Any, Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class WorkflowExecutorClient:
   

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 15.0,
        api_key: Optional[str] = None,
        retries: int = 3,
        backoff_factor: float = 0.3,
    ):
       
        self.base_url = (base_url or os.getenv("WORKFLOW_EXECUTOR_URL", "")).rstrip("/")
        if not self.base_url:
            raise ValueError("base_url is required (or set WORKFLOW_EXECUTOR_URL).")

        self.timeout = timeout
        self.session = requests.Session()

        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET", "POST"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    # ---------- Helpers ----------

    def _post(self, path: str, json: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.post(url, json=json, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("POST %s failed: %s | payload=%s", url, e, json)
            raise

        if not isinstance(data, dict) or not data.get("success", False):
            msg = data.get("error") if isinstance(data, dict) else f"Non-JSON response: {resp.text[:200]}"
            logger.error("POST %s returned error: %s", url, msg)
            raise RuntimeError(msg or "Request failed")

        return data

    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, headers=self.headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("GET %s failed: %s", url, e)
            raise

        if not isinstance(data, dict) or not data.get("success", False):
            msg = data.get("error") if isinstance(data, dict) else f"Non-JSON response: {resp.text[:200]}"
            logger.error("GET %s returned error: %s", url, msg)
            raise RuntimeError(msg or "Request failed")

        return data


    def execute(
        self,
        workflow_uri: str,
        input_data: Optional[Dict[str, Any]] = None,
        wait: bool = False,
        pin_id: Optional[str] = None,
    ) -> Any:
       
        payload = {
            "workflow_uri": workflow_uri,
            "input_data": input_data or {},
            "wait": wait,
        }
        if pin_id:
            payload["pin_id"] = pin_id

        data = self._post("/execute", json=payload)
        return data.get("result")

    def update_slots(self, free_slots: Optional[int] = None, pinned_slots: Optional[int] = None) -> str:
        
        if free_slots is None and pinned_slots is None:
            raise ValueError("Provide at least one of free_slots or pinned_slots.")

        payload: Dict[str, Any] = {}
        if free_slots is not None:
            if free_slots < 0:
                raise ValueError("free_slots must be >= 0")
            payload["free_slots"] = free_slots
        if pinned_slots is not None:
            if pinned_slots < 0:
                raise ValueError("pinned_slots must be >= 0")
            payload["pinned_slots"] = pinned_slots

        data = self._post("/slots/update", json=payload)
        return data.get("message", "")

    def create_pinned_slot(self, pin_id: Optional[str] = None) -> str:
        
        payload = {}
        if pin_id:
            payload["pin_id"] = pin_id
        else:
            # You can still let the server generate it; this ensures you can track locally if needed.
            payload["pin_id"] = str(uuid.uuid4())

        data = self._post("/slots/pin", json=payload)
        return data.get("pin_id", payload["pin_id"])

    def get_tracking_data(self, input_id: str) -> Any:
        
        data = self._get(f"/track/{input_id}")
        return data.get("data")
