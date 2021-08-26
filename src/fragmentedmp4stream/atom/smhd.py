"""The sound media header contains general presentation information,
   independent of the coding, for audio media
"""
from .atom import FullBox


class Box(FullBox):
    """Sound media header, overall information (sound track only"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readfile(file)

    def __repr__(self):
        return super().__repr__() + f" balance:{self.balance}"

    def _readfile(self, file):
        self.balance = int.from_bytes(self._read_some(file, 2), "big")
        self._read_some(file, 2)

    def to_bytes(self):
        ret = super().to_bytes() + \
              self.balance.to_bytes(2, byteorder='big') + \
              (0).to_bytes(2, byteorder='big')
        return ret
