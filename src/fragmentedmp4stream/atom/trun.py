"""Track fragment run"""
from functools import reduce
from enum import IntFlag
from .atom import FullBox


class Frame:
    """Data frame to store in the run box"""
    duration, offset, size = 0, 0, 0
    composition_time = None
    data = b''

    def __str__(self):
        return f'duration:{self.duration} offset:{self.offset}' \
               f'size:{self.size} composition_time:{self.composition_time}'

    def __repr__(self):
        return self.__str__()


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
        self._fields = (kwargs.get('duration', None),
                        kwargs.get('size', None),
                        kwargs.get('flags', None),
                        kwargs.get('composition_time_offset', None))
        self.initial_offset = kwargs.get('initial_offset', 0)

    def __repr__(self):
        return '{' + ','.join(map(lambda x: '' if x is None else str(x), self._fields)) + '}'

    def to_bytes(self):
        """Returns sample optional fields as bytestream, ready to be sent to socket"""
        none_filter = filter(lambda x: x is not None, self._fields)
        return reduce(lambda a, b: a + b, [k.to_bytes(4, byteorder='big') for k in none_filter])


class Box(FullBox):
    """Track fragment run box"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.tr_flags = Flags(self.flags)
        self._samples = []
        if file is not None:
            self._readfile(file)
        else:
            self.size = 16
            self.type = 'trun'
            self.tr_flags = Flags(kwargs.get("flags", 0))
            self.first_sample_flags = kwargs.get("first_sample_flags", 0)
            self.data_offset = 0
            if Flags.DATA_OFFSET in self.tr_flags:
                self.size += 4
            if Flags.FIRST_SAMPLE_FLAGS in self.tr_flags:
                self.size += 4

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
        self._samples.append(OptionalFields(duration=sample_duration,
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
                        ''.join([str(k) for k in self._samples])

    def to_bytes(self):
        ret = super().to_bytes() + len(self._samples).to_bytes(4, byteorder='big')
        if Flags.DATA_OFFSET in self.tr_flags:
            ret += self.data_offset.to_bytes(4, byteorder='big')
        if Flags.FIRST_SAMPLE_FLAGS in self.tr_flags:
            ret += self.first_sample_flags.to_bytes(4, byteorder='big')
        return ret + reduce(lambda a, b: a + b, map(lambda x: x.to_bytes(), self._samples))

    def _readfile(self, file):
        count = int.from_bytes(self._read_some(file, 4), "big")
        if Flags.DATA_OFFSET in self.tr_flags:
            self.data_offset = int.from_bytes(self._read_some(file, 4), "big")
        if Flags.FIRST_SAMPLE_FLAGS in self.tr_flags:
            self.first_sample_flags = int.from_bytes(self._read_some(file, 4), "big")
        self._samples = [map(lambda: self._read_sample(file), range(count))]

    def _read_sample(self, file):
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
