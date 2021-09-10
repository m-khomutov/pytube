"""Sample sizes (framing)"""
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'stsz'


@full_box_derived
class Box(FullBox):
    """Sample table box"""
    sample_size, sample_count = 0, 0
    entries = []

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

    def to_bytes(self):
        ret = super().to_bytes()
        ret += self.sample_size.to_bytes(4, byteorder='big')
        ret += len(self.entries).to_bytes(4, byteorder='big')
        if self.sample_size == 0:
            for entry in self.entries:
                ret += entry.to_bytes(4, byteorder='big')
        return ret
