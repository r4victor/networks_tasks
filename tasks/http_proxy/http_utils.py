
def parse_request(data):
    def parse_status_line(status_line):
        method, url, protocol = status_line.split(maxsplit=2)
        return {
            'method': method,
            'url': url,
            'protocol': protocol
        }

    return parse_message(data, parse_status_line)


def parse_response(data):
    def parse_status_line(status_line):
        protocol, status_code, status_code_desc = status_line.split(maxsplit=2)
        return {
            'protocol': protocol,
            'status_code': status_code,
            'status_code_desc': status_code_desc
        }

    return parse_message(data, parse_status_line)


def parse_message(data, parse_status_line):
    header, body = data.split(b'\r\n\r\n', 1)
    header = header.decode()
    header_lines = header.splitlines()
    header_fields = parse_header_fields(header_lines[1:])
    message = {
        'header_fields': header_fields,
        'body': body
    }

    return {**message, **parse_status_line(header_lines[0])}


def parse_header_fields(raw_header_fields):
    header_fields = {}
    for field in raw_header_fields:
        name, value = field.split(':', 1)
        header_fields[name] = value.strip()
    return header_fields


def build_request(request):
    status_line = ' '.join([
        request['method'],
        request['url'],
        request['protocol']
    ])

    return build_message(request, status_line)


def build_response(response):
    status_line = ' '.join([
        response['protocol'],
        response['status_code'],
        response['status_code_desc']
    ])

    return build_message(response, status_line)


def build_message(message, status_line):
    return b'%s\r\n%s\r\n\r\n%s' % (
        status_line.encode(),
        build_header_fields(message["header_fields"]).encode(),
        message['body']
    )


def build_header_fields(header_fields):
    return '\r\n'.join(f'{k}: {v}'for k, v in header_fields.items())
