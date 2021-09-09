"""The chunk offset table gives the index of each chunk into the containing file"""
from .atom import FullBox


def atom_type():
    """Returns this atom type"""
    return 'stco'


class Box(FullBox):
    """Chunk offset, partial data-offset information"""
    entries = []

    def __repr__(self):
        ret = super().__repr__() + \
              ' offsets:[' + ' '.join(str(k) for k in self.entries) + ']'
        return ret

    def _init_from_file(self, file):
        super()._init_from_file(file)
        count = int.from_bytes(self._read_some(file, 4), "big")
        self.entries = list(
            map(lambda x: int.from_bytes(self._read_some(file, 4), "big"), range(count))
        )

    def _init_from_args(self, **kwargs):
        super()._init_from_args(**kwargs)
        self.type = 'stco'
        self.size = 16

    def to_bytes(self):
        ret = super().to_bytes() + \
              len(self.entries).to_bytes(4, byteorder='big')
        for entry in self.entries:
            ret += entry.to_bytes(4, byteorder='big')
        return ret
