"""The chunk offset table gives the index of each chunk into the containing file.
   The variant, permitting the use of 64-bit offsets
"""
from functools import reduce
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'co64'


@full_box_derived
class Box(FullBox):
    """64-bit chunk offset box"""
    entries = []

    def __repr__(self):
        return super().__repr__() + ' offsets:[' + ' '.join([str(k) for k in self.entries]) + ']'

    def _read_entry(self, file):
        """Reads offset from file"""
        return int.from_bytes(self._read_some(file, 8), 'big')

    def init_from_file(self, file):
        self.entries = self._read_entries(file)

    def init_from_args(self, **kwargs):
        self.type = 'co64'
        self.size = 16

    def to_bytes(self):
        ret = super().to_bytes() + len(self.entries).to_bytes(4, byteorder='big')
        return ret + reduce(lambda a, b: a + b,
                            map(lambda x: x.to_bytes(8, byteorder='big'), self.entries))
