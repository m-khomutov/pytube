"""Network RTSP service"""
import socket
import selectors
import types
import multiprocessing
import time
import logging
from .connection import Connection


class Service(multiprocessing.Process):
    """Manages RTSP protocol network activity"""
    def __init__(self, bind_address, params):
        self._running = True
        self._connections = {}
        super().__init__()
        self._bind_address = bind_address
        self._params = params
        self._lock = multiprocessing.Lock()

    def run(self) -> None:
        """Starts managing RTSP protocol network activity"""
        selector = selectors.DefaultSelector()
        accept_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while True:
            try:
                accept_sock.bind(self._bind_address)
                break
            except OSError:
                time.sleep(2)
        accept_sock.listen()
        accept_sock.setblocking(False)
        selector.register(accept_sock, selectors.EVENT_READ, data=None)
        logging.info('Ok')
        while self._is_running():
            try:
                for key, mask in selector.select(timeout=.01):
                    if key.data is None:
                        sock, address = key.fileobj.accept()
                        sock.setblocking(False)
                        selector.register(sock,
                                          selectors.EVENT_READ | selectors.EVENT_WRITE,
                                          types.SimpleNamespace(addr=address, inb=b'', outb=b''))
                        self._connections[address] = Connection(address, self._params)
                    else:
                        try:
                            self._on_event(key, mask)
                        except Exception as e:  # noqa # pylint: disable=bare-except
                            print(f'Exception: {e}')
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                            del self._connections[key.data.addr]
                            print('connection to', key.data.addr, 'closed')
            except KeyboardInterrupt:
                self._stop()
        accept_sock.close()
        selector.close()

    def join(self, timeout=None) -> None:
        """Implements service thread-safe stop"""
        self._stop()
        if super().is_alive():
            super().join(timeout)

    def _is_running(self):
        """Verifies running process"""
        with self._lock:
            return self._running

    def _stop(self):
        """Stops service in thread-safe manner"""
        with self._lock:
            self._running = False

    def _on_event(self, key, mask):
        """Manages event read/write on socket"""
        connect = self._connections.get(key.data.addr, None)
        if connect:
            if mask & selectors.EVENT_READ:
                connect.on_read_event(key)
            elif mask & selectors.EVENT_WRITE:
                connect.on_write_event(key)
