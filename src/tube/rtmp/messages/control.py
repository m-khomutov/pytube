"""Control messages. These messages contain information needed
   by the RTMP Chunk Stream protocol"""
from enum import IntEnum
from ..chunk import ChunkBasicHeader, ChunkMessageHeader


class ControlMessageException(Exception):
    pass


LimitType: IntEnum = IntEnum('LimitType', ('Hard',
                                           'Soft',
                                           'Dynamic'),
                             start=0
                             )


class ControlStream:
    chunk_id: int = 0
    stream_id: int = 2


class SetChunkSize:
    """Used to notify the peer of a new maximum chunk size"""
    type_id: int = 1

    def __init__(self, chunk_size: int = 128) -> None:
        self._chunk_size: int = chunk_size

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    @chunk_size.setter
    def chunk_size(self, value: int) -> None:
        self._chunk_size = value

    def from_bytes(self, data: bytes) -> None:
        self._chunk_size: int = int.from_bytes(data[:4], 'big') & 0x7fffffff

    def to_bytes(self) -> bytes:
        bh: ChunkBasicHeader = ChunkBasicHeader(ControlStream.chunk_id, ControlStream.stream_id)
        header: ChunkMessageHeader = ChunkMessageHeader()
        header.message_length = 4
        header.message_type_id = SetChunkSize.type_id
        return header.to_bytes(bh) + self._chunk_size.to_bytes(4, byteorder='big')


class AbortMessage:
    """Used to notify the peer if it is waiting for chunks to complete a message,
       then to discard the partially received message over a chunk stream."""
    type_id: int = 2

    def __init__(self, chunk_stream_id: int) -> None:
        self._chunk_stream_id: int = chunk_stream_id

    @property
    def chunk_stream_id(self) -> int:
        return self._chunk_stream_id

    @chunk_stream_id.setter
    def chunk_stream_id(self, value: int) -> None:
        self._chunk_stream_id = value

    def from_bytes(self, data: bytes) -> None:
        self._chunk_stream_id: int = int.from_bytes(data[:4], 'big')

    def to_bytes(self) -> bytes:
        bh: ChunkBasicHeader = ChunkBasicHeader(ControlStream.chunk_id, ControlStream.stream_id)
        header: ChunkMessageHeader = ChunkMessageHeader()
        header.message_length = 4
        header.message_type_id = AbortMessage.type_id
        return header.to_bytes(bh) + self._chunk_stream_id.to_bytes(4, byteorder='big')


class Acknowledgement:
    """Is sent to the peer after receiving bytes equal to the window size"""
    type_id = 3

    def __init__(self, sequence_number: int) -> None:
        self._sequence_number: int = sequence_number

    @property
    def sequence_number(self) -> int:
        return self._sequence_number

    @sequence_number.setter
    def sequence_number(self, value: int) -> None:
        self._sequence_number = value

    def from_bytes(self, data: bytes) -> None:
        self._sequence_number: int = int.from_bytes(data[:4], 'big')

    def to_bytes(self) -> bytes:
        bh: ChunkBasicHeader = ChunkBasicHeader(ControlStream.chunk_id, ControlStream.stream_id)
        header: ChunkMessageHeader = ChunkMessageHeader()
        header.message_length = 4
        header.message_type_id = Acknowledgement.type_id
        return header.to_bytes(bh) + self._sequence_number.to_bytes(4, byteorder='big')


class WindowAcknowledgementSize:
    """Is sent to inform the peer of the window size to use between sending acknowledgments"""
    type_id = 5

    def __init__(self, window_size: int = 2500000) -> None:
        self._window_size: int = window_size

    @property
    def window_size(self) -> int:
        return self._window_size

    @window_size.setter
    def window_size(self, value: int):
        self._window_size = value

    def from_bytes(self, data: bytes) -> None:
        self._window_size: int = int.from_bytes(data[:4], 'big')

    def to_bytes(self) -> bytes:
        bh: ChunkBasicHeader = ChunkBasicHeader(ControlStream.chunk_id, ControlStream.stream_id)
        header: ChunkMessageHeader = ChunkMessageHeader()
        header.message_length = 4
        header.message_type_id = WindowAcknowledgementSize.type_id
        return header.to_bytes(bh) + self._window_size.to_bytes(4, byteorder='big')


