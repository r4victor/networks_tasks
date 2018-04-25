

def int_to_bytes(int_, length):
    return int_.to_bytes(length, byteorder='big')


def int_from_bytes(bytes_):
    return int.from_bytes(bytes_, byteorder='big')


def bytes_to_binstring(bytes_):
    return bin(int_from_bytes(bytes_))[2:]


def flag_value(bits, num):
    return bool(int(bits[num]))
