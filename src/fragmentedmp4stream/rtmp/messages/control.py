"""Control messages. These messages contain information needed
   by the RTMP Chunk Stream protocol"""
from enum import IntEnum
from typing import List
from ..chunk import ChunkBasicHeader, ChunkMessageHeader


class ControlMessageException(Exception):
    pass


LimitType: IntEnum = IntEnum('LimitType', ('Hard',
                                           'Soft',
                                           'Dynamic')
                             )


class ControlStream:
    chunk_id: int = 2
    stream_id: int = 0


class SetChunkSize:
    """Used to notify the peer of a new maximum chunk size"""
    type_id: int = 1

    def __init__(self, chunk_size: int =128) -> None:
        self._chunk_size: int = chunk_size

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    def from_bytes(self, data: bytes) -> None:
        self._chunk_size: int = int.from_bytes(data[:4], 'big') & 0x7fffffff


class AbortMessage:
    """Used to notify the peer if it is waiting for chunks to complete a message,
       then to discard the partially received message over a chunk stream."""
    type_id: int = 2

    def __init__(self, chunk_stream_id: int) -> None:
        self._chunk_stream_id: int = chunk_stream_id

    @property
    def chunk_stream_id(self) -> int:
        return self._chunk_stream_id

    def from_bytes(self, data: bytes) -> None:
        self._chunk_stream_id: int = int.from_bytes(data[:4], 'big')


class Acknowledgement:
    """Is sent to the peer after receiving bytes equal to the window size"""
    type_id = 3

    def __init__(self, sequence_number: int) -> None:
        self._sequence_number: int = sequence_number

    @property
    def sequence_number(self) -> int:
        return self._sequence_number

    def from_bytes(self, data: bytes) -> None:
        self._sequence_number: int = int.from_bytes(data[:4], 'big')


class WindowAcknowledgementSize:
    """Is sent to inform the peer of the window size to use between sending acknowledgments"""
    type_id = 5

    def __init__(self, window_size: int = 25000) -> None:
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
        return header.to_bytes(bh) + self._window_size.to_bytes(4, byteorder='big')


class SetPeerBandwidth:
    """Is sent to limit the output bandwidth of its peer"""
    type_id = 6

    def __init__(self, window_size: int, limit_type: LimitType) -> None:
        self._window_size: int = window_size
        self._limit_type: LimitType = limit_type

    @property
    def window_size(self) -> int:
        return self._window_size

    @property
    def limit_type(self) -> LimitType:
        return self._limit_type

    def from_bytes(self, data: bytes) -> None:
        self._window_size: int = int.from_bytes(data[:4], 'big')
        self._limit_type: LimitType = int(data[4])


UserControlEventType: IntEnum = IntEnum('UserControlEventType', ('StreamBegin',
                                                                 'StreamEOF',
                                                                 'StreamDry',
                                                                 'SetBufferLength',
                                                                 'StreamIsRecorded',
                                                                 'PingRequest',
                                                                 'PingResponse')
                                        )


class UserControlMessage:
    """Contains information used by the RTMP streaming layer"""
    type_id = 4

    def __init__(self, event_type: UserControlEventType, event_data: list) -> None:
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

    @property
    def stream_id(self) -> int:
        if self._event_type == UserControlEventType.PingRequest or\
           self._event_type == UserControlEventType.PingResponse:
            raise ControlMessageException('message has no stream id field')
        return self._event_data[0]

    @property
    def buffer_length(self) -> int:
        if self._event_type == UserControlEventType.SetBufferLength:
            return self._event_data[1]
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
