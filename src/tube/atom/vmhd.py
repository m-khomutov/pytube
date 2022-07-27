"""Video media header, overall information"""
from functools import reduce
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'vmhd'


@full_box_derived
class Box(FullBox):
    """Video media header box"""
    def __init__(self, *args, **kwargs):
        self._graphics_mode = 0
        self._color_channels = []
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return super().__repr__() + " graphics mode:" + str(self._graphics_mode) + \
               " color:" + str(self._color_channels)

    def init_from_file(self, file):
        self._graphics_mode = int.from_bytes(self._read_some(file, 2), "big")
        self._color_channels = list(map(lambda x: int.from_bytes(self._read_some(file, 2), "big"),
                                        range(3)))

    def init_from_args(self, **kwargs):
        super().init_from_args(**kwargs)
        self.type = atom_type()
        self._graphics_mode = kwargs.get('graphics_mode', 0)
        self._color_channels = [int(x) for x in kwargs.get('color_channels', '0 0 0').split(' ')]
        self.size = 20

    def to_bytes(self):
        """Returns box as bytestream, ready to be sent to socket"""
        res = super().to_bytes() + self._graphics_mode.to_bytes(2, byteorder='big')
        return res + reduce(lambda a, b: a + b,
                            map(lambda cl: cl.to_bytes(2, byteorder='big'), self._color_channels))
