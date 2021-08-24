"""A container box which can hold actual media data for a presentation"""
from .atom import Box as Atom


class Box(Atom):
    """media data container"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = bytearray()

    def append(self, sample):
        """Adds a sample of media data"""
        self.data += sample
        self.size += len(sample)

    def empty(self):
        """Verifies if no data is in the container"""
        return len(self.data) == 0

    def clear(self):
        """Removes media data from container"""
        self.data = bytearray()
        self.size = 8

    def to_bytes(self):
        return super().to_bytes() + self.data
