class ReaderException(Exception):
    pass


class Reader:
    """Provides bit operations on a stream"""
    def __init__(self, stream: bytes) -> None:
        self._data: bytes = stream
        self._offset: int = 0

    def __iter__(self):
        return self

    def bit(self) -> int:
        if self._offset >= len(self._data) << 3:
            raise ReaderException('end of data')
        self._offset += 1
        off: int = self._offset - 1
        return (self._data[off >> 3] >> (7 - (off % 8))) & 1

    def bits(self, count: int) -> int:
        if not count:
            raise ReaderException('end of data')
        if count == 1:
            return self.bit()

        ret: int = 0
        i: int = 0
        while i < count:
            ret |= self.bit() << (count-(i+1))
            i += 1
        return ret

    def golomb_u(self):
        zeroes: int = 0
        while self.bit() == 0:
            zeroes += 1

        if self._offset + zeroes >= len(self._data) << 3:
            raise ReaderException('end of data')
        result: int = 1
        for i in range(zeroes):
            result = (result << 1) | self.bit()
        return result - 1

    def golomb_s(self):
        result: int = self.golomb_u()
        rem: int = result % 2
        return -1 * (result >> 1) if not rem else (result >> 1) + 1
