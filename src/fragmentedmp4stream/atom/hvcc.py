from .atom import Box

class ConfigSet:
    def __init__(self, f):
        self.type = f.read(1)[0]
        self.count = int.from_bytes(f.read(2), 'big')
        self.nalus = []
        for c in range(self.count):
            len = int.from_bytes(f.read(2), 'big')
            self.nalus.append(f.read(len))
    def __repr__(self):
        ret = ""
        if self.type == 32:
            ret += "VPS:"
        elif self.type == 33:
            ret += "SPS:"
        elif self.type == 34:
            ret += "PPS:"
        else:
            ret += str(self.type) + ":"
        ret += '['
        for nalu in self.nalus:
            ret += '[ '
            for c in nalu:
                ret += '{:x} '.format(c)
            ret +=']'
        ret +=']\n'
        return ret;
    def encode(self):
        ret  = self.type.to_bytes(1, byteorder='big')
        ret += self.count.to_bytes(2, byteorder='big')
        for nalu in self.nalus:
            ret += len(nalu).to_bytes(2, byteorder='big')
            ret += nalu
        return ret

class Box(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configSets = []
        f = kwargs.get("file", None)
        if f != None:
            self._readfile(f)

    def __repr__(self):
        ret = super().__repr__() + " genconfig:"
        ret += '[ '
        for c in self.general_config:
            ret += '{:x} '.format(c)
        ret +=']'
        ret += " minSpacialSegmentation:" + hex(self.min_spacial_segmentation) + \
               " parallelism:" + hex(self.parallelism) + \
               " chromaFormatIdc:" + hex(self.chroma_format_idc & 3) + \
               " bitDepthLuma:" + str((self.bit_depth_luma & 7)+8 ) + \
               " bitDepthChroma:" + str((self.bit_depth_chroma & 7)+8 ) + \
               " framerate:" + str(self.framerate) + "\n"
        for cset in self.configSets:
            for i in range(self._depth * 2):
                ret += " "
            ret += str(cset)
        return ret
    def _readfile(self, f):
        self._readsome(f, 1)
        self.general_config = self._readsome(f, 12);
        self.min_spacial_segmentation = int.from_bytes(self._readsome(f, 2), 'big')
        self.parallelism = self._readsome(f, 1)[0]
        self.chroma_format_idc = self._readsome(f, 1)[0]
        self.bit_depth_luma = self._readsome(f, 1)[0]
        self.bit_depth_chroma = self._readsome(f, 1)[0]
        self.framerate = int.from_bytes(self._readsome(f, 2), 'big')
        self.max_sub_layers = self._readsome(f, 1)[0]
        number_of_nalus = self._readsome(f, 1)[0]
        for i in range(number_of_nalus):
            self.configSets.append(ConfigSet(f))
    def encode(self):
        ret = super().encode() + (1).to_bytes(1, byteorder="big") + \
                                 self.general_config + \
                                 self.min_spacial_segmentation.to_bytes(2, byteorder="big") + \
                                 self.parallelism.to_bytes(1, byteorder="big") + \
                                 self.chroma_format_idc.to_bytes(1, byteorder="big") + \
                                 self.bit_depth_luma.to_bytes(1, byteorder="big") + \
                                 self.bit_depth_chroma.to_bytes(1, byteorder="big") + \
                                 self.framerate.to_bytes(2, byteorder="big") + \
                                 self.max_sub_layers.to_bytes(1, byteorder="big") + \
                                 len(self.configSets).to_bytes(1, byteorder="big")
        for cset in self.configSets:
            ret += cset.encode()
        return ret