"""Network RTSP service"""
import os
import socket
import selectors
from datetime import datetime
from .session import Session as RtspSession
from .connection import Connection as RtspConnection


class Service:
    """Manages RTSP protocol network activity"""
    _connections = {}
    _session = None
    _identifier_address = ()

    @staticmethod
    def _datetime():
        return str.encode('Date: ' +
                          datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S") +
                          ' GMT\r\n')

    @staticmethod
    def _sequence_number(headers):
        return str.encode([k for k in headers if 'CSeq: ' in k][0] + '\r\n')

    def __init__(self, bind_address, params):
        self._root = params.get("root", ".")
        self._verbal = params.get("verb", False)
        self._bind_address = bind_address

    def run(self):
        selector = selectors.DefaultSelector()
        listening = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening.bind(self._bind_address)
        listening.listen()
        listening.setblocking(False)
        selector.register(listening, selectors.EVENT_READ, data=None)
        while True:
            for key, mask in selector.select(timeout=None):
                if key.data is None:
                    sock, address = key.fileobj.accept()
                    self._connections[address] = RtspConnection((sock, address), selector, self._root)
                else:
                    try:
                        connect = self._connections.get(key.data.addr, None)
                        if connect:
                            connect.on_event(key, mask, selector)
                    except EOFError:
                        del self._connections[key.data.addr]
        listening.close()

    def run_blocked(self):
        """Accepts RTSP protocol directives"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(self._bind_address)
                sock.listen()
                self._connection, self._identifier_address = sock.accept()
                with self._connection:
                    print(f'RTSP connect from {self._identifier_address}')
                    data = b''
                    while True:
                        received = self._connection.recv(1024)
                        if not received:
                            break
                        data += received
                        if data.find(bytes([0x0d, 0x0a, 0x0d, 0x0a])):
                            self._on_rtsp_directive(data)
                            data = b''
        except BrokenPipeError:
            pass
        except ConnectionError:
            pass

    def close(self):
        """Finishes service activity"""
        pass

    def _on_rtsp_directive(self, data):
        """Manages RTSP directive"""
        headers = []
        try:
            rtsp_data = data.decode('utf-8')
            print(rtsp_data)
            headers = rtsp_data.split('\r\n')
            if headers[0][:8] == 'OPTIONS ':
                self._on_options(headers)
                return
            if headers[0][:9] == "DESCRIBE ":
                self._on_describe(headers)
                return
            if headers[0][:6] == "SETUP ":
                self._on_setup(headers)
                return
            if headers[0][:5] == "PLAY ":
                self._on_play(headers)
            if headers[0][:9] == "TEARDOWN ":
                self._on_teardown(headers)
        except:  # noqa # pylint: disable=bare-except
            self._connection.sendall(str.encode('RTSP/1.0 400 Bad Request\r\n') +
                                     self._sequence_number(headers) +
                                     str.encode('\r\n'))

    def _on_options(self, headers):
        """Manager OPTIONS RTSP directive"""
        self._connection.sendall(str.encode('RTSP/1.0 200 OK\r\n') +
                                 self._sequence_number(headers) +
                                 str.encode('Public: OPTIONS, DESCRIBE, '
                                            'SETUP, TEARDOWN, PLAY, PAUSE\r\n\r\n'))

    def _on_describe(self, headers):
        """Manager DESCRIBE RTSP directive"""
        content_base = headers[0].split()[1]
        filename = os.path.join(self._root, content_base.split('/')[-1] + '.mp4')
        if not os.path.isfile(filename):
            self._connection.sendall(str.encode('RTSP/1.0 404 Not Found\r\n\r\n'))
            return
        if [k for k in headers if 'Accept: ' in k][0][8:] != 'application/sdp':
            self._connection.sendall(str.encode('RTSP/1.0 405 Method Not Allowed\r\n') +
                                     self._sequence_number(headers) +
                                     str.encode('\r\n'))
            return
        sdp = self._prepare_sdp(content_base, filename)
        self._connection.sendall(str.encode('RTSP/1.0 200 OK\r\n') +
                                 self._sequence_number(headers) +
                                 self._datetime() +
                                 str.encode('Content-Base: ' +
                                            self._session.content_base + '\r\n') +
                                 str.encode('Content-Type: application/sdp\r\n') +
                                 str.encode('Content-Length: ' + str(len(sdp)) + '\r\n\r\n') +
                                 str.encode(sdp))

    def _on_setup(self, headers):
        """Manager SETUP RTSP directive"""
        transport = self._session.add_stream(headers)
        self._connection.sendall(str.encode('RTSP/1.0 200 OK\r\n') +
                                 self._sequence_number(headers) +
                                 self._datetime() +
                                 self._session.identification +
                                 str.encode(transport + '\r\n') +
                                 str.encode('\r\n'))

    def _on_play(self, headers):
        """Manager PLAY RTSP directive"""
        if self._session.valid_request(headers):
            self._connection.sendall(str.encode('RTSP/1.0 200 OK\r\n') +
                                     self._sequence_number(headers) +
                                     self._datetime() +
                                     self._session.identification +
                                     str.encode('\r\n'))
            self._session.start_streaming()
            return
        self._connection.sendall(str.encode('RTSP/1.0 406 Not Acceptable\r\n') +
                                 self._sequence_number(headers) +
                                 str.encode('\r\n'))

    def _on_teardown(self, headers):
        """Manager TEARDOWN RTSP directive"""
        if self._session.valid_request(headers):
            self._connection.sendall(str.encode('RTSP/1.0 200 OK\r\n') +
                                     self._sequence_number(headers) +
                                     self._datetime() +
                                     self._session.identification +
                                     str.encode('\r\n'))

    def _prepare_sdp(self, content_base, filename):
        self._session = RtspSession(content_base, filename, self._connection, self._verbal)
        ret = 'v=0\r\n' + \
              'o=- 0 0 IN IP4 ' + self._identifier_address[0] + '\r\n' + \
              's=No Title\r\n' + \
              'c=IN IP4 0.0.0.0\r\n' + \
              't=0 0\r\n' + \
              self._session.sdp
        return ret
