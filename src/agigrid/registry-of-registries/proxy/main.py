from core.proxy import SocketRegistryProxy

if __name__ == "__main__":
    proxy = SocketRegistryProxy(port=9001)
    proxy.start()
