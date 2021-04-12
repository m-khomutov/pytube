from .atom import FullBox


class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        self.entries = []
        if f != None:
            self._readfile(f)
        else:
            self.type = 'co64'
            self.size = 16

    def __repr__(self):
        ret = super().__repr__() + " offsets:[ "
        for off in self.entries:
            ret += str(off) + ' '
        ret += "]"
        return ret

    def _readfile(self, f):
        count = int.from_bytes(self._readsome(f, 4), "big")
        for i in range(count):
            self.entries.append(int.from_bytes(self._readsome(f, 8), "big"))

    def encode(self):
        ret = super().encode()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        for off in self.entries:
            ret += off.to_bytes(8, byteorder='big')
        return ret