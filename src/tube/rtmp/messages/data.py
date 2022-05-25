"""The client or the server sends this message to send Metadata or any
    user data to the peer. Metadata includes details about the
    data(audio, video etc.) like creation time, duration, theme and so
    on. These messages have been assigned message type value of 18 for
    AMF0 and message type value of 15 for AMF3.
"""
from __future__ import annotations
import struct
from collections import namedtuple
from enum import IntEnum
from typing import List, Union
from .amf0 import Type as Amf0


class DataMessageException(Exception):
    pass


class Data:
    amf0_type_id = 18
    audio_type_id = 8
    video_type_id = 9

    @staticmethod
    def make(data: bytes) -> Union[Data, None]:
        type_: Amf0 = Amf0.make(data)
        if type_.value == '@setDataFrame':
            data_: bytes = data[len(type_):]
            type_ = Amf0.make(data_)
            return {
                'onMetaData': Metadata,
            }.get(type_.value, lambda d: None)(data_)
        return None

    def __init__(self, data: bytes) -> None:
        field: Amf0 = Amf0.make(data)
        self._type = field.value
        self._size = len(field)


class Metadata(Data):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        if self._type != 'onMetaData':
            raise DataMessageException(f'invalid type: {self._type}. onMetadata expected')
        self.object: Amf0 = Amf0.make(data[self._size:])

    def __repr__(self):
        return f'{self.__class__.__name__}(object={self.object})'


VideoCodecId: IntEnum = IntEnum('VideoCodecId', ('Jpeg',
                                                 'Sorenson',
                                                 'Screen',
                                                 'VP6',
                                                 'VP6alpha',
                                                 'Screen2',
                                                 'AVC',
                                                 )
                                )
PacketType: IntEnum = IntEnum('PacketType', ('SequenceHeader',
                                             'Payload',
                                            ),
                              start=0
                              )
VideoTag: namedtuple = namedtuple('VideoTag', 'frame_type codec_id')
AvcPacket: namedtuple = namedtuple('AvcPacket', 'type composition_time')


class AVCDecoderConfigurationRecord:
    def __init__(self, data: bytes) -> None:
        self.version,\
            self.profile_indication,\
            self.profile_compatibility,\
            self.level_indication,\
            self.length_size,\
            number_of_sps = struct.unpack('=BBBBBB', data[:6])
        self.length_size = self.length_size & 3 + 1
        self.sps: List[bytes] = [bytes() for _ in range(number_of_sps & 0x1f)]
        off: int = 6 + self._set_parameters(self.sps, data[6:])
        self.pps: List[bytes] = [bytes() for _ in range(int(data[off]))]
        self._set_parameters(self.pps, data[off + 1:])

    def __repr__(self):
        return f'{self.__class__.__name__}(version={self.version} ' \
               f'profile={hex(self.profile_indication)} {hex(self.profile_compatibility)} ' \
               f'level={hex(self.level_indication)} length_size={self.length_size} ' \
               f'sps=[{"".join("[" + " ".join(hex(int(x)) for x in ps) + "]" for ps in self.sps)}] ' \
               f'pps=[{"".join("[" + " ".join(hex(int(x)) for x in ps) + "]" for ps in self.pps)}]'

    @staticmethod
    def _set_parameters(param_set: List[bytes], data: bytes) -> int:
        off: int = 0
        for i, _ in enumerate(param_set):
            sz = struct.unpack('>H', data[off:off + 2])[0]
            off += 2
            param_set[i] = data[off:off + sz]
            off += sz
        return off


class VideoData:
    configuration: AVCDecoderConfigurationRecord = None

    def __init__(self, data: bytes, callback=lambda v, d: None) -> None:
        if len(data) < 9:
            raise DataMessageException(f'message too short: {len(data)}')
        off: int = 0
        self._tag: VideoTag = VideoTag(data[off] >> 4, data[off] & 0x0f)
        if self._tag.codec_id == VideoCodecId.AVC:
            self._avc_packet = AvcPacket(data[off+1], int.from_bytes(data[off+2:off+5], 'big'))
            off += 5
        else:
            raise DataMessageException(f'type {self._tag.codec_id} not implemented')
        if self._avc_packet.type == PacketType.SequenceHeader:
            self._on_sequence_header(data[off:], callback)
        elif self._avc_packet.type == PacketType.Payload:
            if not self.__class__.configuration:
                raise DataMessageException('AVCDecoderConfigurationRecord has not been received')
            self._on_nalu(data[off:], callback)

    @property
    def type(self) -> PacketType:
        return self._avc_packet.type

    def __repr__(self):
        return f'{self.__class__.__name__}(tag={self._tag} packet={self._avc_packet})'

    def _on_sequence_header(self, data: bytes, callback) -> None:
        self.__class__.configuration = AVCDecoderConfigurationRecord(data)
        callback(self._avc_packet.type, data)

    def _on_nalu(self, data: bytes, callback):
        off: int = 0
        while off < len(data):
            sz: int = {
                1: struct.unpack('B', data[off:off + 1])[0],
                2: struct.unpack('>H', data[off:off + 2])[0],
                4: struct.unpack('>I', data[off:off + 4])[0],
            }.get(self.__class__.configuration.length_size)
            off += self.__class__.configuration.length_size
            callback(self._avc_packet.type, data[off:off + sz])
            off += sz


SoundFormat: IntEnum = IntEnum('SoundFormat', ('LinearPCM_endian',
                                               'ADPCM',
                                               'MP3',
                                               'LinearPCM_le',
                                               'Nellymoser_16',
                                               'Nellymoser_8',
                                               'Nellymoser',
                                               'A_law',
                                               'Mu_law',
                                               'Reserved',
                                               'AAC',
                                               'Speex',
                                               ),
                               start=0
                               )
SoundRate: IntEnum = IntEnum('SoundRate', ('5_5kHz',
                                           '11kHz',
                                           '22kHz',
                                           '44kHz',
                                           ),
                             start=0
                             )
SoundSize: IntEnum = IntEnum('SoundSize', ('snd8Bit',
                                           'snd16Bit',
                                           ),
                             start=0
                             )
SoundType: IntEnum = IntEnum('SoundType', ('sndMono',
                                           'sndStereo',
                                           ),
                             start=0
                             )
AudioTag: namedtuple = namedtuple('AudioTag', 'format rate size type')


class AudioData:
    def __init__(self, data: bytes, callback) -> None:
        self._tag: AudioTag = AudioTag(data[0] >> 4, (data[0] >> 2) & 3, (data[0] >> 1) & 1, data[0] & 1)
        self._packet_type: PacketType = data[1]
        print(f'{self._tag} : {self._packet_type}')
        callback(self._packet_type, data[2:])

    def __repr__(self):
        return f'{self.__class__.__name__}(tag={self._tag})'
