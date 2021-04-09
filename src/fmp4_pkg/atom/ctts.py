from .atom import FullBox


class Entry:
    def __init__(self, count, offset):
        self.count = count
        self.offset = offset

    def __repr__(self):
        return str(self.count)+":"+str(self.offset)

    def encode(self):
        return self.count.to_bytes(4, byteorder='big') + self.offset.to_bytes(4, byteorder='big')


class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        self.entries = []
        if f != None:
            self._readfile(f)
        else:
            self.type = 'ctts'
            self.size = 16

    def __repr__(self):
        ret = super().__repr__() + " entries:"
        for s in self.entries:
            ret += "{" + s.__repr__() + "}"
        return ret

    def _readfile(self, f):
        count = int.from_bytes(self._readsome(f, 4), "big")
        for i in range(count):
            sample_count = int.from_bytes(self._readsome(f, 4), "big")
            sample_offset = int.from_bytes(self._readsome(f, 4), "big")
            self.entries.append(Entry(sample_count, sample_offset))

    def encode(self):
        ret = super().encode()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        for s in range(len(self.entries)):
            ret += s.encode();
        return ret