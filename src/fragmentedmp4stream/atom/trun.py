"""Track fragment run"""
from functools import reduce
from enum import IntFlag
from .atom import FullBox, full_box_derived


class FrameIter:
    """Chunk iterator of data frame """
    def __init__(self, data, size, unit_size_bytes):
        self._chunk_offset = 0
        self._data = data
        self.size = size
        self._unit_size_bytes = unit_size_bytes

    def __iter__(self):
        return self

    def __next__(self):
        if self._chunk_offset >= self.size:
            raise StopIteration
        if self._unit_size_bytes == 0:
            self._chunk_offset = self.size
            return self._data
        chunk_size = int.from_bytes(
            self._data[self._chunk_offset:self._chunk_offset+self._unit_size_bytes], byteorder='big'
        )
        self._chunk_offset += self._unit_size_bytes + chunk_size
        return self._data[self._chunk_offset-chunk_size:self._chunk_offset]


class Frame:
    """Data frame to store in the run box"""
    def __init__(self, unit_size_bytes=0):
        self.duration, self.offset, self.size = 0, 0, 0
        self.composition_time = None
        self._data = b''
        self._chunk_offset = 0
        self._unit_size_bytes = unit_size_bytes

    def __iter__(self):
        return FrameIter(self._data, self.size, self._unit_size_bytes)

    def __str__(self):
        ret = f'duration:{self.duration} offset:{self.offset} size:{self.size}'
        if self.composition_time:
            ret += f' composition_time:{self.composition_time}'
        return ret

    def __repr__(self):
        return self.__str__()

    def get_data(self):
        """Returns frame as bytestream"""
        return self._data

    def set_data(self, value):
        """Sets frame data bytestream"""
        self._data = value

    data = property(get_data, set_data)


class Flags(IntFlag):
    """Define number of optional fields"""
    DATA_OFFSET = 0x000001
    FIRST_SAMPLE_FLAGS = 0x000004
    SAMPLE_DURATION = 0x000100
    SAMPLE_SIZE = 0x000200
    SAMPLE_FLAGS = 0x000400
    SAMPLE_COMPOSITION_TIME_OFFSETS = 0x000800


class OptionalFields:
    """Sample optional fields"""
    def __init__(self, **kwargs):
        self._fields = [kwargs.get('duration', None),
                        kwargs.get('size', None),
                        kwargs.get('flags', None),
                        kwargs.get('composition_time_offset', None)]
        self.initial_offset = kwargs.get('initial_offset', 0)

    def __repr__(self):
        return '{' + ','.join(map(lambda x: '' if x is None else str(x), self._fields)) + '}'

    @property
    def duration(self):
        """Returns sample duration"""
        return self._fields[0]

    @duration.setter
    def duration(self, value):
        """Sets sample duration"""
        self._fields[0] = value

    @property
    def size(self):
        """Returns sample size"""
        return self._fields[1]

    @size.setter
    def size(self, value):
        """Sets sample size"""
        self._fields[1] = value

    @property
    def flags(self):
        """Returns sample duration"""
        return self._fields[2]

    @flags.setter
    def flags(self, value):
        """Sets sample duration"""
        self._fields[2] = value

    @property
    def composition_time_offset(self):
        """Returns sample composition time offset"""
        return self._fields[3]

    @composition_time_offset.setter
    def composition_time_offset(self, value):
        """Sets sample composition time offset"""
        self._fields[3] = value

    def to_bytes(self):
        """Returns sample optional fields as bytestream, ready to be sent to socket"""
        none_filter = filter(lambda x: x is not None, self._fields)
        return reduce(lambda a, b: a + b, [k.to_bytes(4, byteorder='big') for k in none_filter])


@full_box_derived
class Box(FullBox):
    """Track fragment run box"""
    def __init__(self, *args, **kwargs):
        self.first_sample_flags, self.data_offset = (0, 0)
        self.samples = []
        super().__init__(*args, **kwargs)
        self.tr_flags = Flags(self.flags)

    def add_sample(self, **kwargs):
        """add optional fields to run box in accordance with flags"""
        sample_duration = sample_size = sample_flags = sample_time_offsets = None
        if Flags.SAMPLE_DURATION in self.tr_flags:
            sample_duration = kwargs.get('duration', 0)
            self.size += 4
        if Flags.SAMPLE_SIZE in self.tr_flags:
            sample_size = kwargs.get('size', 0)
            self.size += 4
        if Flags.SAMPLE_FLAGS in self.tr_flags:
            sample_flags = kwargs.get('flags', 0)
            self.size += 4
        if Flags.SAMPLE_COMPOSITION_TIME_OFFSETS in self.tr_flags:
            sample_time_offsets = kwargs.get('time_offsets', 0)
            self.size += 4
        self.samples.append(OptionalFields(duration=sample_duration,
                                           size=sample_size,
                                           flags=sample_flags,
                                           composition_time_offset=sample_time_offsets,
                                           initial_offset=kwargs.get('initial_offset', 0)))

    def __repr__(self):
        result = super().__repr__()
        if Flags.DATA_OFFSET in self.tr_flags:
            result += ' data_offset:{}'.format(self.data_offset)
        if Flags.FIRST_SAMPLE_FLAGS in self.tr_flags:
            result += ' first_sample_flags:{:x}'.format(self.first_sample_flags)
        return result + ' samples{duration,size,flags,comp_time offset}:' + \
                        ''.join([str(k) for k in self.samples])

    def to_bytes(self):
        ret = super().to_bytes() + len(self.samples).to_bytes(4, byteorder='big')
        if Flags.DATA_OFFSET in self.tr_flags:
            ret += self.data_offset.to_bytes(4, byteorder='big')
        if Flags.FIRST_SAMPLE_FLAGS in self.tr_flags:
            ret += self.first_sample_flags.to_bytes(4, byteorder='big')
        if self.samples:
            ret += reduce(lambda a, b: a + b, map(lambda x: x.to_bytes(), self.samples))
        return ret

    def init_from_file(self, file):
        self.samples = self._read_entries(file)
        if Flags.DATA_OFFSET in self.tr_flags:
            self.data_offset = int.from_bytes(self._read_some(file, 4), "big")
        if Flags.FIRST_SAMPLE_FLAGS in self.tr_flags:
            self.first_sample_flags = int.from_bytes(self._read_some(file, 4), "big")

    def init_from_args(self, **kwargs):
        self.size = 16
        self.type = 'trun'
        self.tr_flags = Flags(kwargs.get("flags", 0))
        self.first_sample_flags = kwargs.get("first_sample_flags", 0)
        self.data_offset = 0
        if Flags.DATA_OFFSET in self.tr_flags:
            self.size += 4
        if Flags.FIRST_SAMPLE_FLAGS in self.tr_flags:
            self.size += 4

    def _read_entry(self, file):
        """read sample fields in accordance with option flags"""
        duration = size = flags = time_offsets = None
        if Flags.SAMPLE_DURATION in self.tr_flags:
            duration = int.from_bytes(self._read_some(file, 4), "big")
        if Flags.SAMPLE_SIZE in self.tr_flags:
            size = int.from_bytes(self._read_some(file, 4), "big")
        if Flags.SAMPLE_FLAGS in self.tr_flags:
            flags = int.from_bytes(self._read_some(file, 4), "big")
        if Flags.SAMPLE_COMPOSITION_TIME_OFFSETS in self.tr_flags:
            time_offsets = int.from_bytes(self._read_some(file, 4), "big")
        return OptionalFields(duration=duration,
                              size=size,
                              flags=flags,
                              composition_time_offset=time_offsets)
