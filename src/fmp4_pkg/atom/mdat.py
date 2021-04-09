from .atom import Box


class Box(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = bytearray()
    def append(self, sample):
        self.data += sample
        self.size += len(sample)
    def empty(self):
        return len(self.data) == 0
    def clear(self):
        self.data = bytearray()
        self.size = 8
    def encode(self):
        return super().encode() + self.data
