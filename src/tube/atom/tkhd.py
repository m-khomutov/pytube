"""Track header, overall information about the track"""
import time
from functools import reduce
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'tkhd'


@full_box_derived
class Box(FullBox):
    """Track header box"""
    def __init__(self, *args, **kwargs):
        self.timing = (0, 0)
        self.track_id, self.duration = 0, 0
        self.track_info = (0, 0, 0)  # layer alternative_group volume
        self.matrix = []
        self.width, self.height = 0, 0
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return super().__repr__() + \
              ' creation time={} modification time={} track id={} duration={} layer={}' \
              ' alternative group={} volume={:04x} matrix=[{}]' \
              ' width={} height={}'.format(self.timing[0],
                                           self.timing[1],
                                           self.track_id,
                                           self.duration,
                                           self.track_info[0],
                                           self.track_info[1],
                                           self.track_info[2],
                                           ' '.join([hex(k) for k in self.matrix]),
                                           self.width,
                                           self.height)

    def init_from_file(self, file):
        if self.version == 1:
            self.timing = (
                int.from_bytes(self._read_some(file, 8), "big"),  # creation
                int.from_bytes(self._read_some(file, 8), "big")   # modification
            )
            self.track_id = int.from_bytes(self._read_some(file, 4), "big")
            self._read_some(file, 4)
            self.duration = int.from_bytes(self._read_some(file, 8), "big")
        else:
            self.timing = (
                int.from_bytes(self._read_some(file, 4), "big"),  # creation
                int.from_bytes(self._read_some(file, 4), "big")   # modification
            )
            self.track_id = int.from_bytes(self._read_some(file, 4), "big")
            self._read_some(file, 4)
            self.duration = int.from_bytes(self._read_some(file, 4), "big")
        self._read_some(file, 8)
        self.track_info = (
            int.from_bytes(self._read_some(file, 2), "big"),  # layer
            int.from_bytes(self._read_some(file, 2), "big"),  # alternate_group
            int.from_bytes(self._read_some(file, 2), "big")   # volume
        )
        self._read_some(file, 2)
        self.matrix = [int.from_bytes(k, 'big')
                       for k in map(lambda x: self._read_some(file, 4), range(9))]
        self.width = int.from_bytes(self._read_some(file, 4), "big")
        self.height = int.from_bytes(self._read_some(file, 4), "big")

    def init_from_args(self, **kwargs):
        super().init_from_args(**kwargs)
        self.type = atom_type()
        self.timing = kwargs.get('creation_time', int(time.time())), kwargs.get('modification_time', int(time.time()))
        self.track_id = kwargs.get('track_id', 0)
        self.duration = kwargs.get('duration', 0)
        self.track_info = (kwargs.get('layer', 0),
                           kwargs.get('alternate_group', 0),
                           kwargs.get('volume', 0),
                           )
        self.matrix = kwargs.get('matrix', [0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000])
        self.width = kwargs.get('width', 0)
        self.height = kwargs.get('height', 0)
        self.size = 104 if self.version == 1 else 92

    def to_bytes(self):
        result = super().to_bytes()
        if self.version == 1:
            for t in self.timing:
                result += t.to_bytes(8, byteorder='big')
            result += self.track_id.to_bytes(4, byteorder='big')
            result += (0).to_bytes(4, byteorder='big')
            result += self.duration.to_bytes(8, byteorder='big')
        else:
            for t in self.timing:
                result += t.to_bytes(4, byteorder='big')
            result += self.track_id.to_bytes(4, byteorder='big')
            result += (0).to_bytes(4, byteorder='big')
            result += self.duration.to_bytes(4, byteorder='big')
        result += (0).to_bytes(8, byteorder='big')
        for info in self.track_info:
            result += info.to_bytes(2, byteorder='big')
        result += (0).to_bytes(2, byteorder='big')
        result += reduce(lambda a, b: a + b,
                         map(lambda x: x.to_bytes(4, byteorder='big'), self.matrix))
        result += self.width.to_bytes(4, byteorder='big')
        result += self.height.to_bytes(4, byteorder='big')
        return result
