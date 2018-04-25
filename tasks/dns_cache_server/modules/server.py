import asyncio

from modules.cache import Cache
from modules.resolver import Resolver
from modules.protocol.message import Message, ResponseType


class DNSServerProtocol:
    def __init__(self, cache, remote_addr, remote_port):
        self.cache = cache
        self.remote_addr = remote_addr
        self.remote_port = remote_port

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        query = Message.from_bytes(data)
        if query is None:
            return
        response = self.get_response(query)
        self.transport.sendto(response.to_bytes(), addr)

    def get_response(self, query):
        # answer, authority and additional entries
        response_records = ([], [], [])
        for question_entry in query.question.entries:
            next_response_records = self.get_response_records(question_entry)
            if next_response_records is None:
                return Message.response_from_query(
                    query=query,
                    response_type=ResponseType.SERVER_FAILURE,
                    answer=[],
                    authority=[],
                    additional=[]
                )
            for curr, nxt in zip(response_records, next_response_records):
                curr.extend(nxt)
        return Message.response_from_query(query, *response_records)

    def get_response_records(self, question_entry):
        cache_records = self.cache.get_response_records(question_entry)
        if cache_records is not None:
            return cache_records

        response_records = self.ask_remote_addr(question_entry)
        if response_records is None:
            return None

        self.cache.update(question_entry, response_records)
        return response_records

    def ask_remote_addr(self, question_entry):
        resolver = Resolver(self.remote_addr, self.remote_port)
        query = Message.build_query(question_entry)
        try:
            data = resolver.resolve(query)
        except Exception:
            return None
        if data is None:
            return None
        response = Message.from_bytes(data)
        return response.get_response_records()


class DNSServer:
    def __init__(self, addr, port, remote_addr, remote_port):
        self.addr = addr
        self.port = port
        self.remote_addr = remote_addr
        self.remote_port = remote_port
        self.cache = Cache.load()

    def start(self):
        loop = asyncio.get_event_loop()
        listen = loop.create_datagram_endpoint(
            lambda: DNSServerProtocol(self.cache, self.remote_addr, self.remote_port),
            local_addr=(self.addr, self.port)
        )
        transport, protocol = loop.run_until_complete(listen)
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        transport.close()
        loop.close()
        self.cache.save()
