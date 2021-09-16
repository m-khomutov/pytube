import os
import types
import selectors
from datetime import datetime
from .session import Session as RtspSession


class Connection:
    """Manages RTSP protocol network client activity"""
    _session = None

    @staticmethod
    def _datetime():
        return str.encode('Date: ' +
                          datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S") +
                          ' GMT\r\n')

    @staticmethod
    def _sequence_number(headers):
        return str.encode([k for k in headers if 'CSeq: ' in k][0] + '\r\n')

    def __init__(self, socket_address, selector, root):
        self._socket, self._address = socket_address
        self._root = root
        print(f'RTSP connect from {self._address}')
        self._socket.setblocking(False)
        data = types.SimpleNamespace(addr=self._address, inb=b'', outb=b'')
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        selector.register(self._socket, events, data=data)

    def on_event(self, key, mask, selector):
        if mask & selectors.EVENT_READ:
            data = self._socket.recv(1024)  # Should be ready to read
            if data:
                key.data.inb += data
                if key.data.inb.find(bytes([0x0d, 0x0a, 0x0d, 0x0a])):
                    self._on_rtsp_directive(key.data)
                    key.data.inb = b''
            else:
                print('closing connection to', key.data.addr, "- -", self._address)
                selector.unregister(self._socket)
                self._socket.close()
                raise EOFError()
        if mask & selectors.EVENT_WRITE:
            if key.data.outb:
                sent = self._socket.send(key.data.outb)  # Should be ready to write
                key.data.outb = key.data.outb[sent:]

    def _on_rtsp_directive(self, data):
        """Manages RTSP directive"""
        headers = []
        try:
            directive = data.inb.decode('utf-8')
            print(directive)
            headers = directive.split('\r\n')
            if headers[0][:8] == 'OPTIONS ':
                self._on_options(headers, data)
                return
            if headers[0][:9] == "DESCRIBE ":
                self._on_describe(headers, data)
                return
            if headers[0][:6] == "SETUP ":
                self._on_setup(headers, data)
                return
            if headers[0][:5] == "PLAY ":
                self._on_play(headers, data)
                return
            if headers[0][:9] == "TEARDOWN ":
                self._on_teardown(headers, data)
                pass
        except:  # noqa # pylint: disable=bare-except
            data.outb = str.encode('RTSP/1.0 400 Bad Request\r\n') + \
                self._sequence_number(headers) + \
                str.encode('\r\n')
            pass

    def _on_options(self, headers, data):
        """Manager OPTIONS RTSP directive"""
        data.outb = str.encode('RTSP/1.0 200 OK\r\n') + \
            self._sequence_number(headers) + \
            str.encode('Public: OPTIONS, DESCRIBE, SETUP, TEARDOWN, PLAY, PAUSE\r\n\r\n')

    def _on_describe(self, headers, data):
        """Manager DESCRIBE RTSP directive"""
        content_base = headers[0].split()[1]
        filename = os.path.join(self._root, content_base.split('/')[-1] + '.mp4')
        if not os.path.isfile(filename):
            data.outb = str.encode('RTSP/1.0 404 Not Found\r\n\r\n')
            return
        if [k for k in headers if 'Accept: ' in k][0][8:] != 'application/sdp':
            data.outb = str.encode('RTSP/1.0 405 Method Not Allowed\r\n') + \
                self._sequence_number(headers) + \
                str.encode('\r\n')
            return
        sdp = self._prepare_sdp(content_base, filename)
        data.outb = str.encode('RTSP/1.0 200 OK\r\n') + \
            self._sequence_number(headers) + \
            self._datetime() + \
            str.encode('Content-Base: ' + self._session.content_base + '\r\n') + \
            str.encode('Content-Type: application/sdp\r\n') + \
            str.encode('Content-Length: ' + str(len(sdp)) + '\r\n\r\n') + \
            str.encode(sdp)

    def _on_setup(self, headers, data):
        """Manager SETUP RTSP directive"""
        transport = self._session.add_stream(headers)
        data.outb = str.encode('RTSP/1.0 200 OK\r\n') + \
            self._sequence_number(headers) + \
            self._datetime() + \
            self._session.identification + \
            str.encode(transport + '\r\n') + \
            str.encode('\r\n')

    def _on_play(self, headers, data):
        """Manager PLAY RTSP directive"""
        if self._session.valid_request(headers):
            data.outb = str.encode('RTSP/1.0 200 OK\r\n') + \
                self._sequence_number(headers) + \
                self._datetime() + \
                self._session.identification + \
                str.encode('\r\n')
            # self._session.start_streaming()
            return
        data.outb = str.encode('RTSP/1.0 406 Not Acceptable\r\n') + \
            self._sequence_number(headers) + \
            str.encode('\r\n')

    def _on_teardown(self, headers, data):
        """Manager TEARDOWN RTSP directive"""
        if self._session.valid_request(headers):
            data.outb = str.encode('RTSP/1.0 200 OK\r\n') + \
                self._sequence_number(headers) + \
                self._datetime() + \
                self._session.identification + \
                str.encode('\r\n')

    def _prepare_sdp(self, content_base, filename):
        self._session = RtspSession(content_base, filename, self._socket, 0)#self._verbal)
        ret = 'v=0\r\n' + \
              'o=- 0 0 IN IP4 ' + self._address[0] + '\r\n' + \
              's=No Title\r\n' + \
              'c=IN IP4 0.0.0.0\r\n' + \
              't=0 0\r\n' + \
              self._session.sdp
        return ret
