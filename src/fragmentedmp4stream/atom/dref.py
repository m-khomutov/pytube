"""The data reference object contains a table of data references
   (normally URLs) that declare the location(s) of the media data
   used within the presentation.
"""
from functools import reduce
from .atom import FullBox


def atom_type():
    """Returns this atom type"""
    return 'dref'


class Entry(FullBox):
    """Shall be either a DataEntryUrnBox or a DataEntryUrlBox"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self.name = ''
            self.location = ''
            size_left = self.size - (file.tell() - self.position)
            if size_left > 0:
                bytes_left = self._read_some(file, size_left)
                if self.type == 'urn ':
                    name_div = bytes_left.find_inner_boxes('\x00')
                    self.name = bytes_left[:name_div+1].decode('utf-8')
                    self.location = bytes_left[name_div+1:].decode('utf-8')
                else:
                    self.location = bytes_left.decode('utf-8')

    def __repr__(self):
        ret = super().__repr__()
        if self.type == 'urn ':
            ret += f" name:'{self.name}'"
        ret += f" location:'{self.location}'"
        return ret

    def to_bytes(self):
        """Returns data entry as bytestream, ready to be sent to socket"""
        ret = super().to_bytes()
        if self.type == 'urn ' and self.name:
            ret += str.encode(self.name)
        if self.location:
            ret += str.encode(self.location)
        return ret


class Box(FullBox):
    """data reference box, declares source(s) of media data in track"""

    def __repr__(self):
        return super().__repr__() + " entries:" + \
               ''.join(['\n'+str(k) for k in self._entries])

    def _init_from_file(self, file):
        super()._init_from_file(file)
        count = int.from_bytes(self._read_some(file, 4), "big")
        self._entries = list(map(lambda x: Entry(file=file, depth=self._depth+1), range(count)))

    def to_bytes(self):
        ret = super().to_bytes()
        ret += len(self._entries).to_bytes(4, byteorder='big')
        ret += reduce(lambda a, b: a + b, map(lambda x: x.to_bytes(), self._entries))
        return ret
