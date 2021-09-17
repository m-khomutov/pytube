"""Network RTSP service"""
import socket
import selectors
import types
import threading
from .connection import Connection as RtspConnection


class Service(threading.Thread):
    """Manages RTSP protocol network activity"""
    _running = True
    _connections = {}

    def __init__(self, bind_address, params):
        super().__init__()
        self._bind_address = bind_address
        self._params = params
        self._lock = threading.Lock()

    def run(self) -> None:
        """Starts managing RTSP protocol network activity"""
        selector = selectors.DefaultSelector()
        accept_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        accept_sock.bind(self._bind_address)
        accept_sock.listen()
        accept_sock.setblocking(False)
        selector.register(accept_sock, selectors.EVENT_READ, data=None)
        while self._is_running():
            for key, mask in selector.select(timeout=.01):
                if key.data is None:
                    sock, address = key.fileobj.accept()
                    sock.setblocking(False)
                    selector.register(sock,
                                      selectors.EVENT_READ | selectors.EVENT_WRITE,
                                      types.SimpleNamespace(addr=address, inb=b'', outb=b''))
                    self._connections[address] = RtspConnection(address, self._params)
                else:
                    try:
                        self._on_event(key, mask)
                    except:  # noqa # pylint: disable=bare-except
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        del self._connections[key.data.addr]
        accept_sock.close()
        selector.close()

    def join(self, timeout=None) -> None:
        """Stops service in thread-safe manner"""
        with self._lock:
            self._running = False
        if super().is_alive():
            super().join(timeout)

    def _is_running(self):
        """Verifies running process"""
        with self._lock:
            return self._running

    def _on_event(self, key, mask):
        """Manages event read/write on socket"""
        connect = self._connections.get(key.data.addr, None)
        if connect:
            if mask & selectors.EVENT_READ:
                connect.on_read_event(key)
            elif mask & selectors.EVENT_WRITE:
                connect.on_write_event(key)
