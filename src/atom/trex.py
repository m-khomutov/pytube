from .atom import FullBox


class SampleFlags:
    def __init__(self, depends_on, is_difference):
        self.sample_depends_on = depends_on
        self.sample_is_depended_on = 0
        self.sample_has_redundancy = 0
        self.sample_padding_value = 0
        self.sample_is_difference_sample = is_difference
        self.sample_degradation_priority = 0

    def value(self):
        return (self.sample_depends_on & 3) << 24 |\
               (self.sample_is_depended_on & 3) << 22 | \
               (self.sample_has_redundancy & 3) << 20 | \
               (self.sample_padding_value & 7) << 17 | \
               (self.sample_is_difference_sample & 1) << 16 | \
               (self.sample_degradation_priority & 0xffff)

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = 32
        self.type = 'trex'
        self.trackID = kwargs.get("trakid", 0)
        self.default_sample_description_index = kwargs.get("defindex", 1)
        self.default_sample_duration = kwargs.get("defduration", 0)
        self.default_sample_size = kwargs.get("defsize", 0)
        self.default_sample_flags = kwargs.get("defflags", 0)
        pass
    def __repr__(self):
        return super().__repr__()
    def encode(self):
        return super().encode() + self.trackID.to_bytes(4, byteorder='big') + \
                                  self.default_sample_description_index.to_bytes(4, byteorder='big') + \
                                  self.default_sample_duration.to_bytes(4, byteorder='big') + \
                                  self.default_sample_size.to_bytes(4, byteorder='big') + \
                                  self.default_sample_flags.to_bytes(4, byteorder='big')