"""Decoding time-to-sample"""
from typing import Optional
from .atom import FullBox, full_box_derived


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
        return b''.join([
            self.count.to_bytes(4, byteorder='big'),
            self.delta.to_bytes(4, byteorder='big')
        ])


@full_box_derived
class Box(FullBox):
    """Decoding time-to-sample box"""
    def __init__(self, *args, **kwargs):
        self.entries = []
        self._last_timestamp: Optional[int] = None
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return super().__repr__() + " entries:" + ''.join([str(k) for k in self.entries])

    def init_from_file(self, file):
        self.entries = self._read_entries(file)

    def init_from_args(self, **kwargs):
        self.type = 'stts'
        self.size = 16

    def append(self, timestamp: int):
        if not self._last_timestamp:
            self._last_timestamp = timestamp
        elif timestamp != self._last_timestamp:
            delta: int = timestamp - self._last_timestamp
            self._last_timestamp = timestamp
            if not self.entries or self.entries[-1].delta != delta:
                self.entries.append(Entry(1, delta))
                self.size += 8
            else:
                self.entries[-1].count += 1

    def _read_entry(self, file):
        """Get Entry from file"""
        return Entry(int.from_bytes(self._read_some(file, 4), "big"),
                     int.from_bytes(self._read_some(file, 4), "big"))

    def to_bytes(self):
        rc = [super().to_bytes(), len(self.entries).to_bytes(4, byteorder='big')]
        if self.entries:
            rc.extend([e.to_bytes() for e in self.entries])
        return b''.join(rc)
