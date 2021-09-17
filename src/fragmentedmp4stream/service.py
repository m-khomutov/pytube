"""Network service to receive requests"""
import sys
import os
import getopt
import logging
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import time
from .reader import Reader
from .writer import Writer
from .segmenter import SegmentMaker
from .rtsp.service import Service as RtspService


def make_handler(params):
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
            self.end_headers()
            lst = json.dumps([f[:-4] for f in os.listdir(self._root) if f.endswith('.mp4')])
            self.wfile.write(str.encode(lst))

        def _stream_file(self, filename):
            if os.path.isfile(filename):
                print('sending ', filename)
                self.send_response(200)
                self.send_header('Content-type', 'video/mp4')
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

        def _stream_media_playlist(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.apple.mpegurl')
            self.end_headers()
            segment_maker = self.segment_makers.get(self.path)
            if segment_maker is None:
                segment_maker = SegmentMaker(self._filename,
                                             self.path,
                                             self.server.server_address,
                                             segment_duration=self._segment_floor,
                                             cache=self._cache,
                                             verbal=self._verbal)
                self.segment_makers[self.path] = segment_maker
            self.wfile.write(segment_maker.media_playlist().encode())

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
            self.end_headers()
            if self.path[idx+1:-4] == 'init':
                self.wfile.write(segment_maker.init())
            else:
                segment_number = int(self.path[idx+3:-4])
                self.wfile.write(segment_maker.segment(segment_number))

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
                self._stream_segment()
            elif self.path.endswith('.vtt'):
                self._stream_file(os.path.join(self._root, self.path[1:]))
            else:
                hls = False
                if self.path.endswith(('.m3u', '.m3u8')):
                    if self._stream_file(os.path.join(self._root, self.path[1:])) is True:
                        return
                    hls = True
                    self.path = self.path[:-4]
                    if self.path[-1] == '.':
                        self.path = self.path[:-1]
                self._filename = os.path.join(self._root, self.path[1:]+'.mp4')
                if os.path.isfile(self._filename):
                    if hls:
                        self._stream_media_playlist()
                    else:
                        self._stream_fmp4()
                    return
                self._reply_error(404)

    return Handler


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class Service:
    """Program launcher. Analyses terminal options and starts http server"""
    @staticmethod
    def print_options():
        """Informs about program terminal arguments"""
        print("params:\n\t-p(--ports) ports to bind[http, rtsp] (def 4555,4556)\n\t"
              "-r(--root) files directory(req)\n\t"
              "-s(--segment) segment duration floor\n\t"
              "-c(--cache) cache segmentation as .*.cache files\n\t"
              "-v(--verb) be verbose\n\t"
              "-h(--help) this help")

    def __init__(self):
        self.segment_makers = {}

    def run(self, ports, params, server_class=ThreadedHTTPServer):
        """Starts http server"""
        logging.basicConfig(level=logging.INFO)
        params['segment_makers'] = self.segment_makers
        handler_class = make_handler(params)
        rtsp_server = RtspService(('', ports[1]), params)
        http_server = server_class(('', ports[0]), handler_class)
        logging.info('Starting...')
        try:
            rtsp_server.start()
            http_server.serve_forever()
        except KeyboardInterrupt:
            pass
        http_server.server_close()
        rtsp_server.join()
        logging.info('Stopping')


def start(argv):
    """Program start point"""
    try:
        opts, args = getopt.getopt(argv,
                                   "hp:r:s:cv",
                                   ["help", "ports=", "root=", "segment=", "cache", "verb"])
        if args:
            Service.print_options()
            sys.exit()
    except getopt.GetoptError as error:
        print(error)
        sys.exit()
    ports = [4555, 4556]
    params = {}
    try:
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                Service.print_options()
                sys.exit()
            elif opt in ('-p', '--ports'):
                ports = [int(k) for k in arg.split(',')]
                if len(ports) != 2:
                    Service.print_options()
                    sys.exit()
            elif opt in ('-r', '--root'):
                params['root'] = arg
            elif opt in ('-s', '--segment'):
                params['segment'] = float(arg)
            elif opt in ('-c', '--cache'):
                params['cache'] = True
            elif opt in ('-v', '--verb'):
                params['verb'] = True
    except ValueError as error:
        print(error)
        Service.print_options()
        sys.exit()
    Service().run(ports, params)
