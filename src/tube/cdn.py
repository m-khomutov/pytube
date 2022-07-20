import io
import struct


class CdnIterator:
    def __init__(self, file):
        self._file = file
        self._file.seek(0, io.SEEK_END)
        self._file_size = self._file.tell()
        self._file.seek(0, io.SEEK_SET)
        self._timestamp: int = 0

    def __next__(self):
        try:
            hdr: bytes = self._file.read(22)
            size, ts, ats, st = struct.unpack('=IQQH', hdr)
            if not self._timestamp:
                self._timestamp = ts
            if self._file.tell() + size <= self._file_size:
                prev_ts = self._timestamp
                self._timestamp = ts
                return hdr + self._file.read(size), ts - prev_ts
        except (OSError, struct.error) as err:
            print(err)
        raise StopIteration

    def __iter__(self):
        return self


class Cdn:
    def __init__(self, name: str, path: str):
        self._filename = name + path.split('/')[1] + '.cdn'
        self._file = None
        pass

    def __enter__(self):
        self._file = open(self._filename, 'rb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._file.close()

    def __iter__(self):
        return CdnIterator(self._file)
