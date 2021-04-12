from .atom import FullBox
from enum import IntFlag

class Flags(IntFlag):
    BaseDataOffsetPresent = 0x000001
    SampleDescriptionIndexPresent = 0x000002
    DefaultSampleDurationPresent = 0x000008
    DefaultSampleSizePresent = 0x000010
    DefaultSampleFlagsPresent = 0x000020
    DurationIsEmpty = 0x010000

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tf_flags = Flags(self.flags)
        self.size = 16
        if Flags.BaseDataOffsetPresent in self.tf_flags: self.size += 8
        if Flags.SampleDescriptionIndexPresent in self.tf_flags: self.size += 4
        if Flags.DefaultSampleDurationPresent in self.tf_flags: self.size += 4
        if Flags.DefaultSampleSizePresent in self.tf_flags: self.size += 4
        if Flags.DefaultSampleFlagsPresent in self.tf_flags: self.size += 4
        self.type = 'tfhd'
        self.trackID = kwargs.get("trakid", 0)
        self.base_data_offset = kwargs.get("dataoffset", 0)
        self.sample_description_index = kwargs.get("descriptionindex", 0)
        self.default_sample_duration = kwargs.get("defsampleduration", 0)
        self.default_sample_size = kwargs.get("defsamplesize", 0)
        self.default_sample_flags = kwargs.get("defsampleflags", 0)
    def __repr__(self):
        return super().__repr__() + " trackId:" + str(self.trackID)
    def encode(self):
        ret = super().encode() + self.trackID.to_bytes(4, byteorder='big')
        if Flags.BaseDataOffsetPresent in self.tf_flags:
            ret += self.base_data_offset.to_bytes(8, byteorder='big')
        if Flags.SampleDescriptionIndexPresent in self.tf_flags:
            ret += self.sample_description_index.to_bytes(4, byteorder='big')
        if Flags.DefaultSampleDurationPresent in self.tf_flags:
            ret += self.default_sample_duration.to_bytes(4, byteorder='big')
        if Flags.DefaultSampleSizePresent in self.tf_flags:
            ret += self.default_sample_size.to_bytes(4, byteorder='big')
        if Flags.DefaultSampleFlagsPresent in self.tf_flags:
            ret += self.default_sample_flags.to_bytes(4, byteorder='big')
        return ret