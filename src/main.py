import sys
import fragmentedmp4stream.service

def main(argv):
    fragmentedmp4stream.service.start(argv)

if __name__ == "__main__":
    main(sys.argv[1:])
