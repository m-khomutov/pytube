from . import atom


class Box(atom.Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self._readfile(f)

    def __repr__(self):
        ret = super().__repr__() + " version:" + str(self.version) + \
                                   " profile:" + hex(self.profile) + \
                                   " compat:" + hex(self.cprofiles) + \
                                   " level:" + hex(self.level) + \
                                   " nalulen:" + str(self.nalulen+1) + "\n"
        for i in range(self._depth * 2):
            ret += " "
        ret += 'sps=['
        for sps in self.sps:
            ret += '[ '
            for c in sps:
                ret += '{:x} '.format(c)
            ret +=']'
        ret += ']\n'
        for i in range(self._depth * 2):
            ret += " "
        ret += 'pps=['
        for pps in self.pps:
            ret += '[ '
            for c in pps:
                ret += '{:x} '.format(c)
            ret +=']'
        ret += ']'
        return ret

    def _readfile(self, f):
        self.version = self._readsome(f, 1)[0]
        self.profile = self._readsome(f, 1)[0]
        self.cprofiles = self._readsome(f, 1)[0]
        self.level = self._readsome(f, 1)[0]
        self.nalulen = self._readsome(f, 1)[0] & 3 #1 byte = 0; 2 bytes = 1; 4 bytes = 3
        count = self._readsome(f, 1)[0] & 0x1f
        actual_size=14
        self.sps = []
        for i in range(count):
            len = int.from_bytes(self._readsome(f, 2) ,'big')
            self.sps.append(self._readsome(f, len))
            actual_size+=(len+2)
        count = self._readsome(f, 1)[0]
        actual_size+=1
        self.pps = []
        for i in range(count):
            len = int.from_bytes(self._readsome(f, 2) ,'big')
            self.pps.append(self._readsome(f, len))
            actual_size+=(len+2)
        self.appendix=b''
        if actual_size < self.size:
            self.appendix=self._readsome(f, self.size-actual_size)

    def encode(self):
        ret = super().encode()
        ret += self.version.to_bytes(1, byteorder="big")
        ret += self.profile.to_bytes(1, byteorder="big")
        ret += self.cprofiles.to_bytes(1, byteorder="big")
        ret += self.level.to_bytes(1, byteorder="big")
        b = 0xfc | self.nalulen
        ret += b.to_bytes(1, byteorder="big")
        b = 0xe0 | len(self.sps)
        ret += b.to_bytes(1, byteorder="big")
        for sps in self.sps:
            ret += len(sps).to_bytes(2, byteorder="big")
            ret += sps
        ret += len(self.pps).to_bytes(1, byteorder="big")
        for pps in self.pps:
            ret += len(pps).to_bytes(2, byteorder="big")
            ret += pps
        return ret + self.appendix