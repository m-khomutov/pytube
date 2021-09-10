"""Provides the offset between decoding time and composition time.
   Since decoding time must be less than the composition time,
   the offsets are expressed as unsigned numbers such that
   CT(n) = DT(n) + CTTS(n)
   where CTTS(n) is the (uncompressed) table entry for sample n.
   """
from functools import reduce
from .atom import FullBox


def atom_type():
    """Returns this atom type"""
    return 'ctts'


class Entry:
    """Composition time to sample box entry"""
    def __init__(self, file):
        self._count = int.from_bytes(file.read(4), 'big')
        self._offset = int.from_bytes(file.read(4), 'big')

    def __repr__(self):
        return f'Entry({self._count}, {self._offset})'

    def __str__(self):
        return f"{self._count}:{self._offset}"

    @property
    def count(self):
        """Counts the number of consecutive samples that have the given offset"""
        return self._count

    @property
    def offset(self):
        """Offset between CT and DT, such that CT(n) = DT(n) + CTTS(n)"""
        return self._offset

    def to_bytes(self):
        """Returns time entry as bytestream, ready to be sent to socket"""
        return self._count.to_bytes(4, byteorder='big') + self._offset.to_bytes(4, byteorder='big')


class Box(FullBox):
    """Composition time to sample box"""

    def __repr__(self):
        return super().__repr__() + " entries:" + \
               ''.join(['{'+str(k)+'}' for k in self.entries])

    def _init_from_file(self, file):
        super()._init_from_file(file)
        self.entries = self._read_entries(file)

    def _init_from_args(self, **kwargs):
        self.type = 'ctts'
        super()._init_from_args(**kwargs)
        self.size = 16

    def _read_entry(self, file):
        """Reads entry from file"""
        return Entry(file)

    def to_bytes(self):
        ret = super().to_bytes()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        ret += reduce(lambda a, b: a + b, map(lambda x: x.to_bytes(), self.entries))
        return ret
