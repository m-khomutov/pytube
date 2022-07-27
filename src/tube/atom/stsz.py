"""Sample sizes (framing)"""
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'stsz'


@full_box_derived
class Box(FullBox):
    """Sample table box"""
    def __init__(self, *args, **kwargs):
        self.sample_size, self.sample_count = 0, 0
        self.entries = []
        super().__init__(*args, **kwargs)

    def __repr__(self):
        ret = super().__repr__()
        if self.sample_size != 0:
            return ret + "sample size:{}".format(self.sample_size)
        return ret + " size entries:[ " + ' '.join([str(k) for k in self.entries]) + ']'

    def init_from_file(self, file):
        self.sample_size = int.from_bytes(self._read_some(file, 4), "big")
        self.sample_count = int.from_bytes(self._read_some(file, 4), "big")
        if self.sample_size == 0:
            self.entries =\
                list(map(lambda x:
                         int.from_bytes(self._read_some(file, 4), 'big'), range(self.sample_count)))

    def init_from_args(self, **kwargs):
        self.type = 'stsz'
        super().init_from_args(**kwargs)
        self.size = 20
        self.entries = []
        self.sample_size = 0

    def append(self, entry: int):
        self.entries.append(entry)
        self.size += 4

    def to_bytes(self):
        rc = [
            super().to_bytes(),
            self.sample_size.to_bytes(4, byteorder='big'),
            len(self.entries).to_bytes(4, byteorder='big')
        ]
        if self.sample_size == 0:
            rc.extend([e.to_bytes(4, byteorder='big') for e in self.entries])
        return b''.join(rc)
