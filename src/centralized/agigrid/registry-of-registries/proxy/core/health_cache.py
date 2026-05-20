import redis
import logging
import requests
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError


# Setup logger
logger = logging.getLogger("HealthCache")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class HealthCache:
    def __init__(self, redis_host="localhost", redis_port=6379, db=0, default_ttl=30):
        try:
            self.redis = redis.StrictRedis(host=redis_host, port=redis_port, db=db, decode_responses=True)
            self.ttl = default_ttl
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}, DB={db}")
        except Exception as e:
            logger.exception("Failed to connect to Redis")
            raise RuntimeError("Redis connection failed") from e

    def get_health_status(self, registry_id: str) -> Optional[bool]:
        try:
            key = f"HEALTH_STATUS:{registry_id}"
            value = self.redis.get(key)
            logger.info(f"Health status lookup for '{registry_id}': {'HIT' if value else 'MISS'}")
            if value is None:
                return None
            return value == "healthy"
        except Exception as e:
            logger.exception(f"Failed to get health status for {registry_id}")
            return None

    def set_health_status(self, registry_id: str, is_healthy: bool, ttl: Optional[int] = None) -> None:
        try:
            key = f"HEALTH_STATUS:{registry_id}"
            value = "healthy" if is_healthy else "unhealthy"
            expire = ttl if ttl is not None else self.ttl
            self.redis.set(key, value, ex=expire)
            logger.info(f"Stored health status '{value}' for '{registry_id}' with TTL={expire}s")
        except Exception as e:
            logger.exception(f"Failed to set health status for {registry_id}")



class InternalHealthChecker:
    def __init__(self,
                 mongo_uri: str = "mongodb://localhost:27017",
                 db_name: str = "registry_system",
                 collection_name: str = "registry_core_data"):
        try:
            self.client = MongoClient(mongo_uri)
            self.db = self.client[db_name]
            self.collection = self.db[collection_name]
            logger.info(f"Connected to MongoDB at {mongo_uri}/{db_name}.{collection_name}")
        except Exception as e:
            logger.exception("Failed to connect to MongoDB")
            raise RuntimeError("MongoDB connection error") from e

    def get_health_api(self, registry_id: str) -> str:
        try:
            record = self.collection.find_one({"registry_id": registry_id})
            if not record or "health_check_api" not in record:
                raise ValueError(f"Missing health_check_api for '{registry_id}'")
            return record["health_check_api"]
        except PyMongoError as e:
            logger.exception(f"MongoDB query failed for registry_id={registry_id}")
            raise RuntimeError("DB fetch error") from e
        except Exception as e:
            logger.exception(f"Failed to get health_check_api for {registry_id}")
            raise

    def check_health(self, registry_id: str, timeout: int = 2) -> bool:
        try:
            url = self.get_health_api(registry_id)
            logger.info(f"Checking health for {registry_id} at {url}")
            response = requests.get(url, timeout=timeout)
            healthy = response.status_code == 200
            logger.info(f"Health check result for {registry_id}: {'healthy' if healthy else 'unhealthy'}")
            return healthy
        except Exception as e:
            logger.warning(f"Health check failed for {registry_id}: {e}")
            return False

class HealthChecker:
    def __init__(self,
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 mongo_uri: str = "mongodb://localhost:27017",
                 redis_ttl: int = 30):
        try:
            self.cache = HealthCache(redis_host=redis_host, redis_port=redis_port, default_ttl=redis_ttl)
            self.internal = InternalHealthChecker(mongo_uri=mongo_uri)
            logger.info("HealthChecker initialized successfully")
        except Exception as e:
            logger.exception("Failed to initialize HealthChecker")
            raise

    def is_registry_healthy(self, registry_id: str) -> bool:
        try:
            cached = self.cache.get_health_status(registry_id)
            if cached is not None:
                logger.info(f"Using cached health for '{registry_id}': {cached}")
                return cached

            live_result = self.internal.check_health(registry_id)
            self.cache.set_health_status(registry_id, live_result)
            logger.info(f"Live health result for '{registry_id}': {live_result}")
            return live_result
        except Exception as e:
            logger.warning(f"Health check failed for '{registry_id}': {e}")
            return False
