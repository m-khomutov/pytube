"""Track extends box sets up default values used by the movie fragments"""
from .atom import FullBox, full_box_derived


class SampleFlags:
    """Sample flags field in sample fragments"""
    _is_depended_on, _has_redundancy, _padding_value, _degradation_priority = 0, 0, 0, 0

    def __init__(self, depends_on, is_difference):
        self._depends_on, self._is_difference_sample = depends_on, is_difference

    def __str__(self):
        return 'depends on={} is depended on={} has redundancy={} padding value={}' \
               ' degradation priority={}'.format(self._depends_on, self._is_depended_on,
                                                 self._has_redundancy, self._padding_value,
                                                 self._degradation_priority)

    def __repr__(self):
        return f'SampleFlags({self._depends_on}, {self.is_depended_on})'

    def __int__(self):
        return (self._depends_on & 3) << 24 | \
               (self._is_depended_on & 3) << 22 | \
               (self._has_redundancy & 3) << 20 | \
               (self._padding_value & 7) << 17 | \
               (self._is_difference_sample & 1) << 16 | \
               (self._degradation_priority & 0xffff)

    @property
    def depends_on(self):
        """Returns one of the following four values:
           0: the dependency of this sample is unknown;
           1: this sample does depend on others (not an I picture);
           2: this sample does not depend on others (I picture);
           3: reserved
        """
        return self._depends_on

    @property
    def is_depended_on(self):
        """Returns one of the following four values:
           0: the dependency of other samples on this sample is unknown;
           1: other samples depend on this one (not disposable);
           2: no other sample depends on this one (disposable);
           3: reserved
        """
        return self.is_depended_on

    @property
    def has_redundancy(self):
        """Returns one of the following four values:
           0: it is unknown whether there is redundant coding in this sample;
           1: there is redundant coding in this sample;
           2: there is no redundant coding in this sample;
           3: reserved
        """
        return self._has_redundancy


@full_box_derived
class Box(FullBox):
    """Track extends box"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = 32
        self.type = 'trex'
        self.track_id = kwargs.get("track_id", 0)
        self.default_sample_index = kwargs.get("default_index", 1)
        self.default_sample_duration = kwargs.get("default_duration", 0)
        self.default_sample_size = kwargs.get("default_size", 0)
        self.default_sample_flags = kwargs.get("default_flags", 0)

    def __repr__(self):
        return super().__repr__() + \
               ' track:{} defaults: (description index={} duration={} size={} flags={:04x}'.format(
                   self.track_id, self.default_sample_index,
                   self.default_sample_duration, self.default_sample_size,
                   self.default_sample_flags
               )

    def to_bytes(self):
        """Returns the box as bytestream, ready to be sent to socket"""
        result = super().to_bytes() + self.track_id.to_bytes(4, byteorder='big')
        result += self.default_sample_index.to_bytes(4, byteorder='big')
        result += self.default_sample_duration.to_bytes(4, byteorder='big')
        result += self.default_sample_size.to_bytes(4, byteorder='big')
        return result + self.default_sample_flags.to_bytes(4, byteorder='big')
