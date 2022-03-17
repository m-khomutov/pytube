"""Network service to receive requests"""
import getopt
import logging
import multiprocessing
import os
import ssl
import sys
from .handler import handler
from http.server import HTTPServer
from socketserver import ThreadingMixIn
from .tcp.service import Service as TcpService


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


class HttpsService(multiprocessing.Process):
    """Handles HTTPS protocol network activity"""
    def __init__(self, key_folder, port, params, server_class=ThreadedHTTPServer):
        super().__init__()
        logging.info(f'SSL with {key_folder + "/key.pem"} and {key_folder + "/cert.pem"} is used')
        self.https_server = server_class(('', port), handler(params))
        self.https_server.socket = ssl.wrap_socket(self.https_server.socket,
                                                   keyfile=key_folder + "/key.pem",
                                                   certfile=key_folder + '/cert.pem',
                                                   server_side=True)

    def run(self) -> None:
        """Starts service"""
        try:
            self.https_server.serve_forever()
        except KeyboardInterrupt:
            self.https_server.server_close()

    def join(self, timeout=None) -> None:
        """Implements service thread-safe stop"""
        if super().is_alive():
            self.https_server.server_close()
            super().join(timeout)


class Service:
    """Program launcher. Analyses terminal options and starts http server"""
    @staticmethod
    def print_options():
        """Informs about program terminal arguments"""
        print("params:\n\t-p(--ports) ports to bind[http,https,rtsp] (def 4555,4556,4557)\n\t"
              "-r(--root) files directory(req)\n\t"
              "-s(--segment) segment duration floor\n\t"
              "-c(--cache) cache segmentation as .*.cache files\n\t"
              "-b(--basic) user:password@realm (use Basic Authorization)\n\t"
              "-d(--digest) user:password@realm (use Digest Authorization)\n\t"
              "-k(--keys) directory with key.pem and cert.pem files (req. for https)\n\t"
              "-v(--verb) be verbose\n\t"
              "-h(--help) this help")

    def __init__(self):
        self.segment_makers = {}

    def run(self, ports, params, server_class=ThreadedHTTPServer):
        """Starts http server"""
        logging.basicConfig(level=logging.INFO)
        params['segment_makers'] = self.segment_makers
        tcp_server = TcpService(('', ports[2]), params)
        http_server = server_class(('', ports[0]), handler(params))
        ssl_key_folder = params.get('keys')
        https_server = None
        if ssl_key_folder and os.path.isfile(ssl_key_folder+'/key.pem') and os.path.isfile(ssl_key_folder+'/cert.pem'):
            https_server = HttpsService(ssl_key_folder, ports[1], params)
        logging.info('Starting...')
        try:
            tcp_server.start()
            if https_server:
                https_server.start()
            http_server.serve_forever()
        except KeyboardInterrupt:
            pass
        http_server.server_close()
        https_server and https_server.join()
        tcp_server.join()
        logging.info('Stopping')


def start(argv):
    """Program start point"""
    try:
        opts, args = getopt.getopt(argv,
                                   "hp:r:s:b:d:ck:v",
                                   ["help",
                                    "ports=",
                                    "root=",
                                    "segment=",
                                    "basic=",
                                    "digest=",
                                    "cache",
                                    "keys=",
                                    "verb"])
        if args:
            Service.print_options()
            sys.exit()
    except getopt.GetoptError as error:
        print(error)
        sys.exit()
    ports = [4555, 4556, 4557]
    params = {}
    try:
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                Service.print_options()
                sys.exit()
            elif opt in ('-p', '--ports'):
                ports = [int(k) for k in arg.split(',')]
                if len(ports) != 3:
                    Service.print_options()
                    sys.exit()
            elif opt in ('-r', '--root'):
                params['root'] = arg
            elif opt in ('-s', '--segment'):
                params['segment'] = float(arg)
            elif opt in ('-b', '--basic'):
                params['basic'] = arg
            elif opt in ('-d', '--digest'):
                params['digest'] = arg
            elif opt in ('-c', '--cache'):
                params['cache'] = True
            elif opt in ('-k', '-keys'):
                params['keys'] = arg
            elif opt in ('-v', '--verb'):
                params['verb'] = True
    except ValueError as error:
        print(error)
        Service.print_options()
        sys.exit()
    Service().run(ports, params)
