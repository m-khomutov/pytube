from .atom import FullBox


class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        self.entries = []
        if f != None:
            self._readfile(f)
        else:
            self.type = 'stsz'
            self.size = 20
            self.sample_size = 0

    def __repr__(self):
        ret = super().__repr__()
        if self.sample_size != 0:
            ret += "sample size:" + str(self.sample_size)
        else:
            ret += " size entries:[ "
            for sz in self.entries:
                ret += str(sz) + ' '
            ret += "]"
        return ret

    def _readfile(self, f):
        self.sample_size = int.from_bytes(self._readsome(f, 4), "big")
        self.sample_count = int.from_bytes(self._readsome(f, 4), "big")
        if self.sample_size == 0:
            for i in range(self.sample_count):
                self.entries.append(int.from_bytes(self._readsome(f, 4), "big"))

    def encode(self):
        ret = super().encode()
        ret += self.sample_size.to_bytes(4, byteorder='big')
        ret += len(self.entries).to_bytes(4, byteorder='big')
        if self.sample_size == 0:
            for sz in self.entries:
                ret += sz.encode();
        return ret