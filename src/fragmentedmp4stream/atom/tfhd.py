"""Track fragment header sets up information and defaults used for
runs of samples"""
from enum import IntFlag
from collections import OrderedDict
from .atom import FullBox


class Flags(IntFlag):
    """Track flags for optional fields"""
    BASE_DATA_OFFSET_PRESENT = 0x000001
    SAMPLE_DESCRIPTION_INDEX_PRESENT = 0x000002
    DEFAULT_SAMPLE_DURATION_PRESENT = 0x000008
    DEFAULT_SAMPLE_SIZE_PRESENT = 0x000010
    DEFAULT_SAMPLE_FLAGS_PRESENT = 0x000020
    DURATION_IS_EMPTY = 0x010000


class Box(FullBox):
    """Track fragment header box"""
    _optional_fields = OrderedDict()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.tf_flags = Flags(self.flags)
        self.size = 16
        if file is not None:
            self._readfile(file)
        else:
            if Flags.BASE_DATA_OFFSET_PRESENT in self.tf_flags:
                self.size += 8
                self._optional_fields[Flags.BASE_DATA_OFFSET_PRESENT] =\
                    kwargs.get("data_offset", 0)
            if Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT in self.tf_flags:
                self.size += 4
                self._optional_fields[Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT] = \
                    kwargs.get("description_index", 0)
            if Flags.DEFAULT_SAMPLE_DURATION_PRESENT in self.tf_flags:
                self.size += 4
                self._optional_fields[Flags.DEFAULT_SAMPLE_DURATION_PRESENT] = \
                    kwargs.get("default_sample_duration", 0)
            if Flags.DEFAULT_SAMPLE_SIZE_PRESENT in self.tf_flags:
                self.size += 4
                self._optional_fields[Flags.DEFAULT_SAMPLE_SIZE_PRESENT] = \
                    kwargs.get("default_sample_size", 0)
            if Flags.DEFAULT_SAMPLE_FLAGS_PRESENT in self.tf_flags:
                self.size += 4
                self._optional_fields[Flags.DEFAULT_SAMPLE_FLAGS_PRESENT] = \
                    kwargs.get("default_sample_flags", 0)
            self.type = 'tfhd'
            self.track_id = kwargs.get("track_id", 0)

    def __repr__(self):
        ret = super().__repr__() + " trackId:" + str(self.track_id)
        if Flags.BASE_DATA_OFFSET_PRESENT in self.tf_flags:
            ret += ' base_data_offset:{}'.format(
                self._optional_fields[Flags.BASE_DATA_OFFSET_PRESENT]
            )
        if Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT in self.tf_flags:
            ret += ' index:{}'.format(
                self._optional_fields[Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT]
            )
        ret += ' default_sample['
        if Flags.DEFAULT_SAMPLE_DURATION_PRESENT in self.tf_flags:
            ret += ' duration:{}'.format(
                self._optional_fields[Flags.DEFAULT_SAMPLE_DURATION_PRESENT]
            )
        if Flags.DEFAULT_SAMPLE_SIZE_PRESENT in self.tf_flags:
            ret += ' size:{}'.format(
                self._optional_fields[Flags.DEFAULT_SAMPLE_SIZE_PRESENT]
            )
        if Flags.DEFAULT_SAMPLE_FLAGS_PRESENT in self.tf_flags:
            ret += ' flags:{:x}'.format(
                self._optional_fields[Flags.DEFAULT_SAMPLE_FLAGS_PRESENT]
            )
        return ret + ' ]'

    def to_bytes(self):
        ret = super().to_bytes() + self.track_id.to_bytes(4, byteorder='big')
        for key in self._optional_fields:
            if key == Flags.BASE_DATA_OFFSET_PRESENT:
                ret += self._optional_fields[key].to_bytes(8, byteorder='big')
            else:
                ret += self._optional_fields[key].to_bytes(4, byteorder='big')
        return ret

    def _readfile(self, file):
        self.track_id = int.from_bytes(self._readsome(file, 4), "big")
        if Flags.BASE_DATA_OFFSET_PRESENT in self.tf_flags:
            self._optional_fields[Flags.BASE_DATA_OFFSET_PRESENT] =\
                int.from_bytes(self._readsome(file, 8), "big")
            self.size += 8
        if Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT in self.tf_flags:
            self._optional_fields[Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT] =\
                int.from_bytes(self._readsome(file, 4), "big")
            self.size += 4
        if Flags.DEFAULT_SAMPLE_DURATION_PRESENT in self.tf_flags:
            self._optional_fields[Flags.DEFAULT_SAMPLE_DURATION_PRESENT] =\
                int.from_bytes(self._readsome(file, 4), "big")
            self.size += 4
        if Flags.DEFAULT_SAMPLE_SIZE_PRESENT in self.tf_flags:
            self._optional_fields[Flags.DEFAULT_SAMPLE_SIZE_PRESENT] =\
                int.from_bytes(self._readsome(file, 4), "big")
            self.size += 4
        if Flags.DEFAULT_SAMPLE_FLAGS_PRESENT in self.tf_flags:
            self._optional_fields[Flags.DEFAULT_SAMPLE_FLAGS_PRESENT] =\
                int.from_bytes(self._readsome(file, 4), "big")
            self.size += 4
