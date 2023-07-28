"""MP4 files are formed as a series of objects, called boxes.
   All data is contained in boxes; there is no other data within the file.
"""


class BoxIterator:
    """Makes Box iterable object"""
    def __init__(self, box):
        self._box = box
        self._index = 0

    def __next__(self):
        try:
            result = self._box[self._index]
            self._index += 1
            return result
        except IndexError:
            pass
        raise StopIteration

    def __iter__(self):
        return self

    @property
    def position(self):
        """Returns current position in box iteration"""
        return self._index

    def reset(self):
        """Resets iteration"""
        self._index = 0


class Box:
    """An object-oriented building block defined by a unique type identifier and length
       called ‘atom’ in some specifications, including the first definition of MP4
    """
    @staticmethod
    def _read_some(file, some):
        ret = file.read(some)
        if len(ret) == some:
            return ret
        raise EOFError()

    def __init__(self, *args, **kwargs):
        len(args)
        self._user_type = []
        self._inner_boxes = []
        self._depth = 0
        self.position = 0
        file = kwargs.get("file", None)
        if file:
            self._fromfile(file, kwargs.get("depth", None))
            self.init_from_file(file)
        else:
            self.type = kwargs.get("type", None)
            self.size = 8
            self.init_from_args(**kwargs)

    def __repr__(self):
        ret = " " * (self._depth * 2) + \
              f"{self.type} pos:{self.position} size:{self.full_size()}"
        if len(self._user_type) == 16:
            ret += f" user type:{self._user_type}"
        if isinstance(self, Box):
            ret += ''.join('\n'+str(k) for k in self._inner_boxes)
        return ret

    def __str__(self):
        return self.__repr__()

    def __getitem__(self, item):
        return self._inner_boxes[item]

    def __iter__(self):
        return BoxIterator(self)

    def init_from_file(self, file):
        """Virtual function for derived classes to initialize from file"""

    def init_from_args(self, **kwargs):
        """Virtual function for derived classes to initialize from args"""

    def _read_entry(self, file):
        """Virtual function to read an entry from file"""

    def add_inner_box(self, box, parent_type=''):
        """Adds atom to inner boxes"""
        if parent_type == '':
            box.indent = self._depth + 2
            self._inner_boxes.append(box)
        else:
            parent = self.find_inner_boxes(parent_type)
            if parent:
                parent[0].add_inner_box(box)

    def find_inner_boxes(self, searched_type):
        """Finds all inner boxes of given type"""
        ret = []
        if searched_type == self.type:
            ret.append(self)
            return ret
        for box in self._inner_boxes:
            ret.extend(box.find_inner_boxes(searched_type))
        return ret

    def container(self):
        """verifies if the box is container"""
        ret = (self.type == 'moov' or self.type == 'trak' or self.type == 'edts')
        ret = (ret or self.type == 'mdia' or self.type == 'minf' or self.type == 'dinf')
        ret = (ret or self.type == 'stbl' or self.type == 'mvex' or self.type == 'moof')
        return ret or self.type == 'traf'

    def _read_entries(self, file):
        """Reads a set of entries"""
        count = int.from_bytes(file.read(4), "big")
        return list(map(lambda x: self._read_entry(file), range(count)))

    @property
    def indent(self):
        """Returns indentation for logging"""
        return self._depth

    @indent.setter
    def indent(self, value):
        """Sets indentation for logging"""
        self._depth = value

    def to_bytes(self):
        """Returns the box as bytestream, ready to be sent to socket"""
        full_size = self.full_size()
        ret = []
        if full_size >= 0xffffffff:
            ret.append(b'\x00\x00\x00\x01')
        else:
            ret.append(full_size.to_bytes(4, byteorder='big'))
        ret.append(self.type.encode())
        if full_size >= 0xffffffff:
            ret.append(full_size.to_bytes(8, byteorder='big'))
        if self.type == 'uuid':
            ret.append(self._user_type)
        if isinstance(self, Box):
            ret.extend([x.to_bytes() for x in self._inner_boxes])
        return b''.join(ret)

    def full_size(self):
        """Returns whole size of the box with all inner boxes"""
        ret = self.size
        for box in self._inner_boxes:
            ret += box.full_size()
        return ret

    def _fromfile(self, file, depth):
        self.position = file.tell()
        self.size = int.from_bytes(self._read_some(file, 4), "big")
        self.type = self._read_some(file, 4).decode("utf-8")
        if self.size == 1:
            self.size = int.from_bytes(self._read_some(file, 8), "big")
        if self.type == 'uuid':
            self._user_type = self._read_some(file, 16)
        self._depth = depth


def full_box_derived(cls):
    """Decorator to add parent initialization in child boxes"""
    class Wrapper(cls):
        """Class decorator redefining initialization methods"""
        def init_from_file(self, file):
            """Reads box fields from mp4 file"""
            FullBox.init_from_file(self, file)
            super().init_from_file(file)

        def init_from_args(self, **kwargs):
            """Gets box fields from arguments"""
            FullBox.init_from_args(self, **kwargs)
            super().init_from_args(**kwargs)
    return Wrapper


class FullBox(Box):
    """A box with a version number and flags field"""
    def __init__(self, *args, **kwargs):
        self.version = 0
        self.flags = 0
        super().__init__(*args, **kwargs)

    def __repr__(self):
        ret = super().__repr__() + f" version:{self.version} flags:{self.flags:x}"
        ret += '\n'.join(str(k) for k in self._inner_boxes)
        return ret

    def init_from_file(self, file):
        self.version = self._read_some(file, 1)[0]
        self.flags = int.from_bytes(self._read_some(file, 3), "big")

    def init_from_args(self, **kwargs):
        self.version = kwargs.get("version", 0)
        self.flags = kwargs.get("flags", 0)
        self.size = 12

    def to_bytes(self):
        return b''.join([
            super().to_bytes(),
            self.version.to_bytes(1, byteorder='big'),
            self.flags.to_bytes(3, byteorder='big')
        ])
