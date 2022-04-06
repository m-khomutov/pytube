"""RTMP protocol message format"""
from collections import namedtuple

CS0 = namedtuple('CS0', 'version')
CSn = namedtuple('CSn', 'time time2 random')


class ChunkException(ValueError):
    """Exception, raised on chunk errors"""
    pass


class ChunkBasicHeader:
    """
    +-+-+-+-+-+-+-+-+
    |fmt|   cs id   |
    +-+-+-+-+-+-+-+-+
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |fmt|     0     |    cs id - 64 |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |fmt|     1     |         cs id - 64            |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+"""
    def __init__(self, message: bytes):
        self.chunk_type: int = message[0] >> 6
        self.chunk_stream_id: int = message[0] & 0x3f
        self._length = 1
        if self.chunk_stream_id == 0:
            self.chunk_stream_id = int(message[1]) + 64
            self._length = 2
        elif self.chunk_stream_id == 1:
            self.chunk_stream_id = int(message[2]) * 256 + int(message[1]) + 64
            self._length = 3

    def __len__(self):
        return self._length

    def __repr__(self):
        return f'{self.__class__.__name__}(fmt={self.chunk_type}, cs id={self.chunk_stream_id})'


class ChunkMessageHeader:
    """
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |                  timestamp                    |message length |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |      message length (cont)    |message type id| msg stream id |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
    |          message stream id (cont)             |
    +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ """
    def __init__(self):
        self.timestamp: int = 0
        self.message_length: int = 0
        self.message_type_id: int = 0
        self.message_stream_id: int = 0
        self._length: int = 0

    def parse(self, message: bytes):
        """Parses three parts of Chunk Header"""
        basic_header: ChunkBasicHeader = ChunkBasicHeader(message)
        self._length = len(basic_header)
        {
            0: self._type_0,
            1: self._type_1,
            2: self._type_2,
        }.get(basic_header.chunk_type, self._type_3)(message[self._length:self._length+11])
        if self.timestamp == 0xffffff:
            self.timestamp = int(message[self._length:self._length+4])
            self._length += 4

    def _type_0(self, message: bytes):
        self._type_1(message)
        self.message_stream_id = int.from_bytes(message[7:11], byteorder='big')
        self._length += 3

    def _type_1(self, message: bytes):
        self._type_2(message)
        self.message_length = int.from_bytes(message[3:6], byteorder='big')
        self.message_type_id = int(message[6])
        self._length += 4

    def _type_2(self, message: bytes):
        self.timestamp += int.from_bytes(message[0:3], byteorder='big')
        self._length += 4

    def _type_3(self, message: bytes):
        pass

    def __repr__(self):
        return f'{self.__class__.__name__}(timestamp={self.timestamp},' \
               f' message length={self.message_length}),' \
               f' message type id={self.message_type_id},' \
               f' message stream id={self.message_stream_id}'

    def __len__(self):
        return self._length


class Chunk:
    """
    +--------------+----------------+--------------------+--------------+
    | Basic Header | Message Header | Extended Timestamp | Chunk Data   |
    +--------------+----------------+--------------------+--------------+
    <-------------------- Chunk Header ------------------>"""
    _default_size: int = 128

    def __init__(self):
        self._size = self.__class__._default_size
        self._header: ChunkMessageHeader = ChunkMessageHeader()
        self._data: bytearray = bytearray()
        self._start_of_chunk: bool = True

    @property
    def size(self):
        return self._size

    def parse(self, buffer: bytes, callback):
        """Parses Chunk Header, Stores Chunk Data"""
        offset: int = 0
        while offset < len(buffer):
            if self._start_of_chunk:
                self._header.parse(buffer[offset:offset+11])
                offset += len(self._header)
            rc: int = self._store_data(buffer[offset:offset+self._size])
            self._start_of_chunk = rc >= self._size
            offset += rc
            if self._ready():
                callback(self._header, self._data)
                self._reset()

    def _ready(self) -> bool:
        return len(self._data) == self._header.message_length

    def _store_data(self, buffer: bytes) -> int:
        self._data += buffer[:self._header.message_length]
        return len(buffer) if self._header.message_length > len(buffer) else self._header.message_length

    def _reset(self):
        self._start_of_chunk = True
        self._data = b''
