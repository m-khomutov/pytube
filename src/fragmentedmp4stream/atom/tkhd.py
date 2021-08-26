"""Track header, overall information about the track"""
from functools import reduce
from .atom import FullBox


class Box(FullBox):
    """Track header box"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readfile(file)

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

    def _readfile(self, file):
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

    def to_bytes(self):
        result = super().to_bytes()
        if self.version == 1:
            for time in self.timing:
                result += time.to_bytes(8, byteorder='big')
            result += self.track_id.to_bytes(4, byteorder='big')
            result += (0).to_bytes(4, byteorder='big')
            result += self.duration.to_bytes(8, byteorder='big')
        else:
            for time in self.timing:
                result += time.to_bytes(4, byteorder='big')
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
