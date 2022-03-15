"""The chunk offset table gives the index of each chunk into the containing file"""
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'stco'


@full_box_derived
class Box(FullBox):
    """Chunk offset, partial data-offset information"""
    def __init__(self, *args, **kwargs):
        self.entries = []
        super().__init__(*args, **kwargs)

    def __repr__(self):
        ret = super().__repr__() + ' offsets:[' + \
              ' '.join(str(k) for k in self.entries) + ']'
        return ret

    def init_from_file(self, file):
        count = int.from_bytes(self._read_some(file, 4), "big")
        self.entries = list(
            map(lambda x: int.from_bytes(self._read_some(file, 4), "big"), range(count))
        )

    def init_from_args(self, **kwargs):
        self.type = 'stco'
        self.size = 16

    def to_bytes(self):
        ret = super().to_bytes() + \
              len(self.entries).to_bytes(4, byteorder='big')
        for entry in self.entries:
            ret += entry.to_bytes(4, byteorder='big')
        return ret
