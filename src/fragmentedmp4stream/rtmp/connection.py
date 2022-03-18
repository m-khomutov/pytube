"""RTMP protocol network connection"""
from collections import namedtuple
from datetime import datetime
from enum import IntEnum
import secrets

State: IntEnum = IntEnum('State', ('Initial',
                                   'Handshake'
                                   )
                         )
CS0 = namedtuple('CS0', 'version')
CSn = namedtuple('CSn', 'time time2 random')


class ConnectionException(ValueError):
    """Exception, raised on connection errors"""
    pass


class Connection:
    """Manages RTMP protocol network connection activity"""
    @staticmethod
    def version():
        return 3

    def __init__(self, address, params):
        self._root: str = params.get("root", ".")
        self._verbal: bool = params.get("verb", False)
        self._address: str = address
        self._c1: CSn = CSn(0, 0, b'')
        self._s1: CSn = CSn(int(datetime.now().timestamp()), 0, secrets.token_bytes(1528))
        self._state: State = State.Initial
        print(f'RTMP connect from {self._address}')

    def on_read_event(self, key, buffer):
        """Manager read socket event"""
        if buffer:
            self._on_message(buffer, key.data)
            key.data.inb = b''
            return
        raise EOFError()

    def on_write_event(self, key):
        """Manager write socket event"""
        if key.data.outb:
            sent = key.fileobj.send(key.data.outb)  # Should be ready to write
            key.data.outb = key.data.outb[sent:]

    def _on_message(self, buffer, data):
        if not self._c1.random:
            self._on_c0(buffer, data)
        elif self._state == State.Initial and len(buffer) >= 1536:
            self._on_c2(buffer)
        else:
            print(f'some data of {len(buffer)}')

    def _on_c0(self, buffer, data):
        c0: CS0 = CS0(buffer[0])
        if c0.version != Connection.version():
            raise ConnectionException(f'unsupported protocol version {c0.version}')
        self._c1 = CSn(int.from_bytes(buffer[1:5], byteorder='big'),
                       int.from_bytes(buffer[5:9], byteorder='big'),
                       buffer[9:])
        s0: bytes = Connection.version().to_bytes(1, 'big')
        s1: bytes = self._s1.time.to_bytes(4, 'big') + self._s1.time2.to_bytes(4, 'big') + self._s1.random
        s2: bytes = self._c1.time.to_bytes(4, 'big') + self._s1.time.to_bytes(4, 'big') + self._c1.random
        data.outb = s0 + s1 + s2

    def _on_c2(self, buffer):
        c2: CSn = CSn(int.from_bytes(buffer[0:4], byteorder='big'),
                      int.from_bytes(buffer[4:8], byteorder='big'),
                      buffer[8:])
        time_ok, time2_ok, random_ok = c2.time == self._s1.time,\
            c2.time2 == self._c1.time,\
            c2.random == self._s1.random
        if not (time_ok and time2_ok and random_ok):
            raise ConnectionException(f'Handshake failed: time {time_ok}, time2 {time2_ok} random {random_ok}')
        self._state = State.Handshake