from .atom import FullBox


class Entry(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self.name = ''
            self.location = ''
            left = self.size - (f.tell() - self.position)
            if self.type == 'urn ':
                for i in left:
                    b = self._readsome(f, left).decode("utf-8")
                    self.name += b
                    if b == 0:
                        break;
                left -= len(self.name)
            if left > 0: self.location = self._readsome(f, left).decode("utf-8")

    def __repr__(self):
        ret = super().__repr__()
        if self.type == 'urn ':
            ret += " name:" + self.name
        ret += " location:" + self.location
        return ret

    def encode(self):
        ret = super().encode()
        if self.type == 'urn ':
            if len(self.name): ret += str.encode(self.name)
        if len(self.location): ret += str.encode(self.location)
        return ret

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readfile(f)

    def _readfile(self, f):
        count = int.from_bytes(self._readsome(f, 4), "big")
        self._entries = []
        for i in range(count):
            self._entries.append(Entry(file=f,depth=self._depth+1))
        pass

    def encode(self):
        ret = super().encode()
        ret += len(self._entries).to_bytes(4, byteorder='big')
        for e in self._entries:
            ret += e.encode()
        return ret