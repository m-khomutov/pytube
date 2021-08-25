"""Defines overall information which is media-independent,
   and relevant to the entire presentation considered as a whole
"""
from functools import reduce
from .atom import FullBox


class Box(FullBox):
    """Movie header, overall declarations"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readfile(file)

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

    def _readfile(self, file):
        if self.version == 1:
            self.time = (int.from_bytes(self._readsome(file, 8), "big"),
                         int.from_bytes(self._readsome(file, 8), "big"))
            self.timescale = int.from_bytes(self._readsome(file, 4), "big")
            self.duration = int.from_bytes(self._readsome(file, 8), "big")
        else:
            self.time = (int.from_bytes(self._readsome(file, 4), "big"),
                         int.from_bytes(self._readsome(file, 4), "big"))
            self.timescale = int.from_bytes(self._readsome(file, 4), "big")
            self.duration = int.from_bytes(self._readsome(file, 4), "big")

        self.rate = int.from_bytes(self._readsome(file, 4), "big")
        self.volume = int.from_bytes(self._readsome(file, 2), "big")
        self._readsome(file, 10)
        self.matrix = list(
            map(lambda x: int.from_bytes(self._readsome(file, 4), "big"), range(9))
        )
        self._readsome(file, 24)
        self.next_track_id = int.from_bytes(self._readsome(file, 4), "big")

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
