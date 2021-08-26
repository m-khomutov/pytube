"""The movie fragment header contains a sequence number, as a safety check"""
from .atom import FullBox


class Box(FullBox):
    """movie fragment header box"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self.sequence_number = int.from_bytes(self._read_some(file, 4), "big")
        else:
            self.size = 16
            self.type = 'mfhd'
            self.sequence_number = 0

    def __repr__(self):
        return super().__repr__() + f" sequence num:{self.sequence_number}"

    def to_bytes(self):
        return super().to_bytes() + self.sequence_number.to_bytes(4, byteorder='big')
