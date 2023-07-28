"""RTSP protocol network connection"""
import os
from datetime import datetime
from typing import List
from .session import Session as RtspSession
from ..authentication import AuthenticationContainer, Authentication, AuthenticationException


class Connection:
    """Manages RTSP protocol network connection activity"""
    @staticmethod
    def _datetime():
        return ''.join(['Date: ', datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S"), ' GMT\r\n'])

    @staticmethod
    def _header(headers, header):
        return [k for k in headers if header + ': ' in k]

    @staticmethod
    def _sequence_number(headers):
        return ''.join([Connection._header(headers, 'CSeq')[0], '\r\n'])

    @staticmethod
    def _scale(headers):
        ret = Connection._header(headers, 'Scale')
        return ret[0] if ret else 'Scale: 0'

    def __init__(self, address, params):
        self._session = None
        self._playing = False
        self._root = params.get("root", ".")
        self._verbal = params.get("verb", False)
        self._address = address
        print(f'RTSP connect from {self._address}')
        self._auth = None
        try:
            self._auth = AuthenticationContainer(params.get('basic'), params.get('digest'))
        except ValueError:
            self._auth = None

    def on_read_event(self, key, data):
        """Manager read socket event"""
        if data:
            key.data.inb += data
            if key.data.inb.find(bytes([0x0d, 0x0a, 0x0d, 0x0a])):
                self._on_rtsp_directive(key.data)
                key.data.inb = b''
                return
        raise EOFError()

    def on_write_event(self, key):
        """Manager write socket event"""
        if key.data.outb:
            sent = key.fileobj.send(key.data.outb)  # Should be ready to write
            key.data.outb = key.data.outb[sent:]
        if self._session and self._playing:
            try:
                key.data.outb = self._session.get_next_frame()
            except:  # noqa # pylint: disable=bare-except
                self._playing = False

    def _on_rtsp_directive(self, data):
        """Manages RTSP directive"""
        headers = []
        try:
            directive = data.inb.decode('utf-8')
            print(directive)
            headers = directive.split('\r\n')
            if headers[0][:8] == 'OPTIONS ':
                self._on_options(headers, data)
            else:
                if self._auth:
                    self._auth.verify(self._header(headers, 'Authorization'), headers[0].split()[0])
                if headers[0][:9] == "DESCRIBE ":
                    self._on_describe(headers, data)
                elif headers[0][:9] == "ANNOUNCE ":
                    self._on_announce(headers, data)
                elif headers[0][:14] == "GET_PARAMETER ":
                    self._on_get_parameter(headers, data)
                elif headers[0][:14] == "SET_PARAMETER ":
                    self._on_set_parameter(headers, data)
                elif headers[0][:6] == "SETUP ":
                    self._on_setup(headers, data)
                elif headers[0][:5] == "PLAY ":
                    self._on_play(headers, data)
                elif headers[0][:6] == "PAUSE ":
                    self._on_pause(headers, data)
                elif headers[0][:7] == "RECORD ":
                    self._on_record(headers, data)
                elif headers[0][:9] == "REDIRECT ":
                    self._on_redirect(headers, data)
                elif headers[0][:9] == "TEARDOWN ":
                    self._on_teardown(headers, data)
        except AuthenticationException as exception:
            data.outb = ''.join([f'{exception}', self._sequence_number(headers), '\r\n']).encode()
        except:  # noqa # pylint: disable=bare-except
            data.outb = ''.join(['RTSP/1.0 400 Bad Request\r\n', self._sequence_number(headers), '\r\n']).encode()

    def _on_options(self, headers, data):
        """Manager OPTIONS RTSP directive"""
        data.outb = ''.join(['RTSP/1.0 200 OK\r\n',
                             self._sequence_number(headers),
                             'Public: OPTIONS, DESCRIBE, SETUP, TEARDOWN, PLAY, PAUSE\r\n\r\n']).encode()

    def _on_describe(self, headers, data):
        """Manager DESCRIBE RTSP directive"""
        content_base = headers[0].split()[1]
        filename = os.path.join(self._root, content_base.split('/')[-1] + '.mp4')
        if not os.path.isfile(filename):
            data.outb = str.encode('RTSP/1.0 404 Not Found\r\n\r\n')
            return
        accept = [k for k in headers if 'Accept: ' in k]
        if accept and accept[0][8:] != 'application/sdp':
            data.outb = ''.join(['RTSP/1.0 405 Method Not Allowed\r\n',
                                 self._sequence_number(headers),
                                 '\r\n']).encode()
            return
        sdp = self._prepare_sdp(content_base, filename)
        data.outb = ''.join(['RTSP/1.0 200 OK\r\n',
                             self._sequence_number(headers),
                             self._datetime(),
                             'Content-Base: ', self._session.content_base + '\r\n',
                             'Content-Type: application/sdp\r\n',
                             'Content-Length: ', str(len(sdp)), '\r\n\r\n',
                             sdp]).encode()

    def _on_announce(self, headers, data):
        """Manager ANNOUNCE RTSP directive"""
        pass

    def _on_get_parameter(self, headers, data):
        """Manages GET_PARAMETER RTSP directive"""
        rc: List[str] = ['RTSP/1.0 200 OK\r\n',
                         self._sequence_number(headers),
                         self._session.identification(),
                         self._datetime()]
        if headers[-1] == 'position':
            range_: str = 'Range: ' + self._session.position_absolute_time() + '\r\n'
            rc.append('Content-Length: ' + str(len(range_)) + '\r\n\r\n')
            rc.append(range_)
        else:
            rc.append('\r\n\r\n')
        data.outb = ''.join(rc).encode()
        print(data.outb)

    def _on_set_parameter(self, headers, data):
        """Manager GET_PARAMETER RTSP directive"""
        pass

    def _on_setup(self, headers, data):
        """Manager SETUP RTSP directive"""
        if [k for k in headers if 'Session: ' in k] and \
                not self._session.valid_session(headers):
            self._on_session_error(data, headers)
        else:
            transport = self._session.add_stream(headers)
            data.outb = ''.join(['RTSP/1.0 200 OK\r\n',
                                 self._sequence_number(headers),
                                 self._datetime(),
                                 self._session.identification(';timeout=60'),
                                 transport,
                                 '\r\n\r\n']).encode()

    def _on_play(self, headers, data):
        """Manager PLAY RTSP directive"""
        if self._session.valid_request(headers):
            scale = int(Connection._scale(headers)[7:])
            data.outb = ''.join(['RTSP/1.0 200 OK\r\n',
                                 self._sequence_number(headers),
                                 self._session.set_play_range(headers, scale),
                                 self._session.set_scale(scale),
                                 self._datetime(),
                                 self._session.identification(),
                                 '\r\n']).encode()
            self._playing = True
        else:
            self._on_session_error(data, headers)

    def _on_pause(self, headers, data):
        """Manager PAUSE RTSP directive"""
        if self._session.valid_request(headers):
            data.outb = ''.join(['RTSP/1.0 200 OK\r\n',
                                 self._sequence_number(headers),
                                 self._datetime(),
                                 self._session.identification(),
                                 '\r\n']).encode()
            self._playing = False

    def _on_record(self, headers, data):
        """Manager RECORD RTSP directive"""
        pass

    def _on_redirect(self, headers, data):
        """Manager REDIRECT RTSP directive"""
        pass

    def _on_teardown(self, headers, data):
        """Manager TEARDOWN RTSP directive"""
        if self._session.valid_request(headers):
            data.outb = ''.join(['RTSP/1.0 200 OK\r\n',
                                 self._sequence_number(headers),
                                 self._datetime(),
                                 self._session.identification(),
                                 '\r\n']).encode()
            self._playing = False

    def _on_session_error(self, data, headers):
        data.outb = ''.join(['RTSP/1.0 454 Session Not Found\r\n',
                             self._sequence_number(headers),
                             '\r\n']).encode()

    def _prepare_sdp(self, content_base, filename):
        self._session = RtspSession(content_base, filename, self._verbal)
        return ''.join(['v=0\r\n',
                        'o=- 0 0 IN IP4 ', self._address[0], '\r\n',
                        's=No Title\r\n',
                        'c=IN IP4 0.0.0.0\r\n',
                        't=0 0\r\n',
                        self._session.sdp])
