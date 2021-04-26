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
from .segmenter import Segmenter


def MakeHandler(params):
    class Handler(BaseHTTPRequestHandler, object):
        def __init__(self, *args, **kwargs):
            self._root = params.get("root", ".")
            self._verbal = params.get("verb", False)
            self.segmenters = params.get("segmenters", None)
            super(Handler, self).__init__(*args, **kwargs)
        def _stream_filelist(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            lst=json.dumps([f for f in os.listdir(self._root) if f.endswith('.mp4')])
            self.wfile.write(str.encode(lst))
        def _stream_file(self):
            self.send_response(200)
            self.send_header('Content-type', 'video/mp4')
            self.end_headers()
            reader = Reader(self._filename)
            if self._verbal:
                logging.info(reader)
            writer = Writer(reader)
            self.wfile.write(writer.init())
            while True:
                try:
                    self.wfile.write(writer.fragment())
                    if writer.last_chunk:
                        break
                    time.sleep(writer.chunk_duration)
                except:
                     break
        def _stream_playlist(self):
            self.send_response(200)
            self.send_header('Content-type', 'application/vnd.apple.mpegurl')
            self.end_headers()
            segmenter = self.segmenters.get(self.path)
            if segmenter == None:
                segmenter = Segmenter(self._filename, self.path, self.server.server_address, self._verbal)
                self.segmenters[self.path] = Segmenter(self._filename, self.path, self.server.server_address, self._verbal)
            self.wfile.write(segmenter.playlist().encode())
        def _stream_segment(self):
            idx=self.path.rfind('_')
            if idx < 0:
                self._replyerror(404)
                return
            segmenter = self.segmenters.get(self.path[:idx])
            if segmenter == None:
                self._replyerror(501)
                return
            try:
                self.send_response(200)
                self.send_header('Content-type', 'video/mp4')
                self.end_headers()
                if self.path[idx+1:-4] == 'init':
                    self.wfile.write(segmenter.init())
                else:
                    segment_number=int(self.path[idx+3:-4])
                    self.wfile.write(segmenter.segment(segment_number))
            except:
                self._replyerror(501)
        def _replyerror(self, code):
            self.send_error(code)
            self.end_headers()
        def do_GET(self):
            logging.info("Path: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
            if self.segmenters == None:
                self._replyerror(501)
            elif self.path == '/':
                self._stream_filelist()
            elif self.path.endswith('.m4s') or self.path.endswith('.mp4'):
                self._stream_segment()
            else:
                hls=False
                if self.path.endswith(('.m3u','.m3u8')):
                    hls=True
                    self.path = self.path[:-4]
                    if self.path[-1] =='.':
                        self.path=self.path[:-1]
                self._filename = os.path.join(self._root, self.path[1:] + '.mp4')
                if os.path.isfile(self._filename):
                    self._stream_playlist() if hls==True else self._stream_file()
                else:
                    self._replyerror(404)

    return Handler

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

class Service:
    def __init__(self):
        self.segmenters={}
    def run(self, port, params, server_class=ThreadedHTTPServer):
        logging.basicConfig(level=logging.INFO)
        server_address = ('', port)
        params['segmenters'] = self.segmenters
        HandlerClass=MakeHandler(params)
        httpd = server_class(server_address, HandlerClass)
        logging.info('Starting httpd...')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()
        logging.info('Stopping')

def start(argv):
    try:
        opts,args=getopt.getopt(argv,"hp:r:v",["help","port=","root=","verb"])
    except getopt.GetoptError as e:
        print(e)
        sys.exit()
    port = 4555
    params={}
    for opt, arg in opts:
        if opt in ('-h','--help'):
            print("params:\n\t -p(--port) port to bind(def 4555)\n\t -r(--root) files directory(req)\n\t -v(--verb) be verbose\n\t -h(--help) this help")
            sys.exit()
        elif opt in('-p','--port'):
            port = int(arg)
        elif opt in('-r','--root'):
            params['root'] = arg
        elif opt in('-v','--verb'):
            params['verb'] = True
    Service().run(port, params)