"""The chunk offset table gives the index of each chunk into the containing file.
   The variant, permitting the use of 64-bit offsets
"""
from functools import reduce
from .atom import FullBox


def atom_type():
    """Returns this atom type"""
    return 'co64'


class Box(FullBox):
    """64-bit chunk offset box"""

    def __repr__(self):
        return super().__repr__() + ' offsets:[' + ' '.join([str(k) for k in self.entries]) + ']'

    def _init_from_file(self, file):
        super()._init_from_file(file)
        count = int.from_bytes(self._read_some(file, 4), "big")
        self.entries = [map(lambda: int.from_bytes(self._read_some(file, 8), 'big'), range(count))]

    def _init_from_args(self, **kwargs):
        super()._init_from_args(**kwargs)
        self.type = 'co64'
        self.size = 16

    def to_bytes(self):
        ret = super().to_bytes() + len(self.entries).to_bytes(4, byteorder='big')
        return ret + reduce(lambda a, b: a + b,
                            map(lambda x: x.to_bytes(8, byteorder='big'), self.entries))
