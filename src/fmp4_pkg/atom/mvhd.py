from .atom import FullBox


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
                                   " rate:" + hex(self.rate) + \
                                   " volume:" + hex(self.volume) + \
                                   " matrix:[ "
        for i in self.matrix:
            ret += hex(i) + " "
        ret += "] nextTrackID:" + str(self.nextTrackID)
        return ret

    def _readfile(self, f):
        if self.version == 1:
            self.creationTime = int.from_bytes(self._readsome(f, 8), "big")
            self.modificationTime = int.from_bytes(self._readsome(f, 8), "big")
            self.timescale = int.from_bytes(self._readsome(f, 4), "big")
            self.duration = int.from_bytes(self._readsome(f, 8), "big")
        else:
            self.creationTime = int.from_bytes(self._readsome(f, 4), "big")
            self.modificationTime = int.from_bytes(self._readsome(f, 4), "big")
            self.timescale = int.from_bytes(self._readsome(f, 4), "big")
            self.duration = int.from_bytes(self._readsome(f, 4), "big")

        self.rate = int.from_bytes(self._readsome(f, 4), "big")
        self.volume = int.from_bytes(self._readsome(f, 2), "big")
        self._readsome(f, 10)
        self.matrix = []
        for i in range(9):
            self.matrix.append(int.from_bytes(self._readsome(f, 4), "big"))
        self._readsome(f, 24)
        self.nextTrackID = int.from_bytes(self._readsome(f, 4), "big")

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

        ret += self.rate.to_bytes(4, byteorder='big')
        ret += self.volume.to_bytes(2, byteorder='big')
        ret += (0).to_bytes(2, byteorder='big')
        ret += (0).to_bytes(8, byteorder='big')
        for i in self.matrix:
            ret += i.to_bytes(4, byteorder='big')
        for i in range(6):
            ret += (0).to_bytes(4, byteorder='big')
        ret += self.nextTrackID.to_bytes(4, byteorder='big')
        return ret