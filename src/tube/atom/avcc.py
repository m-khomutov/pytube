"""The decoder configuration record that this atom contains
   is defined in the MPEG-4 specification ISO/IEC FDIS 14496-15
"""
import base64
from . import atom


def atom_type():
    """Returns this atom type"""
    return 'avcC'


class Box(atom.Box):
    """An MPEG-4 decoder configuration atom"""
    def __init__(self, *args, **kwargs):
        self.initial_parameters = 0
        self._unit_len = 0
        self.sps = []
        self.pps = []
        self.appendix = b''
        self._sprop_parameter_sets = ''
        super().__init__(*args, **kwargs)

    def __repr__(self):
        ret = super().__repr__() + " version:" + str(self.initial_parameters[0]) + \
                                   " profile:" + hex(self.initial_parameters[1]) + \
                                   " compatibility:" + hex(self.initial_parameters[2]) + \
                                   " level:" + hex(self.initial_parameters[3]) + \
                                   " unit_len:" + str(self._unit_len+1) + "\n"
        ret += ' ' * self._depth * 2
        ret += 'sps=[' + ''.join(
            '[ ' + ' '.join(['{:x}'.format(c) for c in sps]) + ']' for sps in self.sps
        )
        ret += ']\n' + ' ' * self._depth * 2
        ret += 'pps=[' + ''.join(
            '[ ' + ' '.join(['{:x}'.format(c) for c in pps]) + ']' for pps in self.pps
        )
        return ret + ']'

    def init_from_file(self, file):
        self.initial_parameters = file.read(4)
        self._unit_len = self._read_some(file, 1)[0] & 3  # 1 byte = 0; 2 bytes = 1; 4 bytes = 3
        count = self._read_some(file, 1)[0] & 0x1f
        actual_size = 14
        self.sps = list(map(lambda x: self._read_parameter_set(file), range(count)))
        for sps in self.sps:
            actual_size += len(sps) + 2
        base64_sps = base64.b64encode(self.sps[-1]).decode('ascii')
        count = self._read_some(file, 1)[0]
        actual_size += 1
        self.pps = list(map(lambda x: self._read_parameter_set(file), range(count)))
        for pps in self.pps:
            actual_size += len(pps) + 2
        base64_pps = base64.b64encode(self.pps[-1]).decode('ascii')
        self._sprop_parameter_sets = base64_sps + ',' + base64_pps
        if actual_size < self.size:
            self.appendix = self._read_some(file, self.size - actual_size)

    def init_from_args(self, **kwargs):
        self.type = atom_type()
        self.initial_parameters = kwargs.get('initial', b'')
        self._unit_len = kwargs.get('u_length', 4) - 1
        self.sps = kwargs.get('sps', b'')
        self.pps = kwargs.get('pps', b'')
        self.size = 15
        for s in self.sps:
            self.size += 2 + len(s)
        for s in self.pps:
            self.size += 2 + len(s)

    def _read_parameter_set(self, file):
        """reads one parameter set from file"""
        length = int.from_bytes(self._read_some(file, 2), 'big')
        return self._read_some(file, length)

    @property
    def profile_level_id(self):
        """Returns parameter, used in SDP"""
        ret = ''
        for i in range(1, 4):
            ret += '{:02x}'.format(self.initial_parameters[i])
        return ret

    @property
    def sprop_parameter_sets(self):
        """Returns SPS + PPS in base64"""
        return self._sprop_parameter_sets

    @property
    def unit_length(self):
        """Returns length of avcC size field"""
        return self._unit_len + 1

    def to_bytes(self):
        rc = [
            super().to_bytes(),
            self.initial_parameters,
            (0xfc | self._unit_len).to_bytes(1, byteorder="big"),
            (0xe0 | len(self.sps)).to_bytes(1, byteorder="big")
        ]
        for sps in self.sps:
            rc.append(len(sps).to_bytes(2, byteorder="big"))
            rc.append(sps)
        rc.append(len(self.pps).to_bytes(len(self.pps), byteorder="big"))
        for pps in self.pps:
            rc.append(len(pps).to_bytes(2, byteorder="big"))
            rc.append(pps)
        rc.append(self.appendix)
        return b''.join(rc)
