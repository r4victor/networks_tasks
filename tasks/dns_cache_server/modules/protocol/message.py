import struct
import random
from enum import Enum

from modules.protocol import utils


class MessageType(Enum):
    QUERY = 0
    RESPONSE = 1


class QueryType(Enum):
    QUERY = 0
    IQUERY = 1
    STATUS = 2


class ResponseType(Enum):
    NO_ERROR = 0
    FORMAT_ERROR = 1
    SERVER_FAILURE = 2
    NAME_ERROR = 3
    NOT_IMPLEMENTED = 4
    REFUSED = 5


class Message:
    HEADER_LEN = 12

    def __init__(
        self, id_, type_, query_type, authoritative_answer,
        tructation, recursion_desired, recursion_availible, response_type
    ):
        self.id = id_
        self.type = type_
        self.query_type = query_type
        self.authoritative_answer = authoritative_answer
        self.tructation = tructation
        self.recursion_desired = recursion_desired
        self.recursion_availible = recursion_availible
        self.response_type = response_type

    @classmethod
    def from_bytes(cls, bytes_):
        if len(bytes_) < cls.HEADER_LEN:
            return None

        header = struct.unpack('!HHHHHH', bytes_[:cls.HEADER_LEN])
        id_, flags, qdcount, ancount, nscount, arcount = header

        message = cls(
            id_=id_,
            type_=MessageType(flags >> 15),
            query_type=QueryType(flags >> 11 & 15),
            authoritative_answer=flags & 1024 != 0,
            tructation=flags & 512 != 0,
            recursion_desired=flags & 256 != 0,
            recursion_availible=flags & 128 != 0,
            response_type=ResponseType(flags & 15)
        )

        message.question = Section.from_bytes(
            bytes_=bytes_,
            start=cls.HEADER_LEN,
            entry_class=QEntry,
            count=qdcount
        )

        message.answer = Section.from_bytes(
            bytes_=bytes_,
            start=cls.HEADER_LEN+len(message.question),
            entry_class=ResourceRecord,
            count=ancount
        )

        message.authority = Section.from_bytes(
            bytes_=bytes_,
            start=cls.HEADER_LEN+len(message.question)+len(message.answer),
            entry_class=ResourceRecord,
            count=nscount
        )

        message.additional = Section.from_bytes(
            bytes_=bytes_,
            start=cls.HEADER_LEN+len(message.question)+len(message.answer)+len(message.authority),
            entry_class=ResourceRecord,
            count=arcount
        )

        return message

    @classmethod
    def response_from_query(
        cls, query, answer, authority,
        additional, response_type=ResponseType.NO_ERROR
    ):
        response = cls(
            id_=query.id,
            type_=MessageType.RESPONSE,
            query_type=query.query_type,
            authoritative_answer=False,
            tructation=False,
            recursion_desired=query.recursion_desired,
            recursion_availible=True,
            response_type=response_type
        )
        response.question = query.question
        response.answer = Section(answer)
        response.authority = Section(authority)
        response.additional = Section(additional)
        return response

    def get_response_records(self):
        return self.answer.entries, self.authority.entries, self.additional.entries

    @classmethod
    def build_query(cls, *entries):
        query = cls(
            id_=cls.generate_id(),
            type_=MessageType.QUERY,
            query_type=QueryType.QUERY,
            authoritative_answer=False,
            tructation=False,
            recursion_desired=True,
            recursion_availible=False,
            response_type=ResponseType.NO_ERROR
        )
        query.question = Section(entries)
        query.answer = Section()
        query.authority = Section()
        query.additional = Section()
        return query.to_bytes()

    @staticmethod
    def generate_id():
        return random.getrandbits(16)

    def to_bytes(self):
        flags = (
            (self.type.value << 15) +
            (self.query_type.value << 11) +
            (self.authoritative_answer << 10) +
            (self.tructation << 9) +
            (self.recursion_desired << 8) +
            (self.recursion_availible << 7) +
            self.response_type.value
        )
        header = struct.pack(
            '!HHHHHH',
            self.id,
            flags,
            len(self.question.entries),
            len(self.answer.entries),
            len(self.authority.entries),
            len(self.additional.entries)
        )

        return (
            header +
            self.question.to_bytes() +
            self.answer.to_bytes() +
            self.authority.to_bytes() +
            self.additional.to_bytes()
        )


