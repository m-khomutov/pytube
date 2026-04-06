import datetime

class Sei:
    def __init__(self):
        l = [b'\x66\x00\x08', int(datetime.datetime.now(datetime.UTC).timestamp()*1e3).to_bytes(8, byteorder="little"), b'\xff'*56]
        self._data = b''.join(l)


    def __bytes__(self):
        return self._data