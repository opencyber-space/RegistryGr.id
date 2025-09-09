import os
import socket
import threading
import logging
from .health_cache import HealthChecker
from .health_cache import InternalHealthChecker

logger = logging.getLogger("SocketRegistryProxy")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


class SocketRegistryProxy:
    def __init__(self, host="0.0.0.0", port=9000):
        self.listen_host = host
        self.listen_port = port

        # Load from env
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        redis_ttl = int(os.getenv("HEALTH_CACHE_TTL", 30))

        self.health_checker = HealthChecker(
            redis_host=redis_host,
            redis_port=redis_port,
            mongo_uri=mongo_uri,
            redis_ttl=redis_ttl
        )
        self.registry_lookup = InternalHealthChecker(mongo_uri=mongo_uri)

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.listen_host, self.listen_port))
            s.listen(5)
            logger.info(f"SocketRegistryProxy listening on {self.listen_host}:{self.listen_port}")

            while True:
                client_socket, addr = s.accept()
                threading.Thread(target=self._handle_connection, args=(client_socket, addr)).start()

    def _handle_connection(self, client_socket, addr):
        try:
            logger.info(f"New connection from {addr}")
            registry_id = client_socket.recv(1024).decode().strip()

            if not registry_id:
                logger.warning("Empty registry_id received, closing")
                client_socket.close()
                return

            logger.info(f"Received registry_id: {registry_id}")

            # Health check
            if not self.health_checker.is_registry_healthy(registry_id):
                logger.warning(f"Registry '{registry_id}' is unhealthy. Connection rejected.")
                client_socket.send(b"Registry is currently unavailable.\n")
                client_socket.close()
                return

            # Resolve registry host and port
            registry_info = self.registry_lookup.collection.find_one({"registry_id": registry_id})
            target_host = registry_info.get("host", "localhost")
            target_port = registry_info.get("port", 80)

            # Tunnel connection
            with socket.create_connection((target_host, target_port)) as registry_sock:
                logger.info(f"Forwarding traffic to {target_host}:{target_port}")
                self._relay(client_socket, registry_sock)

        except Exception as e:
            logger.exception(f"Error in handling connection: {e}")
            client_socket.close()

    def _relay(self, client_sock, target_sock):
        def forward(src, dst):
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                src.close()
                dst.close()

        threading.Thread(target=forward, args=(client_sock, target_sock)).start()
        threading.Thread(target=forward, args=(target_sock, client_sock)).start()
