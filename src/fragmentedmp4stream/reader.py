from .atom.atom import Box
from .atom import ftyp, stco, stsc, mvhd, tkhd, mdhd, co64, stts, hdlr, ctts, vmhd, trun, stsd, smhd, dref, stsz, mfhd, tfhd


class FragmentationFinished(Exception):
    pass

class SamplesStscInfo:
    def __init__(self, entries):
        self.entries = []
        self.index = [0, 0]
        for i, entry in enumerate(entries):
            if i > 0:
                runsize = entry.first_chunk - entries[i-1].first_chunk
                for chunk in range(runsize):
                    self.entries.append(entries[i-1].samples_per_chunk)
    def iterate_offset(self):
        return self.index[1] >= len(self.entries) or self.index[0] == 0
    def iterate(self):
        if self.index[1] < len(self.entries):
            self.index[0] += 1
            if self.index[0] >= self.entries[self.index[1]]:
                self.index[0] = 0
                self.index[1] += 1

class SamplesStcoInfo:
    def __init__(self, entries):
        self.entries = entries
        self.index = 0
    def info(self):
        return self.entries[self.index]
    def iterate(self):
        if self.index < len(self.entries):
            self.index += 1

class SamplesStszInfo:
    def __init__(self, entries):
        self.entries = entries
        self.index = 0
    def info(self):
        return self.entries[self.index]
    def iterate(self):
        if self.index < len(self.entries):
            self.index += 1
        else:
            raise FragmentationFinished('')

class SamplesSttsInfo:
    def __init__(self, entries):
        self.entries = entries
        self.index = [0, 0]
    def info(self):
        return self.entries[self.index[1]].delta
    def iterate(self):
        self.index[0] += 1
        if self.index[0] >= self.entries[self.index[1]].count:
            self.index[0] = 0
            self.index[1] += 1

class SamplesCttsInfo:
    def __init__(self):
        self.entries = []
        self.index = [0, 0]
    def info(self):
        if len(self.entries) > 0:
            return self.entries[self.index[1]].offset
        return 0
    def iterate(self):
        if len(self.entries) > 0:
            self.index[0] += 1
            if self.index[0] >= self.entries[self.index[1]].count:
                self.index[0] = 0
                self.index[1] += 1

class SamplesInfo:
    def __init__(self):
        self.ctts = SamplesCttsInfo()
        self.stsc = SamplesStscInfo([])
        self.offset = 0
        self.size = 0
    def setStco(self, stco):
        self.stco = SamplesStcoInfo(stco)
    def setStsz(self, stsz):
        self.stsz = SamplesStszInfo(stsz)
    def setStts(self, stts):
        self.stts = SamplesSttsInfo(stts)
    def setCtts(self, ctts):
        self.ctts.entries = ctts
    def setStsc(self, stsc):
        self.stsc = SamplesStscInfo(stsc)
    def sample(self):
        ret = trun.Frame()
        if self.stsc.iterate_offset():
            ret.offset = self.offset = self.stco.info()
        else:
            self.offset += self.size
            ret.offset = self.offset
        ret.size = self.size = self.stsz.info()
        ret.duration = self.stts.info()
        ret.composition_time = self.ctts.info()
        return ret
    def iterate(self):
        self.stsc.iterate()
        if self.stsc.iterate_offset():
            self.stco.iterate()
        self.stsz.iterate()
        self.stts.iterate()
        self.ctts.iterate()

class Reader:
    def __init__(self, fname):
        self.boxes = []
        self.samples_info = {}
        self.timescale = {}
        self.trakID = 1
        self.vstream_type = stsd.VideoCodecType.UNKNOWN
        self.file = open(fname, "rb")
        try:
            while True:
                self.boxes.append(self._readBox(0))
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
    def find(self, type):
        ret = []
        for box in self.boxes:
            rc = box.find_inner_boxes(type)
            if len(rc) > 0:
                for b in rc:
                    ret.append(b)
        return ret
    def nextSample(self, trakid ):
        sample = self.samples_info[trakid].sample()
        self.samples_info[trakid].iterate()
        self.file.seek(sample.offset)
        sample.data = self.file.read(sample.size)
        return sample
    def sample(self, offset, size):
        self.file.seek(offset)
        return self.file.read(size)
    def hasCT(self, trakid):
        return self.samples_info[trakid].ctts != None
    def _readBox(self, depth):
        box = Box(file=self.file, depth=depth)
        if not box.container():
            if box.type == 'ftyp':
                self.file.seek(box.position)
                box = ftyp.Box(file=self.file, depth=depth)
            elif box.type == 'mvhd':
                self.file.seek(box.position)
                box = mvhd.Box(file=self.file, depth=depth)
            elif box.type == 'tkhd':
                self.file.seek(box.position)
                box = tkhd.Box(file=self.file, depth=depth)
                self.trakID = box.track_id
                self.samples_info[self.trakID] = SamplesInfo()
            elif box.type == 'mdhd':
                self.file.seek(box.position)
                box = mdhd.Box(file=self.file, depth=depth)
                self.timescale[self.trakID] = box.timescale
            elif box.type == 'hdlr':
                self.file.seek(box.position)
                box = hdlr.Box(file=self.file, depth=depth)
                self.hdlr = box.handler_type
            elif box.type == 'vmhd':
                self.file.seek(box.position)
                box = vmhd.Box(file=self.file, depth=depth)
            elif box.type == 'smhd':
                self.file.seek(box.position)
                box = smhd.Box(file=self.file, depth=depth)
            elif box.type == 'dref':
                self.file.seek(box.position)
                box = dref.Box(file=self.file, depth=depth)
            elif box.type == 'stts':
                self.file.seek(box.position)
                box = stts.Box(file=self.file, depth=depth)
                self.samples_info[self.trakID].setStts(box.entries)
            elif box.type == 'ctts':
                self.file.seek(box.position)
                box = ctts.Box(file=self.file, depth=depth)
                self.samples_info[self.trakID].setCtts(box.entries)
            elif box.type == 'stsd':
                self.file.seek(box.position)
                box = stsd.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                if self.hdlr == 'vide':
                    self.vstream_type = box.video_stream_type
            elif box.type == 'stsz':
                self.file.seek(box.position)
                box = stsz.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                if box.sample_size == 0:
                    self.samples_info[self.trakID].setStsz(box.entries)
                else:
                    self.samples_info[self.trakID].setStsz([box.sample_size])
            elif box.type == 'stsc':
                self.file.seek(box.position)
                box = stsc.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                self.samples_info[self.trakID].setStsc(box.entries)
            elif box.type == 'stco':
                self.file.seek(box.position)
                box = stco.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                self.samples_info[self.trakID].setStco(box.entries)
            elif box.type == 'co64':
                self.file.seek(box.position)
                box = co64.Box(file=self.file, depth=depth, hdlr=self.hdlr)
                self.samples_info[self.trakID].setStco(box.entries)
            elif box.type == 'mfhd':
                self.file.seek(box.position)
                box = mfhd.Box(file=self.file, depth=depth)
            elif box.type == 'tfhd':
                self.file.seek(box.position)
                box = tfhd.Box(file=self.file, depth=depth)
            elif box.type == 'trun':
                self.file.seek(box.position)
                box = trun.Box(file=self.file, depth=depth)
            self.file.seek(box.position + box.size)
        else:
            boxSize = box.size - (self.file.tell() - box.position)
            while boxSize > 0:
                b = self._readBox(box.indent + 1)
                boxSize -= b.size
                box.add_inner_box(b)
        return box