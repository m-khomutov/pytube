"""Reads MP4 format file"""
from .atom.atom import Box
from .atom import ftyp, stco, stsc, mvhd, tkhd, mdhd, co64, stts, hdlr,\
    ctts, vmhd, trun, stsd, smhd, dref, stsz, mfhd, tfhd


class FragmentationFinished(Exception):
    """Exception to show end of file fragmentation"""


class SamplesStscInfo:
    """Sample to chunk information"""
    def __init__(self, entries):
        self.entries = []
        self.index = [0, 0]
        for i, entry in enumerate(entries):
            if i > 0:
                run_size = entry.first_chunk - entries[i-1].first_chunk
                self.entries.extend([entries[i-1].samples_per_chunk] * run_size)

    def is_iterate_offset(self):
        """Verifies if two step offset should be iterated"""
        return self.index[1] >= len(self.entries) or self.index[0] == 0

    def next(self):
        """Iterates two step offset"""
        if self.index[1] < len(self.entries):
            self.index[0] += 1
            if self.index[0] >= self.entries[self.index[1]]:
                self.index[0] = 0
                self.index[1] += 1


class SamplesStcoInfo:
    """Chunk offset information"""
    def __init__(self, entries):
        self.entries = entries
        self.index = 0

    def offset(self):
        """Returns Chunk offset"""
        return self.entries[self.index]

    def next(self):
        """Iterates chunk"""
        if self.index < len(self.entries):
            self.index += 1


class SamplesStszInfo:
    """Sample sizes"""
    def __init__(self, entries):
        self.entries = entries
        self.index = 0

    def current_size(self):
        """Returns size of the current sample"""
        return self.entries[self.index]

    def next(self):
        """Iterates sample"""
        if self.index < len(self.entries):
            self.index += 1
        else:
            raise FragmentationFinished('')


class SamplesSttsInfo:
    """Decoding Time to sample"""
    def __init__(self, entries):
        self.entries = entries
        self.index = [0, 0]

    def current_decoding_time(self):
        """Returns decoding time of the current sample"""
        return self.entries[self.index[1]].delta

    def next(self):
        """Iterates sample"""
        self.index[0] += 1
        if self.index[0] >= self.entries[self.index[1]].count:
            self.index[0] = 0
            self.index[1] += 1


class SamplesCttsInfo:
    """Composition Time to sample"""
    def __init__(self):
        self.entries = []
        self.index = [0, 0]

    def current_composition_time(self):
        """Returns composition time of the current sample"""
        if len(self.entries) > 0:
            return self.entries[self.index[1]].offset
        return 0

    def next(self):
        """Iterates sample"""
        if len(self.entries) > 0:
            self.index[0] += 1
            if self.index[0] >= self.entries[self.index[1]].count:
                self.index[0] = 0
                self.index[1] += 1


class SamplesInfo:
    """Composite information of sample atoms"""
    def __init__(self):
        self.stco = SamplesStcoInfo([])
        self.stsz = SamplesStszInfo([])
        self.stts = SamplesSttsInfo([])
        self.ctts = SamplesCttsInfo()
        self.stsc = SamplesStscInfo([])
        self.offset = 0
        self.size = 0

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
        ret = trun.Frame()
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
    def __init__(self, filename):
        self.boxes = []
        self.samples_info = {}
        self.timescale = {}
        self.track_id = 1
        self.video_stream_type = stsd.VideoCodecType.UNKNOWN
        self.file = open(filename, "rb")
        try:
            while True:
                self.boxes.append(self._get_next_box(0))
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

    def _get_next_box(self, depth):
        """Reads a box from file"""
        box = Box(file=self.file, depth=depth)
        if not box.container():
            self.file.seek(box.position)
            if box.type == 'ftyp':
                box = ftyp.Box(file=self.file, depth=depth)
            elif box.type == 'mvhd':
                box = mvhd.Box(file=self.file, depth=depth)
            elif box.type == 'tkhd':
                box = tkhd.Box(file=self.file, depth=depth)
                self.track_id = box.track_id
                self.samples_info[self.track_id] = SamplesInfo()
            elif box.type == 'mdhd':
                box = mdhd.Box(file=self.file, depth=depth)
                self.timescale[self.track_id] = box.timescale
            elif box.type == 'hdlr':
                box = hdlr.Box(file=self.file, depth=depth)
                self.hdlr = box.handler_type
            elif box.type == 'vmhd':
                box = vmhd.Box(file=self.file, depth=depth)
            elif box.type == 'smhd':
                box = smhd.Box(file=self.file, depth=depth)
            elif box.type == 'dref':
                box = dref.Box(file=self.file, depth=depth)
            elif box.type == 'stts':
                box = stts.Box(file=self.file, depth=depth)
                self.samples_info[self.track_id].fill_decoding_time_info(box.entries)
            elif box.type == 'ctts':
                box = ctts.Box(file=self.file, depth=depth)
                self.samples_info[self.track_id].fill_composition_time_info(box.entries)
            elif box.type == 'stsd':
                box = stsd.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                if self.hdlr == 'vide':
                    self.video_stream_type = box.video_stream_type
            elif box.type == 'stsz':
                box = stsz.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                if box.sample_size == 0:
                    self.samples_info[self.track_id].fill_sample_sizes_info(box.entries)
                else:
                    self.samples_info[self.track_id].fill_sample_sizes_info([box.sample_size])
            elif box.type == 'stsc':
                box = stsc.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                self.samples_info[self.track_id].fill_sample_chunk_info(box.entries)
            elif box.type == 'stco':
                box = stco.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                self.samples_info[self.track_id].fill_chunk_offset_info(box.entries)
            elif box.type == 'co64':
                box = co64.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                self.samples_info[self.track_id].fill_chunk_offset_info(box.entries)
            elif box.type == 'mfhd':
                box = mfhd.Box(file=self.file, depth=depth)
            elif box.type == 'tfhd':
                box = tfhd.Box(file=self.file, depth=depth)
            elif box.type == 'trun':
                box = trun.Box(file=self.file, depth=depth)
            self.file.seek(box.position + box.size)
        else:
            box_size = box.size - (self.file.tell() - box.position)
            while box_size > 0:
                next_box = self._get_next_box(box.indent + 1)
                box_size -= next_box.size
                box.add_inner_box(next_box)
        return box
