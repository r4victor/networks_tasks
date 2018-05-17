#!/usr/bin/env python3

from proxy_server import ProxyServer

def main():
    proxy_server = ProxyServer('localhost', 8080)
    proxy_server.start()

if __name__ == '__main__':
    main()