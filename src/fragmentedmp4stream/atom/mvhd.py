"""Defines overall information which is media-independent,
   and relevant to the entire presentation considered as a whole
"""
from functools import reduce
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'mvhd'


@full_box_derived
class Box(FullBox):
    """Movie header, overall declarations"""
    time = (0, 0)
    timescale = 0
    duration = 0
    rate = 0
    volume = 0
    matrix = []
    next_track_id = 0

    def __repr__(self):
        ret = super().__repr__() + \
              f" creation time:{self.time[0]} " \
              f"modification time:{self.time[1]} " \
              f"timescale:{self.timescale} " \
              f"duration:{self.duration} " \
              f"rate:{self.rate} volume:{self.volume} "
        ret += 'matrix:[' + ' '.join(hex(k) for k in self.matrix) + ']'
        ret += f" nextTrackID:{self.next_track_id}"
        return ret

    def init_from_file(self, file):
        if self.version == 1:
            self.time = (int.from_bytes(self._read_some(file, 8), "big"),
                         int.from_bytes(self._read_some(file, 8), "big"))
            self.timescale = int.from_bytes(self._read_some(file, 4), "big")
            self.duration = int.from_bytes(self._read_some(file, 8), "big")
        else:
            self.time = (int.from_bytes(self._read_some(file, 4), "big"),
                         int.from_bytes(self._read_some(file, 4), "big"))
            self.timescale = int.from_bytes(self._read_some(file, 4), "big")
            self.duration = int.from_bytes(self._read_some(file, 4), "big")

        self.rate = int.from_bytes(self._read_some(file, 4), "big")
        self.volume = int.from_bytes(self._read_some(file, 2), "big")
        self._read_some(file, 10)
        self.matrix = list(
            map(lambda x: int.from_bytes(self._read_some(file, 4), "big"), range(9))
        )
        self._read_some(file, 24)
        self.next_track_id = int.from_bytes(self._read_some(file, 4), "big")

    def to_bytes(self):
        ret = super().to_bytes()
        if self.version == 1:
            ret += self.time[0].to_bytes(8, byteorder='big')
            ret += self.time[1].to_bytes(8, byteorder='big')
            ret += self.timescale.to_bytes(4, byteorder='big')
            ret += self.duration.to_bytes(8, byteorder='big')
        else:
            ret += self.time[0].to_bytes(4, byteorder='big')
            ret += self.time[1].to_bytes(4, byteorder='big')
            ret += self.timescale.to_bytes(4, byteorder='big')
            ret += self.duration.to_bytes(4, byteorder='big')

        ret += self.rate.to_bytes(4, byteorder='big')
        ret += self.volume.to_bytes(2, byteorder='big')
        ret += (0).to_bytes(2, byteorder='big')
        ret += (0).to_bytes(8, byteorder='big')
        ret += reduce(
            lambda a, b: a + b, map(lambda x: x.to_bytes(4, byteorder='big'), self.matrix)
        )
        ret += reduce(
            lambda a, b: a + b, map(lambda x: (0).to_bytes(4, byteorder='big'), range(6))
        )
        ret += self.next_track_id.to_bytes(4, byteorder='big')
        return ret
