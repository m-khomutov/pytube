"""The movie fragment header contains a sequence number, as a safety check"""
from .atom import FullBox


class Box(FullBox):
    """movie fragment header box"""

    def __repr__(self):
        return super().__repr__() + f" sequence num:{self.sequence_number}"

    def _init_from_file(self, file):
        super()._init_from_file(file)
        self.sequence_number = int.from_bytes(self._read_some(file, 4), "big")

    def _init_from_args(self, **kwargs):
        super()._init_from_args(**kwargs)
        self.size = 16
        self.type = 'mfhd'
        self.sequence_number = 0

    def to_bytes(self):
        return super().to_bytes() + self.sequence_number.to_bytes(4, byteorder='big')
