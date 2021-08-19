"""The chunk offset table gives the index of each chunk into the containing file.
   The variant, permitting the use of 64-bit offsets
"""
from functools import reduce
from .atom import FullBox


class Box(FullBox):
    """64-bit chunk offset box"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.entries = []
        if file is not None:
            self._readfile(file)
        else:
            self.type = 'co64'
            self.size = 16

    def __repr__(self):
        return super().__repr__() + ' offsets:[' + ' '.join([str(k) for k in self.entries]) + ']'

    def _readfile(self, file):
        count = int.from_bytes(self._readsome(file, 4), "big")
        self.entries = [map(lambda: int.from_bytes(self._readsome(file, 8), 'big'), range(count))]

    def to_bytes(self):
        ret = super().to_bytes() + len(self.entries).to_bytes(4, byteorder='big')
        return ret + reduce(lambda a, b: a + b,
                            map(lambda x: x.to_bytes(8, byteorder='big'), self.entries))
