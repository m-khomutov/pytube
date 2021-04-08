from .atom import FullBox


class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = 16
        self.type = 'mfhd'
        self.sequence_number = 0
    def __repr__(self):
        return super().__repr__() + " seqnum:" + str(self.sequence_number)
    def encode(self):
        return super().encode() + self.sequence_number.to_bytes(4, byteorder='big')