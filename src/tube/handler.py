"""HTTP requests handler"""
import json
import logging
import os
import ssl
import time
from .dash_mpd import DashMpd
from http.server import BaseHTTPRequestHandler
from .reader import Reader
from .segmenter import SegmentMaker
from .writer import Writer


def handler(params):
    """Prepares handler to deal with network activity"""
    class Handler(BaseHTTPRequestHandler):
        """Manages HTTP protocol network activity"""
        def __init__(self, *args, **kwargs):
            self._root = params.get("root", ".")
            self._segment_floor = float(params.get("segment", "6."))
            self._verbal = params.get("verb", False)
            self._cache = params.get("cache", False)
            self.segment_makers = params.get("segment_makers", None)
            self._filename = ''
            self.path = ''
            super().__init__(*args, **kwargs)

        def _stream_file_list(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            lst = json.dumps([f[:-4] for f in os.listdir(self._root) if f.endswith('.mp4')])
            self.send_header('Content-length', str(len(lst)))
            self.end_headers()
            self.wfile.write(str.encode(lst))

        def _stream_file(self, filename, content_type):
            if os.path.isfile(filename):
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.send_header('Content-length', str(os.stat(filename).st_size))
                self.end_headers()
                file = open(filename)
                for line in file:
                    self.wfile.write(line.encode())
                file.close()
                return True
            return False

        def _stream_fmp4(self):
            self.send_response(200)
            self.send_header('Content-type', 'video/mp4')
            self.end_headers()
            reader = Reader(self._filename)
            if self._verbal:
                logging.info(reader)
            writer = Writer(reader)
            self.wfile.write(writer.initializer)
            try:
                for fragment, duration in writer:
                    self.wfile.write(fragment)
                    time.sleep(duration)
            except BrokenPipeError:
                pass
            except ConnectionError:
                pass

        def _stream_dash_mpd(self):
            segment_maker = self._get_segment_maker(brands=['iso5', 'avc1', 'dash'])
            if segment_maker:
                mpd = str(DashMpd(self.path[1:],
                                  segment_maker.duration,
                                  segment_maker.target_duration,
                                  [segment_maker.writer.adaptation_set]))
                self.send_response(200)
                self.send_header('Content-type', 'application/dash+xml')
                self.send_header('Content-length', str(len(mpd)))
                self.end_headers()
                self.wfile.write(mpd.encode())
            else:
                self._reply_error(501)

        def _stream_media_playlist(self):
            segment_maker = self._get_segment_maker()
            if segment_maker:
                playlist = segment_maker.media_playlist()
                self.send_response(200)
                self.send_header('Content-type', 'application/vnd.apple.mpegurl')
                self.send_header('Content-length', str(len(playlist)))
                self.end_headers()
                self.wfile.write(playlist.encode())
            else:
                self._reply_error(501)

        def _stream_segment(self):
            idx = self.path.rfind('_')
            if idx < 0:
                self._reply_error(404)
                return
            segment_maker = self.segment_makers.get(self.path[:idx])
            if segment_maker is None:
                self._reply_error(501)
                return
            self.send_response(200)
            self.send_header('Content-type', 'video/mp4')
            if self.path[idx+1:-4] == 'init':
                body = segment_maker.init()
            else:
                segment_number = int(self.path[idx+3:-4])
                body = segment_maker.segment(segment_number)
            self.send_header('Content-length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _get_segment_maker(self, **kwargs):
            segment_maker = self.segment_makers.get(self.path)
            if segment_maker is None:
                segment_maker = SegmentMaker(self._filename,
                                             self.path,
                                             self.server.server_address,
                                             segment_duration=self._segment_floor,
                                             brands=kwargs.get('brands'),
                                             is_ssl=issubclass(type(self.request), ssl.SSLSocket),
                                             cache=self._cache,
                                             verbal=self._verbal)
                self.segment_makers[self.path] = segment_maker
            return segment_maker

        def _reply_error(self, code):
            self.send_error(code)
            self.end_headers()

        def do_GET(self): # noqa # pylint: disable=invalid-name
            """Manages HTTP GET request"""
            logging.info("Path: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
            if self.segment_makers is None:
                self._reply_error(501)
            elif self.path == '/':
                self._stream_file_list()
            elif self.path.endswith(('.m4s', '.mp4')):
                try:
                    self._stream_segment()
                except Exception as e: # noqa # pylint: disable=bare-except
                    print(e)
            elif self.path.endswith('.vtt'):
                self._stream_file(os.path.join(self._root, self.path[1:]), 'text/vtt')
            else:
                extension = self.path[self.path.rfind('.'):]
                if len(extension) > 1:
                    if self._stream_file(os.path.join(self._root, self.path[1:]), 'text/plain'):
                        return
                    self.path = self.path[:-1*len(extension)]
                self._filename = os.path.join(self._root, self.path[1:]+'.mp4')
                if os.path.isfile(self._filename):
                    if extension in ['.m3u', '.m3u8']:
                        self._stream_media_playlist()
                    elif extension == '.mpd':
                        self._stream_dash_mpd()
                    else:
                        self._stream_fmp4()
                    return
                self._reply_error(404)

    return Handler
