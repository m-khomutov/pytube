import sys
import os
import getopt
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import time
from .reader import Reader
from .writer import Writer


def MakeHandler(params):
    class Handler(BaseHTTPRequestHandler, object):
        def __init__(self, *args, **kwargs):
            self._root = params.get("root", ".")
            self._verbal = params.get("verb", False)
            super(Handler, self).__init__(*args, **kwargs)
        def _streamfile(self):
            self.send_response(200)
            self.send_header('Content-type', 'video/mp4')
            self.end_headers()
            reader = Reader(self._filename)
            if self._verbal:
                print(reader)
            writer = Writer(reader)
            self.wfile.write(writer.init())
            while True:
                try:
                    self.wfile.write(writer.fragment())
                    if writer.last_chunk:
                        break
                    time.sleep( writer.chunk_duration )
                except:
                    break
        def _reply_notfound(self):
            self.send_response(404)
            self.end_headers()
            pass
        def do_GET(self):
            logging.info("Path: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
            self._filename = self._root + self.path + '.mp4'
            if os.path.isfile(self._filename):
                self._streamfile()
            else:
                self._reply_notfound()

    return Handler

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""

def __run(port, params, server_class=ThreadedHTTPServer):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
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
    __run(port, params)