class Section:
    def __init__(self, entries=None):
        if entries is None:
            self.entries = []
        else:
            self.entries = entries

    def __len__(self):
        return sum(map(len, self.entries))

    @classmethod
    def from_bytes(cls, bytes_, start, entry_class, count):
        section = cls([])
        for i in range(count):
            section.entries.append(
                entry_class.from_bytes(bytes_, start+len(section))
            )
        return section

    def to_bytes(self):
        return b''.join(entry.to_bytes() for entry in self.entries)


class QEntry:
    def __init__(self, qname_len, qname, qtype, qclass):
        self.qname = qname
        self.qtype = qtype
        self.qclass = qclass
        self.qname_len = qname_len

    def __len__(self):
        return self.qname_len + 4

    @classmethod
    def from_bytes(cls, bytes_, start):
        qname, qname_len = read_name(bytes_, start)
        type_start = start + qname_len
        qtype, qclass = struct.unpack('!2s2s', bytes_[type_start:type_start+4])
        return cls(
            qname_len=qname_len,
            qname=qname,
            qtype=qtype,
            qclass=qclass,
        )

    def to_bytes(self):
        return (
            encode_name(self.qname) +
            self.qtype +
            self.qclass
        )

    def __hash__(self):
        return hash((self.qname, self.qtype, self.qclass))

    def __eq__(self, other):
        return (
            self.qname == other.qname and
            self.qtype == other.qtype and
            self.qclass == other.qclass
        )


class ResourceRecord:
    def __init__(self, name_len, name, type_, class_, ttl, rdata_len, rdata):
        self.name_len = name_len
        self.rdata_len = rdata_len
        self.name = name
        self.type = type_
        self.class_ = class_
        self.ttl = ttl
        self.rdata = rdata

    def __len__(self):
        return self.name_len + 10 + self.rdata_len

    @classmethod
    def from_bytes(cls, bytes_, start):
        name, name_len = read_name(bytes_, start)
        type_start = start + name_len
        data_start = type_start + 10
        type_, class_, ttl, rdata_len = struct.unpack(
            '!2s2sIH',
            bytes_[type_start:data_start]
        )
        rdata = bytes_[data_start:data_start+rdata_len]
        return cls(
            name_len=name_len,
            name=name,
            type_=type_,
            class_=class_,
            ttl=ttl,
            rdata_len=rdata_len,
            rdata=rdata
        )

    def to_bytes(self):
        return (
            encode_name(self.name) +
            self.type +
            self.class_ +
            utils.int_to_bytes(self.ttl, 4) +
            utils.int_to_bytes(self.rdata_len, 2) +
            self.rdata
        )


def read_name(bytes_, start):
    labels, bytes_read = read_labels(bytes_, start)
    name = b'.'.join(labels)
    if not name.endswith(b'.'):
        name += b'.'
    return name, bytes_read


def read_labels(bytes_, start):
    labels = []
    bytes_read = 0
    while True:
        curr = start + bytes_read
        code = utils.int_from_bytes(bytes_[curr:curr+1]) >> 6
        if code == 0:
            bytes_read += 1
            label_len = utils.int_from_bytes(bytes_[curr:curr+1])
            if label_len == 0:
                break
            label = bytes_[curr+1:curr+1+label_len]
            labels.append(label)
            bytes_read += label_len
        else:
            bytes_read += 2
            pointer = utils.int_from_bytes(bytes_[curr:curr+2]) & (2^14 - 1)
            pointer_labels, _ = read_labels(bytes_, pointer)
            labels.extend(pointer_labels)
            break
    return labels, bytes_read


def encode_name(name):
    labels = name.split(b'.')
    return b''.join(utils.int_to_bytes(len(label), 1) + label for label in labels)
