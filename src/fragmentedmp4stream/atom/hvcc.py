"""The decoder configuration record that this atom contains
   is defined in the MPEG-4 specification ISO/IEC FDIS 14496-15
"""
from enum import IntEnum
from functools import reduce
from bitstring import ConstBitStream
from . import atom


class NetworkUnitType(IntEnum):
    """The Network Abstraction Layer types enumeration"""
    TRAIL_N = 0
    TRAIL_R = 1
    TSA_N = 2
    TSA_R = 3
    STSA_N = 4
    STSA_R = 5
    RADL_N = 6
    RADL_R = 7
    RASL_N = 8
    RASL_R = 9
    RSV_VCL_N10 = 10
    RSV_VCL_R11 = 11
    RSV_VCL_N12 = 12
    RSV_VCL_R13 = 13
    RSV_VCL_N14 = 14
    RSV_VCL_R15 = 15
    BLA_W_LP = 16
    BLA_W_RADL = 17
    BLA_N_LP = 18
    IDR_W_RADL = 19
    IDR_N_LP = 20
    CRA_NUT = 21
    RSV_IRAP_VCL22 = 22
    RSV_IRAP_VCL23 = 23
    VPS_NUT = 32
    SPS_NUT = 33
    PPS_NUT = 34
    AUD_NUT = 35
    EOS_NUT = 36
    EOB_NUT = 37
    FD_NUT = 38
    PREFIX_SEI_NUT = 39
    SUFFIX_SEI_NUT = 40


class NetworkUnitHeader:
    """The Network Abstraction Layer header"""
    def __init__(self, frame):
        if len(frame) == 2:
            bits = ConstBitStream(frame)
            self.forbidden_zero_bit = bits.read('uint:1')
            self.nal_unit_type = bits.read('uint:6')
            self.nuh_layer_id = bits.read('uint:6')
            self.nuh_temporal_id_plus1 = bits.read('uint:3')
        else:
            self.nal_unit_type = frame[0]

    def __repr__(self):
        if self.nal_unit_type == NetworkUnitType.VPS_NUT:
            return "VPS"
        if self.nal_unit_type == NetworkUnitType.SPS_NUT:
            return "SPS"
        if self.nal_unit_type == NetworkUnitType.PPS_NUT:
            return "PPS"
        return str(self.nal_unit_type)

    def keyframe(self):
        """Verifies if this is a keyframe"""
        if self.nal_unit_type >= NetworkUnitType.BLA_W_LP:
            return self.nal_unit_type <= NetworkUnitType.RSV_IRAP_VCL23
        return False

    def to_bytes(self):
        """Returns header as bytestream, ready to be sent to socket"""
        return self.nal_unit_type.to_bytes(1, byteorder='big')


class ConfigSet:
    """Abstraction of a set of configuration"""
    def __init__(self, file):
        self.type = NetworkUnitHeader(file.read(1))
        count = int.from_bytes(file.read(2), 'big')
        self.sets = list(map(lambda x: self.read_configure_set(file), range(count)))

    @staticmethod
    def read_configure_set(file):
        """reads a set of configuration  from file"""
        length = int.from_bytes(file.read(2), 'big')
        return file.read(length)

    @staticmethod
    def config_to_bytes(config):
        """Returns a config set as bytestream, ready to be sent to socket"""
        return len(config).to_bytes(2, byteorder='big') + config

    def __repr__(self):
        ret = str(self.type)
        ret += ''.join(
            '[' + ' '.join('{:x}'.format(k) for k in s) + ']' for s in self.sets
        )
        return ret

    def to_bytes(self):
        """Returns configuration sets as bytestream, ready to be sent to socket"""
        ret = self.type.to_bytes()
        ret += len(self.sets).to_bytes(2, byteorder='big')
        ret += reduce(lambda a, b: a + b, (self.config_to_bytes(x) for x in self.sets))
        return ret


class Box(atom.Box):
    """An MPEG-4 decoder configuration atom"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_sets = []
        file = kwargs.get("file", None)
        if file is not None:
            self._readfile(file)

    def __repr__(self):
        ret = super().__repr__()
        ret += " config:["+''.join('{:x}'.format(k) for k in self.general_config)+"]" + \
               " minSpacialSegmentation:" + hex(self.min_spacial_segmentation) + \
               " parallelism:" + hex(self.chroma[0]) + \
               " chromaFormatIdc:" + hex(self.chroma[1] & 3) + \
               " bitDepthLuma:" + str((self.bit_depth[0] & 7)+8) + \
               " bitDepthChroma:" + str((self.bit_depth[1] & 7)+8) + \
               " frameRate:" + str(self.frame_rate) + "\n" + \
               "\n".join(' '*(self._depth*2) + str(k) for k in self.config_sets)
        return ret

    def _readfile(self, file):
        self._readsome(file, 1)
        self.general_config = self._readsome(file, 12)
        self.min_spacial_segmentation = int.from_bytes(self._readsome(file, 2), 'big')
        self.chroma = self._readsome(file, 2)
        self.bit_depth = self._readsome(file, 2)
        self.frame_rate = int.from_bytes(self._readsome(file, 2), 'big')
        self.max_sub_layers = self._readsome(file, 1)[0]
        number_of_sets = self._readsome(file, 1)[0]
        self.config_sets = list(map(lambda x: ConfigSet(file), range(number_of_sets)))

    def to_bytes(self):
        ret = super().to_bytes() + (1).to_bytes(1, byteorder="big") + \
                                 self.general_config + \
                                 self.min_spacial_segmentation.to_bytes(2, byteorder="big") + \
                                 self.chroma + \
                                 self.bit_depth + \
                                 self.frame_rate.to_bytes(2, byteorder="big") + \
                                 self.max_sub_layers.to_bytes(1, byteorder="big") + \
                                 len(self.config_sets).to_bytes(1, byteorder="big")
        ret += reduce(lambda a, b: a + b, map(lambda x: x.to_bytes(), self.config_sets))
        return ret
