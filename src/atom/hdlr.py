from .atom import FullBox


class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readfile(f)

    def __repr__(self):
        ret = super().__repr__() + " handlerType:" + self.handler_type + \
              " name:" + self.name
        return ret

    def _readfile(self, f):
        self._readsome(f, 4)
        self.handler_type = self._readsome(f, 4).decode("utf-8")
        self._readsome(f, 12)
        left = (self.size - (f.tell() - self.position))
        if left > 0:
            self.name = self._readsome(f, left).decode("utf-8")

    def encode(self):
        ret = super().encode()
        ret += (0).to_bytes(4, byteorder='big')
        ret += str.encode(self.handler_type)
        ret += (0).to_bytes(4, byteorder='big')
        ret += (0).to_bytes(8, byteorder='big')
        if len(self.name) > 0:
            ret += str.encode(self.name)
        return ret