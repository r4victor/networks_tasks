import sys
import os
import json
import socket
import struct

from urllib.request import urlopen
from urllib.error import URLError, HTTPError


PORT = 33458
MAX_HOPS = 25
MAX_ATTEMPS = 3

RIPE_API_URL = (
    'https://rest.db.ripe.net/search.json?'
    '&filters=no-filtering'
    '&source=AFRINIC-GRS'
    '&source=APNIC-GRS'
    '&source=ARIN-GRS'
    '&source=LACNIC-GRS'
    '&source=JPIRR-GRS'
    '&source=RADB-GRS'
    '&source=RIPE'
    '&query-string='
)


def traceroute(destination):
    dest_ip = socket.gethostbyname(destination)
    ip = None
    ttl = 1
    while ip != dest_ip and ttl <= MAX_HOPS:
        recv_sock, send_sock = get_socks(ttl)
        send_sock.sendto(b'', (dest_ip, PORT))
        attempts = 0
        while attempts < MAX_ATTEMPS:
            try:
                data, addr = recv_sock.recvfrom(512)
                ip = addr[0]
                yield get_ip_info(ip)
                break
            except socket.error:
                yield None
                attempts += 1
        recv_sock.close()
        send_sock.close()
        ttl += 1


def get_socks(ttl):
    recv_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_RAW,
        socket.getprotobyname('icmp')
    )
    recv_sock.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_RCVTIMEO,
        struct.pack("ll", 3, 0)
    )
    recv_sock.bind(('', PORT))

    send_sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM,
        socket.getprotobyname('udp')
    )
    send_sock.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)

    return recv_sock, send_sock


def get_ip_info(ip):
    info = {'ip': ip}
    response = get_json_response(RIPE_API_URL + ip)
    if not 'objects' in response:
        return info
    objects = response['objects']['object']
    for obj in objects:
        info.update(get_info(obj))
    return info


def get_info(obj):
    def get_info_by_keys(*keys):
        info = {}
        for attr in attrs:
            for key in keys:
                if 'name' in attr:
                    if attr['name'] == key:
                        info[key] = attr['value']
        return info
    info = {}
    attrs = obj['attributes']['attribute']
    if obj['type'] == 'inetnum':
        info = get_info_by_keys('country')
    elif obj['type'] == 'role':
        info = get_info_by_keys('role')
    elif obj['type'] == 'route':
        info = get_info_by_keys('origin')

    if not info:
        return {}
    return info


def get_json_response(request_url):
    try:
        with urlopen(request_url) as raw_response:
            return json.load(raw_response)
    except (URLError, HTTPError):
        return {}


if __name__ == '__main__':
    for x in traceroute(sys.argv[1]):
        if x:
            if 'origin' in x:
                print('{ip} {role} {country} {origin}'.format(**x))
            else:
                print('{ip} {role} {country} not visible in RIS'.format(**x))
        else:
            print('*')
