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

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = 16
        self.type = 'trun'
        self.samples = []
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

    def encode(self):
        ret = super().encode() + len(self.samples).to_bytes(4, byteorder='big')
        if Flags.DataOffsetPresent in self.tr_flags:
            ret += self.data_offset.to_bytes(4, byteorder='big')
        if Flags.FirstSampleFlagsPresent in self.tr_flags:
            ret += self.first_sample_flags.to_bytes(4, byteorder='big')
        for s in self.samples:
            ret += s.encode()
        return ret