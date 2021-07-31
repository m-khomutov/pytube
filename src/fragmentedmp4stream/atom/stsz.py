"""Sample sizes (framing)"""
from .atom import FullBox


class Box(FullBox):
    """Sample table box"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.entries = []
        if file is not None:
            self._readfile(file)
        else:
            self.type = 'stsz'
            self.size = 20
            self.sample_size = 0

    def __repr__(self):
        ret = super().__repr__()
        if self.sample_size != 0:
            return ret + "sample size:{}".format(self.sample_size)
        return ret + " size entries:[ " + ' '.join([str(k) for k in self.entries]) + ']'

    def _readfile(self, file):
        self.sample_size = int.from_bytes(self._readsome(file, 4), "big")
        self.sample_count = int.from_bytes(self._readsome(file, 4), "big")
        if self.sample_size == 0:
            self.entries =\
                list(map(lambda x:
                         int.from_bytes(self._readsome(file, 4), 'big'), range(self.sample_count)))

    def to_bytes(self):
        ret = super().to_bytes()
        ret += self.sample_size.to_bytes(4, byteorder='big')
        ret += len(self.entries).to_bytes(4, byteorder='big')
        if self.sample_size == 0:
            for entry in self.entries:
                ret += entry.to_bytes(4, byteorder='big')
        return ret
