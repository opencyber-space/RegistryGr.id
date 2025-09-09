import logging
import os
from typing import Optional, Dict, List
from kubernetes import client, config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Exported env variables ---
POLICY_DB_URL = os.getenv("POLICY_DB_URL")
WORKFLOW_CLIENT_URL = os.getenv("WORKFLOW_CLIENT_URL", "http://localhost:9000")
FREE_SLOTS = int(os.getenv("FREE_SLOTS", "2"))
PINNED_SLOTS = int(os.getenv("PINNED_SLOTS", "2"))
PORT = int(os.getenv("PORT", "8080"))  # default 8080
CONTAINER_IMAGE_NAME = os.getenv("EXECUTOR_CONTAINER_IMAGE_NAME", "")
JOB_POLL_INTERVAL = int(os.getenv("JOB_POLL_INTERVAL", 2))
JOB_MAX_RETRIES = int(os.getenv("JOB_MAX_RETRIES", 300))


class DSLExecutorInitializer:

    def __init__(
        self,
        cluster_config: dict,
        executor_id: Optional[str],
        free_slots: int = FREE_SLOTS,
        pinned_slots: int = PINNED_SLOTS,
        port: int = PORT,
        *,
        namespace: str = "dsl-system",
        image: str = CONTAINER_IMAGE_NAME,
        replicas: int = 1,
        job_poll_interval=JOB_POLL_INTERVAL,
        job_max_retries=JOB_MAX_RETRIES,
        labels: Optional[Dict[str, str]] = None,
        annotations: Optional[Dict[str, str]] = None,
        extra_env: Optional[Dict[str, str]] = None,
    ):
        if not executor_id:
            raise ValueError(
                "EXECUTOR_ID is required (pass as parameter or set env EXECUTOR_ID).")

        self.executor_id = executor_id
        self.namespace = namespace
        self.image = image
        self.replicas = replicas
        self.port = int(port)
        self.free_slots = int(free_slots)
        self.pinned_slots = int(pinned_slots)
        self.labels = {"app": f"dsl-executor-{executor_id}", **(labels or {})}
        self.annotations = annotations or {}
        self.deployment_name = f"dsl-executor-{executor_id}"
        self.service_name = f"dsl-executor-svc-{executor_id}"
        self.extra_env = extra_env or {}
        self.job_poll_interval = job_poll_interval
        self.job_max_retries = job_max_retries

        self.node_port_http = 31080

        try:
            self._load_cluster_config(cluster_config)
            self.apps_v1 = client.AppsV1Api()
            self.core_v1 = client.CoreV1Api()
            self._ensure_namespace()
        except Exception as e:
            logger.error(f"Error loading cluster config: {e}")
            raise

    def create_executor(self):
        try:
            self._create_deployment()
            self._create_service()
        except Exception as e:
            logger.error(f"Error creating DSL executor resources: {e}")
            raise

    def remove_executor(self):
        try:
            self._delete_deployment()
            self._delete_service()
        except Exception as e:
            logger.error(f"Error removing DSL executor resources: {e}")
            raise

    def _load_cluster_config(self, cluster_config: dict):
        config.load_kube_config_from_dict(cluster_config)

    def _ensure_namespace(self):
        try:
            self.core_v1.read_namespace(name=self.namespace)
            logger.info(f"Namespace {self.namespace} already exists.")
        except Exception:
            logger.info(f"Namespace {self.namespace} not found. Creating it.")
            ns_body = client.V1Namespace(
                metadata=client.V1ObjectMeta(name=self.namespace))
            self.core_v1.create_namespace(body=ns_body)
            logger.info(f"Namespace {self.namespace} created successfully.")

    def _container_env(self) -> List[client.V1EnvVar]:
        envs = [
            client.V1EnvVar(name="POLICY_DB_URL", value=POLICY_DB_URL or ""),
            client.V1EnvVar(name="WORKFLOW_CLIENT_URL", value=WORKFLOW_CLIENT_URL),
            client.V1EnvVar(name="FREE_SLOTS", value=str(self.free_slots)),
            client.V1EnvVar(name="PINNED_SLOTS", value=str(self.pinned_slots)),
            client.V1EnvVar(name="PORT", value=str(self.port)),
            client.V1EnvVar(name="EXECUTOR_ID", value=str(self.executor_id)),
            client.V1EnvVar(name="JOB_POLL_INTERVAL", value=str(self.job_poll_interval)),
            client.V1EnvVar(name="JOB_MAX_RETRIES", value=str(self.job_max_retries))
        ]

        for k, v in self.extra_env.items():
            envs.append(client.V1EnvVar(name=k, value=str(v)))
        return envs

    def _create_deployment(self):
        try:
            container = client.V1Container(
                name=self.deployment_name,
                image=self.image,
                env=self._container_env(),
                ports=[client.V1ContainerPort(container_port=self.port)],
            )

            pod_meta = client.V1ObjectMeta(
                labels=self.labels, annotations=self.annotations)
            pod_spec = client.V1PodSpec(containers=[container])

            template = client.V1PodTemplateSpec(
                metadata=pod_meta, spec=pod_spec)

            spec = client.V1DeploymentSpec(
                replicas=self.replicas,
                selector=client.V1LabelSelector(
                    match_labels={"app": self.labels["app"]}),
                template=template,
            )

            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(
                    name=self.deployment_name, namespace=self.namespace),
                spec=spec,
            )

            self.apps_v1.create_namespaced_deployment(
                namespace=self.namespace, body=deployment)
            logger.info(
                f"Deployment {self.deployment_name} created successfully.")
        except Exception as e:
            logger.error(f"Error creating deployment: {e}")
            raise

    def _create_service(self):
        try:
            ports = [
                client.V1ServicePort(
                    name="http",
                    port=self.port,
                    target_port=self.port,
                    node_port=self.node_port_http,
                )
            ]

            spec = client.V1ServiceSpec(
                selector={"app": self.labels["app"]},
                type="NodePort",
                ports=ports,
            )

            service = client.V1Service(
                api_version="v1",
                kind="Service",
                metadata=client.V1ObjectMeta(
                    name=self.service_name, namespace=self.namespace),
                spec=spec,
            )

            self.core_v1.create_namespaced_service(
                namespace=self.namespace, body=service)
            logger.info(
                f"Service {self.service_name} created successfully with NodePort {self.node_port_http}.")
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            raise

    def _delete_deployment(self):
        try:
            self.apps_v1.delete_namespaced_deployment(
                name=self.deployment_name, namespace=self.namespace)
            logger.info(
                f"Deployment {self.deployment_name} deleted successfully.")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.info(
                    f"Deployment {self.deployment_name} not found; skipping.")
            else:
                raise

    def _delete_service(self):
        try:
            self.core_v1.delete_namespaced_service(
                name=self.service_name, namespace=self.namespace)
            logger.info(f"Service {self.service_name} deleted successfully.")
        except client.exceptions.ApiException as e:
            if e.status == 404:
                logger.info(
                    f"Service {self.service_name} not found; skipping.")
            else:
                raise
