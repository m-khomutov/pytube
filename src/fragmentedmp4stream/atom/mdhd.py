"""The media header declares overall information that is media-independent,
   and relevant to characteristics of the media in a track.
"""
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'mdhd'


@full_box_derived
class Box(FullBox):
    """Media header box, overall information about the media"""
    creation_time = 0
    modification_time = 0
    timescale = 0
    duration = 0
    language = ''

    def __repr__(self):
        return super().__repr__() + \
              f' creation time:{self.creation_time}' \
              f' modification time:{self.modification_time}' \
              f' timescale:{self.timescale}' \
              f' duration:{self.duration}' \
              f' language:{self.language}'

    @property
    def media_duration_sec(self):
        """Returns media duration in seconds"""
        return self.duration / self.timescale

    def init_from_file(self, file):
        if self.version == 1:
            self.creation_time = int.from_bytes(self._read_some(file, 8), "big")
            self.modification_time = int.from_bytes(self._read_some(file, 8), "big")
            self.timescale = int.from_bytes(self._read_some(file, 4), "big")
            self.duration = int.from_bytes(self._read_some(file, 8), "big")
        else:
            self.creation_time = int.from_bytes(self._read_some(file, 4), "big")
            self.modification_time = int.from_bytes(self._read_some(file, 4), "big")
            self.timescale = int.from_bytes(self._read_some(file, 4), "big")
            self.duration = int.from_bytes(self._read_some(file, 4), "big")

        lang = self._read_some(file, 2)
        self.language = chr(((lang[0] >> 2) & 0x1f) + 0x60) + \
            chr((((lang[0] & 0x03) << 3) | (lang[1] >> 5)) + 0x60) + \
            chr((lang[1] & 0x1f) + 0x60)
        self._read_some(file, 2)

    def to_bytes(self):
        ret = super().to_bytes()
        if self.version == 1:
            ret += self.creation_time.to_bytes(8, byteorder='big')
            ret += self.modification_time.to_bytes(8, byteorder='big')
            ret += self.timescale.to_bytes(4, byteorder='big')
            ret += self.duration.to_bytes(8, byteorder='big')
        else:
            ret += self.creation_time.to_bytes(4, byteorder='big')
            ret += self.modification_time.to_bytes(4, byteorder='big')
            ret += self.timescale.to_bytes(4, byteorder='big')
            ret += self.duration.to_bytes(4, byteorder='big')
        lang, offset = 0, 14
        for symbol in self.language:
            digit = ord(symbol)-0x60
            for i in range(5):
                lang |= ((digit >> i) & 1) << offset
                offset -= 1
        ret += lang.to_bytes(2, byteorder='big')
        ret += (0).to_bytes(2, byteorder='big')
        return ret
