"""Reads MP4 format file"""
from enum import IntEnum
from .atom.atom import Box
from .atom import stco, stsc, stsz, tkhd, mdhd, co64, stts, ctts, hdlr, stsd, trun
from .atom import ftyp, vmhd, mvhd, smhd, dref  # noqa # pylint: disable=unused-import


class ClockRate(IntEnum):
    """Trick to declare a 90kHz video clock rate"""
    VIDEO_Khz = 90000


class SamplesStscInfo:
    """Sample to chunk information"""
    def __init__(self, entries):
        self._entries = []
        self._index = [0, 0]
        for i, entry in enumerate(entries):
            if i > 0:
                run_size = entry.first_chunk - entries[i-1].first_chunk
                self._entries.extend([entries[i-1].samples_per_chunk] * run_size)

    def is_iterate_offset(self):
        """Verifies if two step offset should be iterated"""
        return self._index[1] >= len(self._entries) or self._index[0] == 0

    def next(self):
        """Iterates two step offset"""
        if self._index[1] < len(self._entries):
            self._index[0] += 1
            if self._index[0] >= self._entries[self._index[1]]:
                self._index[0] = 0
                self._index[1] += 1


class SamplesStcoInfo:
    """Chunk offset information"""
    def __init__(self, entries):
        self._entries = entries
        self._index = 0

    def offset(self):
        """Returns Chunk offset"""
        return self._entries[self._index]

    def next(self):
        """Iterates chunk"""
        if self._index < len(self._entries):
            self._index += 1


class SamplesStszInfo:
    """Sample sizes"""
    def __init__(self, entries):
        self._entries = entries
        self._index = 0

    def current_size(self):
        """Returns size of the current sample"""
        return self._entries[self._index]

    def next(self):
        """Iterates sample"""
        if self._index < len(self._entries):
            self._index += 1


class SamplesSttsInfo:
    """Decoding Time to sample"""
    def __init__(self, entries):
        self._entries = entries
        self._index = [0, 0]

    def current_decoding_time(self):
        """Returns decoding time of the current sample"""
        return self._entries[self._index[1]].delta

    def next(self):
        """Iterates sample"""
        self._index[0] += 1
        if self._index[0] >= self._entries[self._index[1]].count:
            self._index[0] = 0
            self._index[1] += 1


class SamplesCttsInfo:
    """Composition Time to sample"""
    def __init__(self):
        self.entries = []
        self.index = [0, 0]

    def current_composition_time(self):
        """Returns composition time of the current sample"""
        if self.entries:
            return self.entries[self.index[1]].offset
        return None

    def next(self):
        """Iterates sample"""
        if self.entries:
            self.index[0] += 1
            if self.index[0] >= self.entries[self.index[1]].count:
                self.index[0] = 0
                self.index[1] += 1


class SamplesInfo:  # pylint: disable=too-many-instance-attributes
    """Composite information of sample atoms"""
    offset, size, unit_size_bytes = 0, 0, 0
    timescale_multiplier = 1

    def __init__(self):
        self.stco = SamplesStcoInfo([])
        self.stsz = SamplesStszInfo([])
        self.stts = SamplesSttsInfo([])
        self.ctts = SamplesCttsInfo()
        self.stsc = SamplesStscInfo([])

    def fill_chunk_offset_info(self, info):
        """Sets chunk offset information"""
        self.stco = SamplesStcoInfo(info)

    def fill_sample_sizes_info(self, info):
        """Sets sample sizes information"""
        self.stsz = SamplesStszInfo(info)

    def fill_decoding_time_info(self, info):
        """Sets decoding time information"""
        self.stts = SamplesSttsInfo(info)

    def fill_composition_time_info(self, info):
        """Sets composition time information"""
        self.ctts.entries = info

    def fill_sample_chunk_info(self, info):
        """Sets sample to chunk information"""
        self.stsc = SamplesStscInfo(info)

    def sample(self):
        """Returns a specific sample information"""
        ret = trun.Frame(self.unit_size_bytes)
        if self.stsc.is_iterate_offset():
            ret.offset = self.offset = self.stco.offset()
        else:
            self.offset += self.size
            ret.offset = self.offset
        ret.size = self.size = self.stsz.current_size()
        ret.duration = self.stts.current_decoding_time()
        ret.composition_time = self.ctts.current_composition_time()
        return ret

    def next(self):
        """Iterates overall sample information"""
        self.stsc.next()
        if self.stsc.is_iterate_offset():
            self.stco.next()
        self.stsz.next()
        self.stts.next()
        self.ctts.next()