class SetPeerBandwidth:
    """Is sent to limit the output bandwidth of its peer"""
    type_id = 6

    def __init__(self, window_size: int = 2500000, limit_type: LimitType = LimitType.Dynamic) -> None:
        self._window_size: int = window_size
        self._limit_type: LimitType = limit_type

    @property
    def window_size(self) -> int:
        return self._window_size

    @window_size.setter
    def window_size(self, value: int) -> None:
        self._window_size = value

    @property
    def limit_type(self) -> LimitType:
        return self._limit_type

    @limit_type.setter
    def limit_type(self, value: LimitType) -> None:
        self._limit_type = value

    def from_bytes(self, data: bytes) -> None:
        self._window_size: int = int.from_bytes(data[:4], 'big')
        self._limit_type: LimitType = int(data[4])

    def to_bytes(self) -> bytes:
        bh: ChunkBasicHeader = ChunkBasicHeader(ControlStream.chunk_id, ControlStream.stream_id)
        header: ChunkMessageHeader = ChunkMessageHeader()
        header.message_length = 5
        header.message_type_id = SetPeerBandwidth.type_id
        return header.to_bytes(bh) + \
            self._window_size.to_bytes(4, byteorder='big') + self._limit_type.to_bytes(1, byteorder='big')


UserControlEventType: IntEnum = IntEnum('UserControlEventType', ('StreamBegin',
                                                                 'StreamEOF',
                                                                 'StreamDry',
                                                                 'SetBufferLength',
                                                                 'StreamIsRecorded',
                                                                 'PingRequest',
                                                                 'PingResponse'),
                                        start=0
                                        )


class UserControlMessage:
    """Contains information used by the RTMP streaming layer"""
    type_id = 4

    def __init__(self,
                 event_type: UserControlEventType = UserControlEventType.StreamBegin,
                 event_data: list = (0, 0)) -> None:
        self._event_type: UserControlEventType = event_type
        self._event_data: list = event_data

    def from_bytes(self, data: bytes) -> None:
        self._event_type: UserControlEventType = int.from_bytes(data[:2], 'big')
        self._event_data[0] = int.from_bytes(data[2:6], 'big')
        if self._event_type == UserControlEventType.SetBufferLength:
            self._event_data[1] = int.from_bytes(data[2:6], 'big')

    @property
    def event_type(self) -> UserControlEventType:
        return self._event_type

    @event_type.setter
    def event_type(self, value: UserControlEventType) -> None:
        self._event_type = value

    @property
    def stream_id(self) -> int:
        if self._event_type == UserControlEventType.PingRequest or\
           self._event_type == UserControlEventType.PingResponse:
            raise ControlMessageException('message has no stream id field')
        return self._event_data[0]

    @stream_id.setter
    def stream_id(self, value: int) -> None:
        if self._event_type == UserControlEventType.PingRequest or\
           self._event_type == UserControlEventType.PingResponse:
            raise ControlMessageException('message has no stream id field')
        self._event_data[0] = value

    @property
    def buffer_length(self) -> int:
        if self._event_type == UserControlEventType.SetBufferLength:
            return self._event_data[1]
        raise ControlMessageException('message has no buffer length field')

    @buffer_length.setter
    def buffer_length(self, value: int) -> None:
        if self._event_type == UserControlEventType.SetBufferLength:
            self._event_data[1] = value
        else:
            raise ControlMessageException('message has no buffer length field')

    @property
    def timestamp(self) -> int:
        if self._event_type == UserControlEventType.PingRequest or \
           self._event_type == UserControlEventType.PingResponse:
            return self._event_data[0]
        raise ControlMessageException('message has no timestamp field')

    @timestamp.setter
    def timestamp(self, value: int):
        if self._event_type == UserControlEventType.PingRequest or \
           self._event_type == UserControlEventType.PingResponse:
            self._event_data[0] = value
        else:
            raise ControlMessageException('message has no timestamp field')

    def to_bytes(self) -> bytes:
        bh: ChunkBasicHeader = ChunkBasicHeader(ControlStream.chunk_id, ControlStream.stream_id)
        header: ChunkMessageHeader = ChunkMessageHeader()
        header.message_length = 10 if self._event_type == UserControlEventType.SetBufferLength else 6
        header.message_type_id = UserControlMessage.type_id
        ret: bytearray = header.to_bytes(bh) + \
            self._event_type.to_bytes(2, byteorder='big') + self._event_data[0].to_bytes(4, byteorder='big')
        if self._event_type == UserControlEventType.SetBufferLength:
            ret += self._event_data[1].to_bytes(4, byteorder='big')
        return ret
