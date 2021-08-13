"""The decoder configuration record that this atom contains
   is defined in the MPEG-4 specification ISO/IEC FDIS 14496-15
"""
from . import atom


class Box(atom.Box):
    """An MPEG-4 decoder configuration atom"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readfile(file)

    def __repr__(self):
        ret = super().__repr__() + " version:" + str(self.initial_parameters[0]) + \
                                   " profile:" + hex(self.initial_parameters[1]) + \
                                   " compatibility:" + hex(self.initial_parameters[2]) + \
                                   " level:" + hex(self.initial_parameters[3]) + \
                                   " unit_len:" + str(self.unit_len+1) + "\n"
        ret += ' ' * self._depth * 2
        ret += 'sps=[' + ''.join(
            '[ ' + ' '.join(['{:x}'.format(c) for c in sps]) + ']' for sps in self.sps
        )
        ret += ']\n' + ' ' * self._depth * 2
        ret += 'pps=[' + ''.join(
            '[ ' + ' '.join(['{:x}'.format(c) for c in pps]) + ']' for pps in self.pps
        )
        return ret + ']'

    def _readfile(self, file):
        self.initial_parameters = file.read(4)
        self.unit_len = self._readsome(file, 1)[0] & 3  # 1 byte = 0; 2 bytes = 1; 4 bytes = 3
        count = self._readsome(file, 1)[0] & 0x1f
        actual_size = 14
        self.sps = list(map(lambda x: self._read_parameter_set(file), range(count)))
        for sps in self.sps:
            actual_size += len(sps) + 2
        count = self._readsome(file, 1)[0]
        actual_size += 1
        self.pps = list(map(lambda x: self._read_parameter_set(file), range(count)))
        for pps in self.pps:
            actual_size += len(pps) + 2
        self.appendix = b'' if actual_size >= self.size \
            else self._readsome(file, self.size - actual_size)

    def _read_parameter_set(self, file):
        """reads one parameter set from file"""
        length = int.from_bytes(self._readsome(file, 2), 'big')
        return self._readsome(file, length)

    def to_bytes(self):
        ret = super().to_bytes() + self.initial_parameters
        unit_length = 0xfc | self.unit_len
        ret += unit_length.to_bytes(1, byteorder="big")
        unit_length = 0xe0 | len(self.sps)
        ret += unit_length.to_bytes(1, byteorder="big")
        for sps in self.sps:
            ret += len(sps).to_bytes(2, byteorder="big")
            ret += sps
        ret += len(self.pps).to_bytes(1, byteorder="big")
        for pps in self.pps:
            ret += len(pps).to_bytes(2, byteorder="big")
            ret += pps
        return ret + self.appendix
