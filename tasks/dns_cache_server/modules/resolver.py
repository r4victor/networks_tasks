import socket


class Resolver:
    def __init__(self, server_addr, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.server_addr = server_addr
        self.server_port = server_port

    def resolve(self, message):
        self.sock.sendto(message, (self.server_addr, self.server_port))
        try:
            data = self.sock.recv(1024)
        except socket.timeout:
            return None
        return data
