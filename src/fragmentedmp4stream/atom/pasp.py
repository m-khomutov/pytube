"""Pixel aspect ratio. This extension is mandatory for video formats that use non-square pixels"""
from .atom import Box as Atom


class Box(Atom):
    """Pixel aspect ratio box"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self.h_spacing = int.from_bytes(self._readsome(file, 4), "big")
            self.v_spacing = int.from_bytes(self._readsome(file, 4), "big")
        else:
            self.type = 'pasp'
            self.size = 16
            self.h_spacing = kwargs.get("h_spacing", 0)
            self.v_spacing = kwargs.get("v_spacing", 0)

    def __repr__(self):
        return super().__repr__() +\
               ' h_spacing:' + str(self.h_spacing) + 'v_spacing:' + str(self.v_spacing)

    def to_bytes(self):
        return super().to_bytes() + self.h_spacing.to_bytes(4, byteorder='big') +\
                                    self.v_spacing.to_bytes(4, byteorder='big')
