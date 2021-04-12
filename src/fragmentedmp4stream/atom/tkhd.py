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
              " trackID:" + str(self.trackID) + \
              " duration:" + str(self.duration) + \
              " layer:" + str(self.layer) + \
              " alternateGroup:" + str(self.alternateGroup) + \
              " volume:" + hex(self.volume) + \
              " matrix:[ "
        for i in self.matrix:
            ret += hex(i) + " "
        ret += "] width:" + str(self.width) + \
               " height:" + str(self.height)
        return ret

    def _readfile(self, f):
        if self.version == 1:
            self.creationTime = int.from_bytes(self._readsome(f, 8), "big")
            self.modificationTime = int.from_bytes(self._readsome(f, 8), "big")
            self.trackID = int.from_bytes(self._readsome(f, 4), "big")
            self._readsome(f,4)
            self.duration = int.from_bytes(self._readsome(f, 8), "big")
        else:
            self.creationTime = int.from_bytes(self._readsome(f, 4), "big")
            self.modificationTime = int.from_bytes(self._readsome(f, 4), "big")
            self.trackID = int.from_bytes(self._readsome(f, 4), "big")
            self._readsome(f,4)
            self.duration = int.from_bytes(self._readsome(f, 4), "big")

        self._readsome(f,8)
        self.layer = int.from_bytes(self._readsome(f, 2), "big")
        self.alternateGroup = int.from_bytes(self._readsome(f, 2), "big")
        self.volume = int.from_bytes(self._readsome(f, 2), "big")
        self._readsome(f, 2)
        self.matrix = []
        for i in range(9):
            self.matrix.append(int.from_bytes(self._readsome(f, 4), "big"))
        self.width = int.from_bytes(self._readsome(f, 4), "big")
        self.height = int.from_bytes(self._readsome(f, 4), "big")

    def encode(self):
        ret = super().encode()
        if self.version == 1:
            ret += self.creationTime.to_bytes(8, byteorder='big')
            ret += self.modificationTime.to_bytes(8, byteorder='big')
            ret += self.trackID.to_bytes(4, byteorder='big')
            ret += (0).to_bytes(4, byteorder='big')
            ret += self.duration.to_bytes(8, byteorder='big')
        else:
            ret += self.creationTime.to_bytes(4, byteorder='big')
            ret += self.modificationTime.to_bytes(4, byteorder='big')
            ret += self.trackID.to_bytes(4, byteorder='big')
            ret += (0).to_bytes(4, byteorder='big')
            ret += self.duration.to_bytes(4, byteorder='big')

        ret += (0).to_bytes(8, byteorder='big')
        ret += self.layer.to_bytes(2, byteorder='big')
        ret += self.alternateGroup.to_bytes(2, byteorder='big')
        ret += self.volume.to_bytes(2, byteorder='big')
        ret += (0).to_bytes(2, byteorder='big')
        for i in self.matrix:
            ret += i.to_bytes(4, byteorder='big')
        ret += self.width.to_bytes(4, byteorder='big')
        ret += self.height.to_bytes(4, byteorder='big')
        return ret