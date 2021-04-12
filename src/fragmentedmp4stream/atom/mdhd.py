from .atom import FullBox
from bitstring import BitArray

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readfile(f)

    def __repr__(self):
        ret = super().__repr__() + " ctime:" + str(self.creationTime) + \
              " mtime:" + str(self.modificationTime) + \
              " timescale:" + str(self.timescale) + \
              " duration:" + str(self.duration) + \
              " language:" + str(self.language)
        return ret

    def _readfile(self, f):
        if self.version == 1:
            self.creationTime = int.from_bytes(self._readsome(f, 8), "big");
            self.modificationTime = int.from_bytes(self._readsome(f, 8), "big");
            self.timescale = int.from_bytes(self._readsome(f, 4), "big");
            self.duration = int.from_bytes(self._readsome(f, 8), "big");
        else:
            self.creationTime = int.from_bytes(self._readsome(f, 4), "big");
            self.modificationTime = int.from_bytes(self._readsome(f, 4), "big");
            self.timescale = int.from_bytes(self._readsome(f, 4), "big");
            self.duration = int.from_bytes(self._readsome(f, 4), "big");

        l = BitArray(self._readsome(f, 2));
        self.language = ""
        for i in range(3):
            b=5*i+1
            e=b+5
            self.language += chr(int(l[b:e].bin, 2)+0x60)
        self._readsome(f, 2);

    def encode(self):
        ret = super().encode()
        if self.version == 1:
            ret += self.creationTime.to_bytes(8, byteorder='big')
            ret += self.modificationTime.to_bytes(8, byteorder='big')
            ret += self.timescale.to_bytes(4, byteorder='big')
            ret += self.duration.to_bytes(8, byteorder='big')
        else:
            ret += self.creationTime.to_bytes(4, byteorder='big')
            ret += self.modificationTime.to_bytes(4, byteorder='big')
            ret += self.timescale.to_bytes(4, byteorder='big')
            ret += self.duration.to_bytes(4, byteorder='big')

        lang = 0
        offset=14
        for c in self.language:
            d = ord(c)-0x60
            for i in range(5):
                lang |= ((d >> i) & 1)<<offset
                offset -= 1
        ret += lang.to_bytes(2, byteorder='big')
        ret += (0).to_bytes(2, byteorder='big')
        return ret