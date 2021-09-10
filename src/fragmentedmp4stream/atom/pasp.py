"""Pixel aspect ratio. This extension is mandatory for video formats that use non-square pixels"""
from .atom import Box as Atom


class Box(Atom):
    """Pixel aspect ratio box"""

    def __repr__(self):
        return super().__repr__() +\
               f' h_spacing:{self.h_spacing} v_spacing:{self.v_spacing}'

    def _init_from_file(self, file):
        super()._init_from_file(file)
        self.h_spacing = int.from_bytes(self._read_some(file, 4), "big")
        self.v_spacing = int.from_bytes(self._read_some(file, 4), "big")

    def _init_from_args(self, **kwargs):
        self.type = 'pasp'
        super()._init_from_args(**kwargs)
        self.size = 16
        self.h_spacing = kwargs.get("h_spacing", 0)
        self.v_spacing = kwargs.get("v_spacing", 0)

    def to_bytes(self):
        return super().to_bytes() + self.h_spacing.to_bytes(4, byteorder='big') +\
                                    self.v_spacing.to_bytes(4, byteorder='big')
