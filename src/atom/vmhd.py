from .atom import FullBox


class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readfile(f)

    def __repr__(self):
        ret = super().__repr__() + " graphicsmode:" + str(self.graphicsmode) + \
              " opcolor:" + str(self.opcolor)
        return ret

    def _readfile(self, f):
        self.graphicsmode = int.from_bytes(self._readsome(f, 2), "big")
        self.opcolor=[]
        for i in range(3):
            self.opcolor.append(int.from_bytes(self._readsome(f, 2), "big"))

    def encode(self):
        ret = super().encode()
        ret += self.graphicsmode.to_bytes(2, byteorder='big')
        for cl in self.opcolor:
            ret += cl.to_bytes(2, byteorder='big')
        return ret