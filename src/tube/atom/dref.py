"""The data reference object contains a table of data references
   (normally URLs) that declare the location(s) of the media data
   used within the presentation.
"""
from functools import reduce
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'dref'


@full_box_derived
class Entry(FullBox):
    """Shall be either a DataEntryUrnBox or a DataEntryUrlBox"""
    def __init__(self, *args, **kwargs):
        self.name = ''
        self.location = ''
        super().__init__(*args, **kwargs)

    def init_from_file(self, file):
        size_left = self.size - (file.tell() - self.position)
        if size_left > 0:
            bytes_left = self._read_some(file, size_left)
            if self.type == 'urn ':
                name_div = bytes_left.find_inner_boxes('\x00')
                self.name = bytes_left[:name_div+1].decode('utf-8')
                self.location = bytes_left[name_div+1:].decode('utf-8')
            else:
                self.location = bytes_left.decode('utf-8')

    def init_from_args(self, **kwargs):
        super().init_from_args(**kwargs)
        if kwargs.get('name'):
            self.name = kwargs.get('name', '')
            self.size += len(self.name) + 1
        if kwargs.get('location'):
            self.location = kwargs.get('location', '')
            self.size += len(self.location) + 1

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
            ret += str.encode(self.name) + b'\x00'
        if self.location:
            ret += str.encode(self.location) + b'\x00'
        return ret


@full_box_derived
class Box(FullBox):
    """data reference box, declares source(s) of media data in track"""
    def __init__(self, *args, **kwargs):
        self._entries = []
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return super().__repr__() + " entries:" + \
               ''.join(['\n'+str(k) for k in self._entries])

    def _read_entry(self, file):
        """Reads entry from file"""
        return Entry(file=file, depth=self._depth+1)

    def init_from_file(self, file):
        self._entries = self._read_entries(file)

    def init_from_args(self, **kwargs):
        super().init_from_args(**kwargs)
        self.type = atom_type()
        self.size = 16

    def add_entry(self, entry):
        self._entries.append(entry)
        self.size += entry.size

    def to_bytes(self):
        ret = super().to_bytes()
        ret += len(self._entries).to_bytes(4, byteorder='big')
        if self._entries:
            ret += reduce(lambda a, b: a + b, map(lambda x: x.to_bytes(), self._entries))
        return ret
