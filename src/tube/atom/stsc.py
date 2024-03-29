"""Samples within the media data are grouped into chunks.
   Chunks can be of different sizes, and the samples within a chunk
   can have different sizes. This table can be used to find the chunk
   that contains a sample, its position, and the associated sample description
"""
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'stsc'


class Entry:
    """Gives the index of the first chunk of a run of chunks
       with the same characteristics
    """
    def __init__(self, **kwargs):
        if kwargs.get('file'):
            file = kwargs.get('file')
            self._first_chunk = int.from_bytes(file.read(4), 'big')
            self._samples_per_chunk = int.from_bytes(file.read(4), 'big')
            self._sample_description_index = int.from_bytes(file.read(4), 'big')
        else:
            self._first_chunk = kwargs.get('first_chunk', 1)
            self._samples_per_chunk = kwargs.get('samples_per_chunk', 1)
            self._sample_description_index = kwargs.get('sample_description_index', 1)

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
        return b''.join(
            [
                self._first_chunk.to_bytes(4, byteorder='big'),
                self._samples_per_chunk.to_bytes(4, byteorder='big'),
                self._sample_description_index.to_bytes(4, byteorder='big')
            ])


@full_box_derived
class Box(FullBox):
    """Sample-to-chunk, partial data-offset information"""
    def __init__(self, *args, **kwargs):
        self.entries = []
        self._first_chunk = 1
        super().__init__(*args, **kwargs)

    def __repr__(self):
        ret = super().__repr__() + \
              " entries{first_chunk:samples_per_chunk:sample_description_index}:" + \
              ''.join('{'+str(k)+'}' for k in self.entries)
        return ret

    def _read_entry(self, file):
        """Reads entry from file"""
        return Entry(file=file)

    def init_from_file(self, file):
        self.entries = self._read_entries(file)

    def init_from_args(self, **kwargs):
        self.type = 'stsc'
        self.size = 16

    def append(self, frame_size: int):
        if not self.entries:
            self.entries.append(Entry())
            self.size += 12
        self._first_chunk += 1

    def to_bytes(self):
        rc = [super().to_bytes(), len(self.entries).to_bytes(4, byteorder='big')]
        if self.entries:
            rc.extend([x.to_bytes() for x in self.entries])
        return b''.join(rc)
