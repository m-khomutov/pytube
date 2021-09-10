"""Track fragment header sets up information and defaults used for
runs of samples"""
from enum import IntFlag
from .atom import FullBox, full_box_derived


class Flags(IntFlag):
    """Track flags for optional fields"""
    BASE_DATA_OFFSET_PRESENT = 0x000001
    SAMPLE_DESCRIPTION_INDEX_PRESENT = 0x000002
    DEFAULT_SAMPLE_DURATION_PRESENT = 0x000008
    DEFAULT_SAMPLE_SIZE_PRESENT = 0x000010
    DEFAULT_SAMPLE_FLAGS_PRESENT = 0x000020
    DURATION_IS_EMPTY = 0x010000


class OptionalFields:
    """Track fragment header optional fields"""
    _size = 0

    def __init__(self, flags, **kwargs):
        self._flags = flags
        file = kwargs.get("file", None)
        if file is not None:
            self.read_from_file(file)
        else:
            if Flags.BASE_DATA_OFFSET_PRESENT in flags:
                self._size += 8
                self._base_offset = kwargs.get("data_offset", 0)
            if Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT in flags:
                self._size += 4
                self._description_index = kwargs.get("description_index", 0)
            if Flags.DEFAULT_SAMPLE_DURATION_PRESENT in flags:
                self._size += 4
                self._duration = kwargs.get("default_sample_duration", 0)
            if Flags.DEFAULT_SAMPLE_SIZE_PRESENT in flags:
                self._size += 4
                self._sample_size = kwargs.get("default_sample_size", 0)
            if Flags.DEFAULT_SAMPLE_FLAGS_PRESENT in flags:
                self._size += 4
                self._sample_flags = kwargs.get("default_sample_flags", 0)

    def __repr__(self):
        ret = ''
        if Flags.BASE_DATA_OFFSET_PRESENT in self._flags:
            ret += ' base_data_offset:{}'.format(self._base_offset)
        if Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT in self._flags:
            ret += ' index:{}'.format(self._description_index)
        ret += ' default_sample['
        if Flags.DEFAULT_SAMPLE_DURATION_PRESENT in self._flags:
            ret += ' duration:{}'.format(self._duration)
        if Flags.DEFAULT_SAMPLE_SIZE_PRESENT in self._flags:
            ret += ' size:{}'.format(self._sample_size)
        if Flags.DEFAULT_SAMPLE_FLAGS_PRESENT in self._flags:
            ret += ' flags:{:x}'.format(self._sample_flags)
        return ret

    def __len__(self):
        return self._size

    def read_from_file(self, file):
        """Get optional field from mp4 file"""
        if Flags.BASE_DATA_OFFSET_PRESENT in self._flags:
            self._base_offset = int.from_bytes(file.read(8), "big")
            self._size += 8
        if Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT in self._flags:
            self._description_index = int.from_bytes(file.read(4), "big")
            self._size += 4
        if Flags.DEFAULT_SAMPLE_DURATION_PRESENT in self._flags:
            self._duration = int.from_bytes(file.read(4), "big")
            self._size += 4
        if Flags.DEFAULT_SAMPLE_SIZE_PRESENT in self._flags:
            self._sample_size = int.from_bytes(file.read(4), "big")
            self._size += 4
        if Flags.DEFAULT_SAMPLE_FLAGS_PRESENT in self._flags:
            self._sample_flags = int.from_bytes(file.read(4), "big")
            self._size += 4

    def to_bytes(self):
        """Returns optional fields as bytestream, ready to be sent to socket"""
        ret = b''
        if Flags.BASE_DATA_OFFSET_PRESENT in self._flags:
            ret += self._base_offset.to_bytes(8, byteorder='big')
        if Flags.SAMPLE_DESCRIPTION_INDEX_PRESENT in self._flags:
            ret += self._description_index.to_bytes(4, byteorder='big')
        if Flags.DEFAULT_SAMPLE_DURATION_PRESENT in self._flags:
            ret += self._duration.to_bytes(4, byteorder='big')
        if Flags.DEFAULT_SAMPLE_SIZE_PRESENT in self._flags:
            ret += self._sample_size.to_bytes(4, byteorder='big')
        if Flags.DEFAULT_SAMPLE_FLAGS_PRESENT in self._flags:
            ret += self._sample_flags.to_bytes(4, byteorder='big')
        return ret


@full_box_derived
class Box(FullBox):
    """Track fragment header box"""
    track_id = 0
    _optional_fields = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = 16 + len(self._optional_fields)

    def __repr__(self):
        return super().__repr__() + " trackId:" + str(self.track_id) +\
               str(self._optional_fields) + ' ]'

    def to_bytes(self):
        return super().to_bytes() + self.track_id.to_bytes(4, byteorder='big') +\
               self._optional_fields.to_bytes()

    def init_from_file(self, file):
        self.track_id = int.from_bytes(self._read_some(file, 4), "big")
        self._optional_fields = OptionalFields(Flags(self.flags), file=file)

    def init_from_args(self, **kwargs):
        self._optional_fields = \
            OptionalFields(Flags(self.flags),
                           data_offset=kwargs.get('data_offset', None),
                           description_index=kwargs.get("description_index", None),
                           default_sample_duration=kwargs.get('default_sample_duration', None),
                           default_sample_size=kwargs.get("default_sample_size", None),
                           default_sample_flags=kwargs.get('default_sample_flags', None))
        self.type = 'tfhd'
        self.track_id = kwargs.get("track_id", 0)