class Reader:
    """Reads atom from MP4 format file"""
    media_duration_sec = 0.

    def __init__(self, filename):
        self.boxes = []
        self.samples_info = {}
        self.media_header = {}
        self.video_stream_type = stsd.VideoCodecType.UNKNOWN
        self.file = open(filename, "rb")
        try:
            track_id, handler = 1, ''
            while True:
                box, track_id, handler = self._get_next_box(0, track_id, handler)
                self.boxes.append(box)
        except EOFError:
            pass

    def __del__(self):
        self.file.close()

    def __repr__(self):
        ret = ""
        for box in self.boxes:
            ret += str(box) + "\n"
        return ret

    def __str__(self):
        return self.__repr__()

    def find_box(self, box_type):
        """Searches box by atom type"""
        ret = []
        for box in self.boxes:
            ret.extend(box.find_inner_boxes(box_type))
        return ret

    def next_sample(self, track_id):
        """Reads track next sample from file"""
        sample = self.samples_info[track_id].sample()
        self.samples_info[track_id].next()
        self.file.seek(sample.offset)
        sample.data = self.file.read(sample.size)
        return sample

    def sample(self, offset, size):
        """Reads a sample from file"""
        self.file.seek(offset)
        return self.file.read(size)

    def has_composition_time(self, track_id):
        """Checks if sample has composition time"""
        return len(self.samples_info[track_id].ctts.entries) > 0

    def _get_next_box(self, depth, track_id, handler):
        """Reads a box from file"""
        box = Box(file=self.file, depth=depth)
        if not box.container():
            module = globals().get(box.type)
            if module is not None:
                self.file.seek(box.position)
                box, track_id, handler = self._get_info_box(module, depth, track_id, handler)
            self.file.seek(box.position + box.size)
        else:
            box_size = box.size - (self.file.tell() - box.position)
            while box_size > 0:
                next_box, track_id, handler = self._get_next_box(box.indent + 1, track_id, handler)
                box_size -= next_box.size
                box.add_inner_box(next_box)
        return box, track_id, handler

    def _get_info_box(self, module, depth, track_id, handler):
        """Reads no container box from file"""
        box = getattr(module, 'Box')(file=self.file, depth=depth, hdlr=handler)
        try:
            track_id, handler = getattr(self, f'_on_{box.type}')(box, track_id, handler)
        except AttributeError:
            pass
        return box, track_id, handler

    def _on_tkhd(self, box, track_id, handler):
        """Manager Track header box"""
        if box.type == tkhd.atom_type():
            track_id = box.track_id
            self.samples_info[track_id] = SamplesInfo()
        return track_id, handler

    def _on_mdhd(self, box, track_id, handler):
        """Manager Media header box"""
        if box.type == mdhd.atom_type():
            self.media_header[track_id] = box
        return track_id, handler

    def _on_hdlr(self, box, track_id, handler):
        """Manager Handler box"""
        if box.type == hdlr.atom_type():
            handler = box.handler_type
            if handler == 'vide':
                self.samples_info[track_id].timescale_multiplier = \
                    int(ClockRate.VIDEO_Khz.value / self.media_header[track_id].timescale)
                self.media_duration_sec = self.media_header[track_id].media_duration_sec
        return track_id, handler

    def _on_stts(self, box, track_id, handler):
        """Manager Sample Decoding Time box"""
        if box.type == stts.atom_type():
            self.samples_info[track_id].fill_decoding_time_info(box.entries)
        return track_id, handler

    def _on_ctts(self, box, track_id, handler):
        """Manager Sample Composition Time box"""
        if box.type == ctts.atom_type():
            self.samples_info[track_id].fill_composition_time_info(box.entries)
        return track_id, handler

    def _on_stsd(self, box, track_id, handler):
        """Manager Sample Descriptions box"""
        if box.type == stsd.atom_type():
            if handler == 'vide':
                self.video_stream_type = box.video_stream_type
                self.samples_info[track_id].unit_size_bytes = \
                    box.video_configuration_box().unit_length
        return track_id, handler

    def _on_stsz(self, box, track_id, handler):
        """Manager Sample Sizes box"""
        if box.type == stsz.atom_type():
            if box.sample_size == 0:
                self.samples_info[track_id].fill_sample_sizes_info(box.entries)
            else:
                self.samples_info[track_id].fill_sample_sizes_info([box.sample_size])
        return track_id, handler

    def _on_stsc(self, box, track_id, handler):
        """Manager Sample Chunk box"""
        if box.type == stsc.atom_type():
            self.samples_info[track_id].fill_sample_chunk_info(box.entries)
        return track_id, handler

    def _on_stco(self, box, track_id, handler):
        """Manager Sample Chunk Offsets box"""
        if box.type == stco.atom_type():
            self.samples_info[track_id].fill_chunk_offset_info(box.entries)
        return track_id, handler

    def _on_co64(self, box, track_id, handler):
        """Manager Sample Chunk 64bit Offsets box"""
        if box.type == co64.atom_type():
            self.samples_info[track_id].fill_chunk_offset_info(box.entries)
        return track_id, handler
