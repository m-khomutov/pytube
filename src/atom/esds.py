from .atom import FullBox


class Descriptor:
    def __init__(self, tag, file):
        self.tag = tag
        self.etag = file.read(1)
        if int.from_bytes(self.etag, "big") == 0x80:
            self.etag += file.read(2)
            self.length = file.read(1)[0]
        else:
            self.length = self.etag[0]
            self.etag = bytearray()
    def encode(self):
        ret = self.tag.to_bytes(1, byteorder='big')
        if len(self.etag) > 0:
            ret += self.etag
        ret += self.length.to_bytes(1, byteorder='big')
        return ret

class ESDescriptor(Descriptor):
    def __init__(self, file):
        super().__init__(3, file)
        self.esId = int.from_bytes(file.read(2), 'big')
        self.streamPrio = file.read(1)[0]
    def __repr__(self):
        return ' esId:' + str(self.esId) + ' prio:' + str(self.streamPrio)
    def encode(self):
        return super().encode() + self.esId.to_bytes(2, byteorder='big') + \
                                  self.streamPrio.to_bytes(1, byteorder='big')

class ConfigDescriptor(Descriptor):
    def __init__(self, file):
        super().__init__(4, file)
        self._objdict = {
            1: 'system v1',
            2: 'system v2',
            32: 'MPEG-4 video',
            33: 'MPEG-4 AVC SPS',
            34: 'MPEG-4 AVC PPS',
            64: 'MPEG-4 audio',
            96: 'MPEG-2 simple video',
            97: 'MPEG-2 main video',
            98: 'MPEG-2 SNR video',
            99: 'MPEG-2 spatial video',
            100: 'MPEG-2 high video',
            101: 'MPEG-2 4:2:2 video',
            102: 'MPEG-4 ADTS main',
            103: 'MPEG-4 ADTS Low Complexity',
            104: 'MPEG-4 ADTS Scalable Sampling Rate',
            105: 'MPEG-2 ADTS',
            106: 'MPEG-1 video',
            107: 'MPEG-1 ADTS',
            108: 'JPEG video',
            192: 'private audio',
            208: 'private video',
            224: '16-bit PCM LE audio',
            225: 'vorbis audio',
            226: 'dolby v3 (AC3) audio',
            227: 'alaw audio',
            228: 'mulaw audio',
            229: 'G723 ADPCM audio',
            230: '16-bit PCM Big Endian audio',
            240: 'YCbCr 4:2:0 (YV12) video',
            241: 'H264 video',
            242: 'H263 video',
            243: 'H261 video'
        }
        self._streamdict = {
            1: 'object descript.',
            2: 'clock ref.',
            3: 'scene descript.',
            4: 'visual',
            5: 'audio',
            6: 'MPEG-7',
            7: 'IPMP',
            8: 'OCI',
            9: 'MPEG Java',
            32: 'user private'
        }
        self.object_type_id = file.read(1)[0]
        try:
            self._objtype = self._objdict[self.object_type_id]
        except KeyError as e:
            self._objtype = str(self.object_type_id)
        self.stream_type = file.read(1)[0]
        try:
            self._streamtype = self._streamdict[self.stream_type >> 2]
        except KeyError as e:
            self._streamtype = str(self.stream_type)
        self.buffersize = int.from_bytes(file.read(3),'big')
        self.maxbitrare = int.from_bytes(file.read(4) ,'big')
        self.avbitrare = int.from_bytes(file.read(4) ,'big')
    def __repr__(self):
        return " obj:'" + self._objtype + "' stream:'" + self._streamtype + "'" + " bufsz:" + str(self.buffersize) + \
               " maxbr:" + str(self.maxbitrare) + " avbr:" + str(self.avbitrare)
    def encode(self):
        return super().encode() + self.object_type_id.to_bytes(1, byteorder='big') + \
                                  self.stream_type.to_bytes(1, byteorder='big') + \
                                  self.buffersize.to_bytes(3, byteorder='big') + \
                                  self.maxbitrare.to_bytes(4, byteorder='big') + \
                                  self.avbitrare.to_bytes(4, byteorder='big')

class DecoderSpecificDescriptor(Descriptor):
    def __init__(self, file):
        super().__init__(5, file)
        self.header_start_codes = file.read(self.length)
    def __repr__(self):
        ret = " startcodes:[ "
        for c in self.header_start_codes:
            ret += '{:x} '.format(c)
        ret += ']'
        return ret
    def encode(self):
        return super().encode() + self.header_start_codes

class SLConfigDescriptor(Descriptor):
    def __init__(self, file):
        super().__init__(6, file)
        self.value = file.read(1)[0]
    def __repr__(self):
        return " sl:" + str(self.value)
    def encode(self):
        return super().encode() + self.value.to_bytes(1, byteorder='big')

class Box(FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.descriptors = []
        f = kwargs.get("file", None)
        if f != None:
            self._readfile(f)

    def __repr__(self):
        ret = super().__repr__()
        for d in self.descriptors:
            ret += str(d)
        return ret

    def _readfile(self, f):
        left = self.size - (f.tell() - self.position)
        while left > 0:
            tag = f.read(1)[0]
            if tag == 3:
                self.descriptors.append(ESDescriptor(f))
                left = self.size - (f.tell() - self.position)
            elif tag == 4:
                self.descriptors.append(ConfigDescriptor(f))
            elif tag == 5:
                self.descriptors.append(DecoderSpecificDescriptor(f))
            elif tag == 6:
                self.descriptors.append(SLConfigDescriptor(f))
            else:
                left = 0

    def encode(self):
        ret = super().encode()
        for d in self.descriptors:
            ret += d.encode()
        return ret