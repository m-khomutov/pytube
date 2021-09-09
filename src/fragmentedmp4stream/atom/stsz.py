"""Sample sizes (framing)"""
from .atom import FullBox


def atom_type():
    """Returns this atom type"""
    return 'stsz'


class Box(FullBox):
    """Sample table box"""

    def __repr__(self):
        ret = super().__repr__()
        if self.sample_size != 0:
            return ret + "sample size:{}".format(self.sample_size)
        return ret + " size entries:[ " + ' '.join([str(k) for k in self.entries]) + ']'

    def _init_from_file(self, file):
        super()._init_from_file(file)
        self.sample_size = int.from_bytes(self._read_some(file, 4), "big")
        self.sample_count = int.from_bytes(self._read_some(file, 4), "big")
        if self.sample_size == 0:
            self.entries =\
                list(map(lambda x:
                         int.from_bytes(self._read_some(file, 4), 'big'), range(self.sample_count)))

    def _init_from_args(self, **kwargs):
        super()._init_from_args(**kwargs)
        self.type = 'stsz'
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
