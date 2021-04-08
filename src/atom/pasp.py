from .atom import Box


class Box(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self.hspacing = int.from_bytes(self._readsome(f, 4), "big")
            self.vspacing = int.from_bytes(self._readsome(f, 4), "big")
        else:
            self.type = 'pasp'
            self.size = 16
            self.hspacing = kwargs.get("hspacing", 0)
            self.tr_flags = kwargs.get("vspacing", 0)
    def __repr__(self):
        return super().__repr__() + ' hspacing:' + str(self.hspacing) + 'vspacing:' + str(self.vspacing)
    def encode(self):
        return super().encode() + self.hspacing.to_bytes(4, byteorder='big') + self.vspacing.to_bytes(4, byteorder='big')