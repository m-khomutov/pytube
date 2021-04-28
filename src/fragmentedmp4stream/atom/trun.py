from .atom import FullBox
from enum import IntFlag

class Frame:
    def __init__(self):
        self.duration = 0
        self.offset = 0
        self.size = 0
        self.composition_time = None
        self.data = []

class Flags(IntFlag):
    DataOffsetPresent = 0x000001
    FirstSampleFlagsPresent = 0x000004
    SampleDurationPresent = 0x000100
    SampleSizePresent = 0x000200
    SampleFlagsPresent = 0x000400
    SampleCompositionTimeOffsetsPresent = 0x000800

class Sample:
    def __init__(self, duration, size, flags, composition_time_offset):
        self.duration = duration
        self.size = size
        self.flags = flags
        self.composition_time_offset = composition_time_offset
    def encode(self):
        ret = b''
        if self.duration != None:
            ret += self.duration.to_bytes(4, byteorder='big')
        if self.size != None:
            ret += self.size.to_bytes(4, byteorder='big')
        if self.flags != None:
            ret += self.flags.to_bytes(4, byteorder='big')
        if self.composition_time_offset != None:
            ret += self.composition_time_offset.to_bytes(4, byteorder='big')
        return ret
    def __repr__(self):
        ret = '{'
        if self.duration != None:
            ret += str(self.duration)
        ret += ','
        if self.size != None:
            ret += str(self.size)
        ret += ','
        if self.flags != None:
            ret += hex(self.flags)
        ret += ','
        if self.composition_time_offset != None:
            ret += str(self.composition_time_offset)
        ret +='}'
        return ret

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        self.tr_flags = Flags(self.flags)
        self.samples=[]
        if f != None:
            self._readfile(f)
        else:
            self.size = 16
            self.type = 'trun'
            self.tr_flags = Flags(kwargs.get("flags", 0))
            self.first_sample_flags = kwargs.get("firstsampleflags", 0)
            self.data_offset = 0
            if Flags.DataOffsetPresent in self.tr_flags:
                self.size += 4
            if Flags.FirstSampleFlagsPresent in self.tr_flags:
                self.size += 4
    def add_sample(self, *args, **kwargs):
        sample_duration = sample_size = sample_flags = sample_time_offsets = None
        if Flags.SampleDurationPresent in self.tr_flags:
            sample_duration = kwargs.get('duration', 0)
            self.size += 4
        if Flags.SampleSizePresent in self.tr_flags:
            sample_size = kwargs.get('size', 0)
            self.size += 4
        if Flags.SampleFlagsPresent in self.tr_flags:
            sample_flags = kwargs.get('flags', 0)
            self.size += 4
        if Flags.SampleCompositionTimeOffsetsPresent in self.tr_flags:
            sample_time_offsets = kwargs.get('timeoffsets', 0)
            self.size += 4
        self.samples.append(Sample(sample_duration, sample_size, sample_flags, sample_time_offsets))
    def __repr__(self):
        ret=super().__repr__()
        if Flags.DataOffsetPresent in self.tr_flags:
            ret += ' data_offset:' + str(self.data_offset)
        if Flags.FirstSampleFlagsPresent in self.tr_flags:
            ret += ' first_sample_flags:' + hex(self.first_sample_flags)
        ret += ' samples{duration,size,flags,ctime offset}:'
        for s in self.samples:
            ret += str(s)
        return ret
    def encode(self):
        ret = super().encode() + len(self.samples).to_bytes(4, byteorder='big')
        if Flags.DataOffsetPresent in self.tr_flags:
            ret += self.data_offset.to_bytes(4, byteorder='big')
        if Flags.FirstSampleFlagsPresent in self.tr_flags:
            ret += self.first_sample_flags.to_bytes(4, byteorder='big')
        for s in self.samples:
            ret += s.encode()
        return ret
    def _readfile(self, f):
        count = int.from_bytes(self._readsome(f, 4), "big")
        if Flags.DataOffsetPresent in self.tr_flags:
            self.data_offset = int.from_bytes(self._readsome(f, 4), "big")
        if Flags.FirstSampleFlagsPresent in self.tr_flags:
            self.first_sample_flags = int.from_bytes(self._readsome(f, 4), "big")
        for i in range(count):
            duration=size=flags=time_offsets=None
            if Flags.SampleDurationPresent in self.tr_flags:
                duration = int.from_bytes(self._readsome(f, 4), "big")
            if Flags.SampleSizePresent in self.tr_flags:
                size = int.from_bytes(self._readsome(f, 4), "big")
            if Flags.SampleFlagsPresent in self.tr_flags:
                flags = int.from_bytes(self._readsome(f, 4), "big")
            if Flags.SampleCompositionTimeOffsetsPresent in self.tr_flags:
                time_offsets = int.from_bytes(self._readsome(f, 4), "big")
            self.samples.append(Sample(duration, size, flags, time_offsets))