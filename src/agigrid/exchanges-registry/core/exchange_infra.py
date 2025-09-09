import os
import json
from flask import jsonify
import time
import logging
from typing import Optional, Dict,  Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from .schema import Exchange

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class JobExchangeInfraCreator:
 
    def __init__(
        self,
        kubeconfig: Dict,
        namespace: str,
        deployment_name: str,
        storage_size: str,
        node_port: Optional[int],
        use_static_pv: bool = True,
        storage_class_name: Optional[str] = None,
        mongo_host_path: Optional[str] = None,     
        mongo_node_name: Optional[str] = None,  
        stats_collection_interval: int = 60,
        stats_flush_interval: int = 60,
        stats_report_interval: int = 60,
        job_assignment_policy_rule_uri: str = "",
        job_assignment_policy_parameters: Optional[dict] = None,
        exchange_subject_association_policy_rule_uri: str = "",
        exchange_subject_association_policy_parameters: Optional[dict] = None,
        # Wait settings
        pvc_bound_timeout_s: int = 120,
        deployment_ready_timeout_s: int = 240,
    ):
        # Basic fields
        self.namespace = namespace
        self.deployment_name = deployment_name
        self.storage_size = storage_size
        self.use_static_pv = use_static_pv
        self.storage_class_name = storage_class_name
        self.mongo_host_path = mongo_host_path or f"/home/ubuntu/{namespace}/{deployment_name}"
        self.mongo_node_name = mongo_node_name
        self.pvc_bound_timeout_s = pvc_bound_timeout_s
        self.deployment_ready_timeout_s = deployment_ready_timeout_s

        # Names
        self.mongo_pv_name = f"{deployment_name}-exchange-pv"
        self.mongo_pvc_name = f"{deployment_name}-exchange-storage"
        self.mongo_dep_name = f"{deployment_name}-exchange-storage"
        self.mongo_svc_name = f"{deployment_name}-exchange-storage-svc"

        self.exchange_dep_name = f"{deployment_name}-exchange-service"
        self.exchange_svc_name = f"{deployment_name}-exchange-service-svc"

        # NodePort – validate (or allow cluster to allocate if None)
        self.node_port = self._validate_node_port(node_port)

        # Images and external envs
        self.exchange_image = os.getenv("EXCHANGE_IMAGE_NAME")
        if not self.exchange_image:
            raise ValueError("EXCHANGE_IMAGE_NAME env var is required for the exchange-service image.")

        # Required-by-spec envs (from runtime env)
        self.policy_db_url = os.getenv("POLICY_DB_URL", "")
        self.stats_reporting_destination_url = os.getenv("STATS_REPORTING_DESTINATION_URL", "")

        # Exchange envs (constructor-driven)
        self.exchange_envs = {
            "STATS_COLLECTION_INTERVAL": str(stats_collection_interval),
            "STATS_FLUSH_INTERVAL": str(stats_flush_interval),
            "STATS_REPORT_INTERVAL": str(stats_report_interval),
            "JOB_ASSIGNMENT_POLICY_RULE_URI": job_assignment_policy_rule_uri,
            "JOB_ASSIGNMENT_POLICY_PARAMETERS": json.dumps(job_assignment_policy_parameters or {}),
            "EXCHANGE_SUBJECT_ASSOCIATION_POLICY_RULE_URI": exchange_subject_association_policy_rule_uri,
            "EXCHANGE_SUBJECT_ASSOCIATION_POLICY_PARAMETERS": json.dumps(
                exchange_subject_association_policy_parameters or {}
            ),
        }

        # K8s clients
        config.load_kube_config_from_dict(kubeconfig)
        self.core = client.CoreV1Api()
        self.apps = client.AppsV1Api()

    def create(self):
        self._ensure_namespace()

        # Mongo: PV (optional), PVC, Deployment, Service
        if self.use_static_pv and not self.storage_class_name:
            self._create_mongo_pv()
        self._create_mongo_pvc()
        mongo_url = self._create_mongo_deployment_and_service()

        # Exchange: Deployment + NodePort Service
        self._create_exchange_deployment_and_service(mongo_url)

        logger.info("Create flow complete.")

    def remove(self):
        # Exchange first
        self._delete_deployment(self.exchange_dep_name)
        self._delete_service(self.exchange_svc_name)

        # Mongo next (reverse of create)
        self._delete_deployment(self.mongo_dep_name)
        self._delete_service(self.mongo_svc_name)

        # PVC before PV
        self._delete_pvc(self.mongo_pvc_name)

        # PV if we created one
        if self.use_static_pv and not self.storage_class_name:
            self._delete_pv(self.mongo_pv_name)

        logger.info("🧹 Cleanup flow complete.")

   
    def _ensure_namespace(self):
        try:
            self.core.read_namespace(name=self.namespace)
            logger.info(f"Namespace '{self.namespace}' already exists.")
        except ApiException as e:
            if e.status == 404:
                ns = client.V1Namespace(metadata=client.V1ObjectMeta(name=self.namespace))
                self.core.create_namespace(ns)
                logger.info(f"Created namespace '{self.namespace}'.")
            else:
                raise

    # ---------------------------
    # Helpers: PV / PVC
    # ---------------------------

    def _create_mongo_pv(self):
        """
        Create a static hostPath PV for MongoDB.
        """
        pv_body = client.V1PersistentVolume(
            api_version="v1",
            kind="PersistentVolume",
            metadata=client.V1ObjectMeta(
                name=self.mongo_pv_name,
                labels={"app": self.deployment_name, "component": "exchange-storage"},
            ),
            spec=client.V1PersistentVolumeSpec(
                capacity={"storage": self.storage_size},
                access_modes=["ReadWriteOnce"],
                persistent_volume_reclaim_policy="Delete",  # so 'remove' cleans it up
                storage_class_name="manual",
                host_path=client.V1HostPathVolumeSource(path=self.mongo_host_path),
                node_affinity=(
                    client.V1VolumeNodeAffinity(
                        required=client.V1NodeSelector(
                            node_selector_terms=[
                                client.V1NodeSelectorTerm(
                                    match_expressions=[
                                        client.V1NodeSelectorRequirement(
                                            key="kubernetes.io/hostname",
                                            operator="In",
                                            values=[self.mongo_node_name],
                                        )
                                    ]
                                )
                            ]
                        )
                    ) if self.mongo_node_name else None
                ),
            ),
        )

        try:
            self.core.create_persistent_volume(pv_body)
            logger.info(f"Created PV '{self.mongo_pv_name}'.")
        except ApiException as e:
            if e.status == 409:  # Already exists
                logger.info(f"PV '{self.mongo_pv_name}' already exists. Skipping.")
            else:
                raise

    def _create_mongo_pvc(self):
        """
        Create PVC; if using static PV, bind explicitly via volumeName + storageClass 'manual'.
        If dynamic, set storageClassName and omit volumeName.
        """
        if self.use_static_pv and not self.storage_class_name:
            pvc_spec = client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(requests={"storage": self.storage_size}),
                storage_class_name="manual",
                volume_name=self.mongo_pv_name,
            )
        else:
            if not self.storage_class_name:
                # If the cluster has default StorageClass, PVC will still bind; but it’s clearer if provided.
                logger.warning(
                    "No storage_class_name provided; relying on cluster default StorageClass for dynamic provisioning."
                )
            pvc_spec = client.V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                resources=client.V1ResourceRequirements(requests={"storage": self.storage_size}),
                storage_class_name=self.storage_class_name,
            )

        pvc_body = client.V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=client.V1ObjectMeta(
                name=self.mongo_pvc_name,
                namespace=self.namespace,
                labels={"app": self.deployment_name, "component": "exchange-storage"},
            ),
            spec=pvc_spec,
        )

        try:
            self.core.create_namespaced_persistent_volume_claim(namespace=self.namespace, body=pvc_body)
            logger.info(f"Created PVC '{self.mongo_pvc_name}'. Waiting to bind...")
        except ApiException as e:
            if e.status == 409:
                logger.info(f"PVC '{self.mongo_pvc_name}' already exists. Continuing.")
            else:
                raise

        self._wait_for_pvc_bound(self.mongo_pvc_name, timeout_s=self.pvc_bound_timeout_s)

    def _wait_for_pvc_bound(self, pvc_name: str, timeout_s: int = 120):
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                pvc = self.core.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=self.namespace)
                phase = pvc.status.phase
                if phase == "Bound":
                    logger.info(f"PVC '{pvc_name}' is Bound.")
                    return
                logger.info(f"PVC '{pvc_name}' phase: {phase}. Waiting...")
            except ApiException as e:
                if e.status != 404:
                    logger.warning(f"While waiting for PVC, got: {e}")
            time.sleep(2)
        raise TimeoutError(f"PVC '{pvc_name}' did not reach Bound state within {timeout_s}s.")

    # ---------------------------
    # Helpers: Mongo Deployment + Service
    # ---------------------------

    def _create_mongo_deployment_and_service(self) -> str:
        labels = {"app": self.mongo_dep_name, "component": "exchange-storage"}

        # Container
        container = client.V1Container(
            name="mongodb",
            image="mongo:6.0",
            ports=[client.V1ContainerPort(container_port=27017)],
            volume_mounts=[client.V1VolumeMount(name="data", mount_path="/data/db")],
        )

        pod_spec = client.V1PodSpec(
            containers=[container],
            volumes=[
                client.V1Volume(
                    name="data",
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=self.mongo_pvc_name),
                )
            ],
        )

        # Pin pod to node if static PV with node affinity (recommended)
        if self.use_static_pv and self.mongo_node_name:
            if pod_spec.node_selector is None:
                pod_spec.node_selector = {}
            pod_spec.node_selector["kubernetes.io/hostname"] = self.mongo_node_name

        dep_body = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=self.mongo_dep_name, namespace=self.namespace, labels=labels),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": self.mongo_dep_name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": self.mongo_dep_name}),
                    spec=pod_spec,
                ),
            ),
        )

        try:
            self.apps.create_namespaced_deployment(namespace=self.namespace, body=dep_body)
            logger.info(f"Created Mongo Deployment '{self.mongo_dep_name}'.")
        except ApiException as e:
            if e.status == 409:
                logger.info(f"Mongo Deployment '{self.mongo_dep_name}' already exists. Skipping.")
            else:
                raise

        # Service (ClusterIP)
        svc_body = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(name=self.mongo_svc_name, namespace=self.namespace, labels=labels),
            spec=client.V1ServiceSpec(
                selector={"app": self.mongo_dep_name},
                ports=[client.V1ServicePort(port=27017, target_port=27017)],
                type="ClusterIP",
            ),
        )

        try:
            self.core.create_namespaced_service(namespace=self.namespace, body=svc_body)
            logger.info(f"Created Mongo Service '{self.mongo_svc_name}'.")
        except ApiException as e:
            if e.status == 409:
                logger.info(f"Mongo Service '{self.mongo_svc_name}' already exists. Skipping.")
            else:
                raise

        # Service DNS to use in MONGO_URL
        mongo_url = f"mongodb://{self.mongo_svc_name}.{self.namespace}.svc.cluster.local:27017"
        return mongo_url

    def _create_exchange_deployment_and_service(self, mongo_url: str):
        labels = {"app": self.exchange_dep_name, "component": "exchange-service"}

        env_list = [client.V1EnvVar(name=k, value=v) for k, v in self.exchange_envs.items()]
        env_list += [
            client.V1EnvVar(name="MONGO_URL", value=mongo_url),
            client.V1EnvVar(name="POLICY_DB_URL", value=self.policy_db_url),
            client.V1EnvVar(name="STATS_REPORTING_DESTINATION_URL", value=self.stats_reporting_destination_url),
        ]

        container = client.V1Container(
            name="exchange-service",
            image=self.exchange_image,
            ports=[client.V1ContainerPort(container_port=8080)],
            env=env_list,
        )

        dep_body = client.V1Deployment(
            api_version="apps/v1",
            kind="Deployment",
            metadata=client.V1ObjectMeta(name=self.exchange_dep_name, namespace=self.namespace, labels=labels),
            spec=client.V1DeploymentSpec(
                replicas=1,
                selector=client.V1LabelSelector(match_labels={"app": self.exchange_dep_name}),
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": self.exchange_dep_name}),
                    spec=client.V1PodSpec(containers=[container]),
                ),
            ),
        )

        try:
            self.apps.create_namespaced_deployment(namespace=self.namespace, body=dep_body)
            logger.info(f"Created Exchange Deployment '{self.exchange_dep_name}'.")
        except ApiException as e:
            if e.status == 409:
                logger.info(f"Exchange Deployment '{self.exchange_dep_name}' already exists. Skipping.")
            else:
                raise

        # Service (NodePort)
        svc_ports = [
            client.V1ServicePort(
                port=8080,
                target_port=8080,
                node_port=self.node_port if self.node_port is not None else None,
            )
        ]

        svc_body = client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(name=self.exchange_svc_name, namespace=self.namespace, labels=labels),
            spec=client.V1ServiceSpec(
                selector={"app": self.exchange_dep_name},
                type="NodePort",
                ports=svc_ports,
            ),
        )

        try:
            self.core.create_namespaced_service(namespace=self.namespace, body=svc_body)
            logger.info(f"Created Exchange Service '{self.exchange_svc_name}'.")
        except ApiException as e:
            if e.status == 409:
                logger.info(f"Exchange Service '{self.exchange_svc_name}' already exists. Skipping.")
            else:
                raise

    # ---------------------------
    # Helpers: Deletion
    # ---------------------------

    def _delete_deployment(self, name: str):
        try:
            self.apps.delete_namespaced_deployment(name=name, namespace=self.namespace)
            logger.info(f"Deleted Deployment '{name}'.")
        except ApiException as e:
            if e.status == 404:
                logger.info(f"Deployment '{name}' not found. Skipping.")
            else:
                raise

    def _delete_service(self, name: str):
        try:
            self.core.delete_namespaced_service(name=name, namespace=self.namespace)
            logger.info(f"Deleted Service '{name}'.")
        except ApiException as e:
            if e.status == 404:
                logger.info(f"Service '{name}' not found. Skipping.")
            else:
                raise

    def _delete_pvc(self, name: str):
        try:
            self.core.delete_namespaced_persistent_volume_claim(name=name, namespace=self.namespace)
            logger.info(f"Deleted PVC '{name}'.")
        except ApiException as e:
            if e.status == 404:
                logger.info(f"PVC '{name}' not found. Skipping.")
            else:
                raise

    def _delete_pv(self, name: str):
        try:
            self.core.delete_persistent_volume(name=name)
            logger.info(f"Deleted PV '{name}'.")
        except ApiException as e:
            if e.status == 404:
                logger.info(f"PV '{name}' not found. Skipping.")
            else:
                raise


    @staticmethod
    def _validate_node_port(node_port: Optional[int]) -> Optional[int]:
        if node_port is None:
            return None
        if 30000 <= int(node_port) <= 32767:
            return int(node_port)
        logger.warning(
            f"nodePort '{node_port}' is outside the default range 30000-32767. "
            "If your cluster allows this, it will work; otherwise consider passing a valid value or None."
        )
        return int(node_port)


