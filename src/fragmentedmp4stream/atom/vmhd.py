"""Video media header, overall information"""
from functools import reduce
from .atom import FullBox


def atom_type():
    """Returns this atom type"""
    return 'vmhd'


class Box(FullBox):
    """Video media header box"""
    _graphics_mode = 0
    _color_channels = []

    def __repr__(self):
        return super().__repr__() + " graphics mode:" + str(self._graphics_mode) + \
               " color:" + str(self._color_channels)

    def _init_from_file(self, file):
        super()._init_from_file(file)
        self._graphics_mode = int.from_bytes(self._read_some(file, 2), "big")
        self._color_channels = list(map(lambda x: int.from_bytes(self._read_some(file, 2), "big"),
                                        range(3)))

    def to_bytes(self):
        """Returns box as bytestream, ready to be sent to socket"""
        res = super().to_bytes() + self._graphics_mode.to_bytes(2, byteorder='big')
        return res + reduce(lambda a, b: a + b,
                            map(lambda cl: cl.to_bytes(2, byteorder='big'), self._color_channels))
