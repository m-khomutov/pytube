from .atom import FullBox


class Entry:
    def __init__(self, first_chunk, samples_per_chunk, sample_description_index):
        self.first_chunk = first_chunk
        self.samples_per_chunk = samples_per_chunk
        self.sample_description_index = sample_description_index

    def __repr__(self):
        return str(self.first_chunk)+":"+str(self.samples_per_chunk)+":"+str(self.sample_description_index)

    def encode(self):
        return self.first_chunk.to_bytes(4, byteorder='big') + \
               self.samples_per_chunk.to_bytes(4, byteorder='big') + \
               self.sample_description_index.to_bytes(4, byteorder='big')

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        self.entries = []
        if f != None:
            self._readfile(f)
        else:
            self.type = 'stsc'
            self.size = 16

    def __repr__(self):
        ret = super().__repr__() + " entries{first_chunk:samples_per_chunk:sample_description_index}:"
        for s in self.entries:
            ret += "{" + str(s) + "}"
        return ret

    def _readfile(self, f):
        count = int.from_bytes(self._readsome(f, 4), "big")
        for i in range(count):
            first_chunk = int.from_bytes(self._readsome(f, 4), "big")
            samples_per_chunk = int.from_bytes(self._readsome(f, 4), "big")
            sample_description_index = int.from_bytes(self._readsome(f, 4), "big")
            self.entries.append(Entry(first_chunk, samples_per_chunk, sample_description_index))

    def encode(self):
        ret = super().encode()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        for s in self.entries:
            ret += s.encode();
        return ret