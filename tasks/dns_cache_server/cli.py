import sys
import argparse

from modules.server import DNSServer


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-la', '--localaddress', default='127.0.0.1')
    parser.add_argument('-lp', '--localport', type=int, default=55555)
    parser.add_argument('-ra', '--remoteadress', default='8.8.8.8')
    parser.add_argument('-rp', '--remoteport', type=int, default=53)
    namespace = parser.parse_args(sys.argv[1:])
    server = DNSServer(
        addr=namespace.localaddress,
        port=namespace.localport,
        remote_addr=namespace.remoteadress,
        remote_port=namespace.remoteport)
    print('Running on {}:{}'.format(server.addr, server.port))
    server.start()