def bad_request(msg: str, details: Optional[dict] = None):
    payload = {"success": False, "error": msg}
    if details:
        payload["details"] = details
    return jsonify(payload), 400

def collect_and_sanitize_config(payload: Dict[str, Any]) -> Dict[str, Any]:
    cfg = dict(payload)  # shallow copy
    cfg.pop("kubeconfig", None)
    return cfg

def get_or_create_exchange(exchange_id: str, db) -> Exchange:
    ok, res = db.get_by_exchange_id(exchange_id)
    if ok:
        return res  # type: ignore
    # create a bare Exchange doc if not present
    e = Exchange(
        exchange_id=exchange_id,
        exchange_name="",
        exchange_description="",
    )
    db.insert(e)
    return e

def build_infra_creator(payload: Dict[str, Any]) -> JobExchangeInfraCreator:
    kubeconfig = payload["kubeconfig"]  # dict, not persisted
    namespace = payload["namespace"]
    deployment_name = payload["deployment_name"]
    storage_size = payload["storage_size"]
    node_port = payload.get("node_port")

    # optional storage options
    use_static_pv = payload.get("use_static_pv", True)
    storage_class_name = payload.get("storage_class_name")  # for dynamic provisioning
    mongo_host_path = payload.get("mongo_host_path")
    mongo_node_name = payload.get("mongo_node_name")

    # exchange env knobs (all optional with sensible defaults)
    stats_collection_interval = int(payload.get("stats_collection_interval", 60))
    stats_flush_interval = int(payload.get("stats_flush_interval", 60))
    stats_report_interval = int(payload.get("stats_report_interval", 60))
    job_assignment_policy_rule_uri = payload.get("job_assignment_policy_rule_uri", "")
    job_assignment_policy_parameters = payload.get("job_assignment_policy_parameters", {}) or {}
    exchange_subject_association_policy_rule_uri = payload.get("exchange_subject_association_policy_rule_uri", "")
    exchange_subject_association_policy_parameters = payload.get(
        "exchange_subject_association_policy_parameters", {}
    ) or {}

    return JobExchangeInfraCreator(
        kubeconfig=kubeconfig,
        namespace=namespace,
        deployment_name=deployment_name,
        storage_size=storage_size,
        node_port=node_port,
        # storage mode
        use_static_pv=use_static_pv,
        storage_class_name=storage_class_name,
        mongo_host_path=mongo_host_path,
        mongo_node_name=mongo_node_name,
        # env knobs
        stats_collection_interval=stats_collection_interval,
        stats_flush_interval=stats_flush_interval,
        stats_report_interval=stats_report_interval,
        job_assignment_policy_rule_uri=job_assignment_policy_rule_uri,
        job_assignment_policy_parameters=job_assignment_policy_parameters,
        exchange_subject_association_policy_rule_uri=exchange_subject_association_policy_rule_uri,
        exchange_subject_association_policy_parameters=exchange_subject_association_policy_parameters,
    )
