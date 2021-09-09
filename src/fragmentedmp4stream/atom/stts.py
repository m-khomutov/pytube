"""Decoding time-to-sample"""
from .atom import FullBox


def atom_type():
    """Returns this atom type"""
    return 'stts'


class Entry:
    """Consecutive samples with the same duration"""
    def __init__(self, count, delta):
        self.count = count
        self.delta = delta

    def __str__(self):
        return f'{{{self.count}:{self.delta}}}'

    def __repr__(self):
        return f'Entry({self.count}, {self.delta})'

    def empty(self):
        """Verifies of consecutive samples exist"""
        return self.count == 0

    def to_bytes(self):
        """Returns sample the box entry as bytestream, ready to be sent to socket"""
        return self.count.to_bytes(4, byteorder='big') + self.delta.to_bytes(4, byteorder='big')


class Box(FullBox):
    """Decoding time-to-sample box"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.entries = []
        if file is not None:
            self._readfile(file)
        else:
            self.type = 'stts'
            self.size = 16

    def __repr__(self):
        return super().__repr__() + " entries:" + ''.join([str(k) for k in self.entries])

    def _readfile(self, file):
        count = int.from_bytes(self._read_some(file, 4), "big")
        self.entries = list(map(lambda x: self._read_entry(file), range(count)))

    def _read_entry(self, file):
        """Get Entry from file"""
        return Entry(int.from_bytes(self._read_some(file, 4), "big"),
                     int.from_bytes(self._read_some(file, 4), "big"))

    def to_bytes(self):
        ret = super().to_bytes() + len(self.entries).to_bytes(4, byteorder='big')
        for entry in self.entries:
            ret += entry.to_bytes()
        return ret
