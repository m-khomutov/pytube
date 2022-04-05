"""Control messages. These messages contain information needed
   by the RTMP Chunk Stream protocol"""
from enum import IntEnum

LimitType: IntEnum = IntEnum('LimitType', ('Hard',
                                           'Soft',
                                           'Dynamic')
                             )


class SetChunkSize:
    """Used to notify the peer of a new maximum chunk size"""
    type_id: int = 1

    def __init__(self, data: bytes) -> None:
        self._chunk_size: int = int.from_bytes(data[:4], 'big') & 0x7fffffff

    @property
    def chunk_size(self) -> int:
        return self._chunk_size


class AbortMessage:
    """Used to notify the peer if it is waiting for chunks to complete a message,
       then to discard the partially received message over a chunk stream."""
    type_id: int = 2

    def __init__(self, data: bytes) -> None:
        self._chunk_stream_id: int = int.from_bytes(data[:4], 'big')

    @property
    def chunk_stream_id(self) -> int:
        return self._chunk_stream_id


class Acknowledgement:
    """Is sent to the peer after receiving bytes equal to the window size"""
    type_id = 3

    def __init__(self, data: bytes) -> None:
        self._sequence_number: int = int.from_bytes(data[:4], 'big')

    @property
    def sequence_number(self) -> int:
        return self._sequence_number


class WindowAcknowledgementSize:
    """Is sent to inform the peer of the window size to use between sending acknowledgments"""
    type_id = 5

    def __init__(self, data: bytes) -> None:
        self._window_size: int = int.from_bytes(data[:4], 'big')

    @property
    def window_size(self) -> int:
        return self._window_size


class SetPeerBandwidth:
    """Is sent to limit the output bandwidth of its peer"""
    type_id = 6

    def __init__(self, data: bytes) -> None:
        self._window_size: int = int.from_bytes(data[:4], 'big')
        self._limit_type: LimitType = int(data[4])

    @property
    def window_size(self) -> int:
        return self._window_size

    @property
    def limit_type(self) -> LimitType:
        return self._limit_type
