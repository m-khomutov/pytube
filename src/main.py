import sys
import fmp4_pkg.service

def main(argv):
    fmp4_pkg.service.start(argv)

if __name__ == "__main__":
    main(sys.argv[1:])
