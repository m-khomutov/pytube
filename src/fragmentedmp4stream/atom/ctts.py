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
        self.count = int.from_bytes(file.read(4), "big")
        self.offset = int.from_bytes(file.read(4), "big")

    def __repr__(self):
        return f"{self.count}:{self.offset}"

    def to_bytes(self):
        """Returns time entry as bytestream, ready to be sent to socket"""
        return self.count.to_bytes(4, byteorder='big') + self.offset.to_bytes(4, byteorder='big')


class Box(FullBox):
    """Composition time to sample box"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.entries = []
        if file is not None:
            self._readfile(file)
        else:
            self.type = 'ctts'
            self.size = 16

    def __repr__(self):
        return super().__repr__() + " entries:" + \
               ''.join(['{'+str(k)+'}' for k in self.entries])

    def _readfile(self, file):
        count = int.from_bytes(self._read_some(file, 4), "big")
        self.entries = list(map(lambda x: Entry(file), range(count)))

    def to_bytes(self):
        ret = super().to_bytes()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        ret += reduce(lambda a, b: a + b, map(lambda x: x.to_bytes(), self.entries))
        return ret
