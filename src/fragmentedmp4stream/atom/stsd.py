from .atom import Box, FullBox
from . import esds, avcc, hvcc, pasp, fiel
from enum import IntEnum


class VideoStreamType(IntEnum):
    Unknown = 0
    AVC = 1
    HEVC = 2

class SampleEntry(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readsome(f, 6)
            self.data_reference_index = int.from_bytes(self._readsome(f, 2), "big")
    def __repr__(self):
        return super().__repr__() + " dataRefIdx:" + str(self.data_reference_index)
    def encode(self):
        return super().encode() + bytearray(6) + self.data_reference_index.to_bytes(2, byteorder='big')

class VisualSampleEntry(SampleEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readsome(f, 16)
            self.width = int.from_bytes(self._readsome(f, 2), "big")
            self.height = int.from_bytes(self._readsome(f, 2), "big")
            self.horizresolution = int.from_bytes(self._readsome(f, 4), "big")
            self.vertresolution = int.from_bytes(self._readsome(f, 4), "big")
            self._readsome(f, 4)
            self.frame_count = int.from_bytes(self._readsome(f, 2), "big")
            self.compressorname = self._readsome(f, 32).decode("utf-8")
            self.colordepth = int.from_bytes(self._readsome(f, 2), "big")
            self._readsome(f, 2)
            left = self.size - (f.tell()-self.position)
            self.avcc = None
            self.hvcc = None
            self.pasp = None
            self.fiel = None
            while left > 0:
                box = Box(file=f, depth=self._depth + 1)
                if box.type == 'avcC':
                    f.seek(box.position)
                    self.avcc = avcc.Box(file=f, depth=self._depth + 1)
                    left -= self.avcc.size
                elif box.type == 'hvcC':
                    f.seek(box.position)
                    self.hvcc = hvcc.Box(file=f, depth=self._depth + 1)
                    left -= self.hvcc.size
                elif box.type == 'pasp':
                    f.seek(box.position)
                    self.pasp = pasp.Box(file=f, depth=self._depth + 1)
                    left -= self.pasp.size
                elif box.type == 'fiel':
                    f.seek(box.position)
                    self.fiel = fiel.Box(file=f, depth=self._depth + 1)
                    left -= self.fiel.size
                else:
                    f.seek(box.position+box.size)
                    left -= box.size
                    self.size -= box.size
    def __repr__(self):
        ret = super().__repr__() + " width:" + str(self.width) + \
                                   " height:" + str(self.height) + \
                                   " hresolution:" + hex(self.horizresolution) + \
                                   " vresolution:" + hex(self.vertresolution) + \
                                   " framecount:" + str(self.frame_count) + \
                                   " compressorname:'" + self.compressorname + "'"\
                                   " depth:" + str(self.colordepth)
        if self.avcc != None:
            ret += "\n" + self.avcc.__repr__()
        if self.hvcc != None:
            ret += "\n" + self.hvcc.__repr__()
        if self.pasp != None:
            ret += "\n" + self.pasp.__repr__()
        if self.fiel != None:
            ret += "\n" + self.fiel.__repr__()
        return ret
    def encode(self):
        ret = super().encode()
        ret += bytearray(16)
        ret += self.width.to_bytes(2, byteorder='big')
        ret += self.height.to_bytes(2, byteorder='big')
        ret += self.horizresolution.to_bytes(4, byteorder='big')
        ret += self.vertresolution.to_bytes(4, byteorder='big')
        ret += (0).to_bytes(4, byteorder='big')
        ret += self.frame_count.to_bytes(2, byteorder="big")
        ret += str.encode(self.compressorname)
        ret += self.colordepth.to_bytes(2, byteorder='big')
        ret += (0xffff).to_bytes(2, byteorder='big')
        if self.avcc != None:
            ret += self.avcc.encode()
        if self.hvcc != None:
            ret += self.hvcc.encode()
        if self.pasp != None:
            ret += self.pasp.encode()
        if self.fiel != None:
            ret += self.fiel.encode()
        return ret

class AudioSampleEntry(SampleEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readsome(f, 8)
            self.channelcount = int.from_bytes(self._readsome(f, 2), "big")
            self.samplesize = int.from_bytes(self._readsome(f, 2), "big")
            self._readsome(f, 4)
            self.samplerate = int.from_bytes(self._readsome(f, 4), "big")
            left = self.size - (f.tell()-self.position)
            while left > 0:
                box = Box(file=f, depth=self._depth + 1)
                if box.type == 'esds':
                    f.seek(box.position)
                    self.esds = esds.Box(file=f, depth=self._depth + 1)
                    left -= self.esds.size
    def __repr__(self):
        ret = super().__repr__() + " channels:" + str(self.channelcount) + \
                                   " samplesize:" + str(self.samplesize) + \
                                   " samplerate:" + str(self.samplerate>>16);
        if self.esds != None:
            ret += "\n" + self.esds.__repr__()
        return ret
    def encode(self):
        ret = super().encode()
        ret += bytearray(8)
        ret += self.channelcount.to_bytes(2, byteorder='big')
        ret += self.samplesize.to_bytes(2, byteorder='big')
        ret += bytearray(4)
        ret += self.samplerate.to_bytes(4, byteorder='big')
        if self.esds != None:
            ret += self.esds.encode()
        return ret

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        self.entries = []
        self.vstream_type = VideoStreamType.Unknown
        if f != None:
            self._readfile(f, kwargs.get('hdlr', None))
    def __repr__(self):
        ret = super().__repr__()
        for s in self.entries:
            ret += "\n" + s.__repr__()
        return ret
    def normalize(self):
        self.size=16
        for entry in self.entries:
            self.size+=entry.size
    def _readfile(self, f, hdlr):
        count = int.from_bytes(self._readsome(f, 4), "big")
        if hdlr != None:
            for i in range(count):
                if hdlr == 'vide':
                    entry = VisualSampleEntry(file=f,depth=self._depth+1)
                    if entry.avcc != None:
                        self.vstream_type = VideoStreamType.AVC
                    elif entry.hvcc != None:
                        self.vstream_type = VideoStreamType.HEVC
                    self.entries.append(entry)
                elif hdlr == 'soun':
                    self.entries.append(AudioSampleEntry(file=f,depth=self._depth+1))
    def encode(self):
        ret = super().encode()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        for s in self.entries:
            ret += s.encode()
        return ret