import socket
import concurrent.futures

import http_utils

class ProxyServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        self.listen()
    
    def listen(self):
        with concurrent.futures.ThreadPoolExecutor(20) as executor:
            while True:
                client_sock, address = self.sock.accept()
                client_sock.settimeout(10)
                executor.submit(self.handle, client_sock, address)

    def handle(self, client_sock, address):
        while True:
            request = self.get_message(client_sock, http_utils.parse_request)
            if request is None:
                break
            print(request)

            response = self.send_request(
                request['header_fields']['Host'],
                http_utils.build_request(request)
            )
            if response is None:
                break
            print(response)

            modified_response = self.get_modified_response(response)
            client_sock.send(
                http_utils.build_response(modified_response)
            )

    def get_message(self, sock, parse):
        BUFF_SIZE = 8192
        try:
            data = sock.recv(BUFF_SIZE)
        except sock.timeout:
            return None
        try:
            message = parse(data)
        except Exception:
            return None
        if 'Content-Length' in message['header_fields']:
            content_length = int(message['header_fields']['Content-Length'])
            while content_length - len(message['body']) > 0:
                message['body'] += sock.recv(BUFF_SIZE)
        return message

    def send_request(self, host, data):
        sock = socket.create_connection((socket.gethostbyname(host), 80))
        sock.send(data)
        return self.get_message(sock, http_utils.parse_response)

    def get_modified_response(self, response):
        if 'body' not in response:
            return response
        header_fields = '<br>'.join(f'{k}: {v}'for k, v in response['header_fields'].items())
        i = response['body'].find(b'<body>') + 6
        response['body'] = response['body'][:i] + header_fields.encode() + response['body'][i:]
        response['header_fields']['Content-Length'] = str((len(response['body'])))
        return response