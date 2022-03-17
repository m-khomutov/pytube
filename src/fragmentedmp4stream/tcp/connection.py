"""Base class for any protocol connection"""
from ..rtsp.connection import Connection as RtspConnection


class Connection:
    def __init__(self, address, params):
        self._address = address
        self._params = params
        self._specific = None

    def on_read_event(self, key):
        data = key.fileobj.recv(2048)  # Should be ready to read
        if not self._specific:
            self._guess_protocol(data)
        if self._specific:
            self._specific.on_read_event(key, data)

    def on_write_event(self, key):
        if self._specific:
            self._specific.on_write_event(key)

    def _guess_protocol(self, data):
        if data.find(b'RTSP/1.') > 0:
            self._specific = RtspConnection(self._address, self._params)
