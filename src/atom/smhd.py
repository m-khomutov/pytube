from .atom import FullBox


class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readfile(f)

    def __repr__(self):
        ret = super().__repr__() + " balance:" + str(self.balance)
        return ret

    def _readfile(self, f):
        self.balance = int.from_bytes(self._readsome(f, 2), "big")
        self._readsome(f, 2)

    def encode(self):
        ret = super().encode()
        ret += self.balance.to_bytes(2, byteorder='big')
        ret += (0).to_bytes(2, byteorder='big')
        return ret