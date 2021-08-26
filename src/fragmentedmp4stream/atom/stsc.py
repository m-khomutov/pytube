"""Samples within the media data are grouped into chunks.
   Chunks can be of different sizes, and the samples within a chunk
   can have different sizes. This table can be used to find the chunk
   that contains a sample, its position, and the associated sample description
"""
from .atom import FullBox


class Entry:
    """Gives the index of the first chunk of a run of chunks
       with the same characteristics
    """
    def __init__(self, file):
        self.first_chunk = int.from_bytes(file.read(4), "big")
        self.samples_per_chunk = int.from_bytes(file.read(4), "big")
        self.sample_description_index = int.from_bytes(file.read(4), "big")

    def __repr__(self):
        return f'{self.first_chunk}:{self.samples_per_chunk}:{self.sample_description_index}'

    def to_bytes(self):
        """Returns data entry as bytestream, ready to be sent to socket"""
        ret = self.first_chunk.to_bytes(4, byteorder='big')
        ret += self.samples_per_chunk.to_bytes(4, byteorder='big')
        ret += self.sample_description_index.to_bytes(4, byteorder='big')
        return ret


class Box(FullBox):
    """Sample-to-chunk, partial data-offset information"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.entries = []
        if file is not None:
            self._readfile(file)
        else:
            self.type = 'stsc'
            self.size = 16

    def __repr__(self):
        ret = super().__repr__() + \
              " entries{first_chunk:samples_per_chunk:sample_description_index}:" + \
              ''.join('{'+str(k)+'}' for k in self.entries)
        return ret

    def _readfile(self, file):
        count = int.from_bytes(self._read_some(file, 4), "big")
        self.entries = list(map(lambda x: Entry(file), range(count)))

    def to_bytes(self):
        ret = super().to_bytes() + \
              len(self.entries).to_bytes(4, byteorder='big')
        for entry in self.entries:
            ret += entry.to_bytes()
        return ret
