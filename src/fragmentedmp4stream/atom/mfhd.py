"""The movie fragment header contains a sequence number, as a safety check"""
from .atom import FullBox, full_box_derived


@full_box_derived
class Box(FullBox):
    """movie fragment header box"""
    sequence_number = 0

    def __repr__(self):
        return super().__repr__() + f" sequence num:{self.sequence_number}"

    def init_from_file(self, file):
        self.sequence_number = int.from_bytes(self._read_some(file, 4), "big")

    def init_from_args(self, **kwargs):
        self.type = 'mfhd'
        self.size = 16
        self.sequence_number = 0

    def to_bytes(self):
        return super().to_bytes() + self.sequence_number.to_bytes(4, byteorder='big')
