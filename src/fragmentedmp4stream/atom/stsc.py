"""Samples within the media data are grouped into chunks.
   Chunks can be of different sizes, and the samples within a chunk
   can have different sizes. This table can be used to find the chunk
   that contains a sample, its position, and the associated sample description
"""
from functools import reduce
from .atom import FullBox


def atom_type():
    """Returns this atom type"""
    return 'stsc'


class Entry:
    """Gives the index of the first chunk of a run of chunks
       with the same characteristics
    """
    def __init__(self, file):
        self._first_chunk = int.from_bytes(file.read(4), 'big')
        self._samples_per_chunk = int.from_bytes(file.read(4), 'big')
        self._sample_description_index = int.from_bytes(file.read(4), 'big')

    def __str__(self):
        return f'{self._first_chunk}:{self._samples_per_chunk}:{self._sample_description_index}'

    def __repr__(self):
        return f'Entry({self._first_chunk}, ' \
               f'{self._samples_per_chunk}, ' \
               f'{self._sample_description_index})'

    @property
    def first_chunk(self):
        """Index of the first chunk in this run of chunks that share the
           same samples-per-chunk and sample-description-index
        """
        return self._first_chunk

    @property
    def samples_per_chunk(self):
        """number of samples in each of the chunks in this run"""
        return self._samples_per_chunk

    @property
    def sample_description_index(self):
        """Index of the sample entry that describes the samples in this chunk"""
        return self._sample_description_index

    def to_bytes(self):
        """Returns data entry as bytestream, ready to be sent to socket"""
        ret = self._first_chunk.to_bytes(4, byteorder='big')
        ret += self._samples_per_chunk.to_bytes(4, byteorder='big')
        ret += self._sample_description_index.to_bytes(4, byteorder='big')
        return ret


class Box(FullBox):
    """Sample-to-chunk, partial data-offset information"""
    entries = []

    def __repr__(self):
        ret = super().__repr__() + \
              " entries{first_chunk:samples_per_chunk:sample_description_index}:" + \
              ''.join('{'+str(k)+'}' for k in self.entries)
        return ret

    def _read_entry(self, file):
        """Reads entry from file"""
        return Entry(file)

    def _init_from_file(self, file):
        super()._init_from_file(file)
        self.entries = self._read_entries(file)

    def _init_from_args(self, **kwargs):
        self.type = 'stsc'
        super()._init_from_args(**kwargs)
        self.size = 16

    def to_bytes(self):
        ret = super().to_bytes() + \
              len(self.entries).to_bytes(4, byteorder='big')
        if self.entries:
            ret += reduce(lambda a, b: a + b, map(lambda x: x.to_bytes, self.entries))
        return ret
