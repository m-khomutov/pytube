"""RTMP protocol message format"""
from __future__ import annotations
from collections import namedtuple, defaultdict

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
    def __init__(self, chunk_type: int = 0, stream_id: int = 0) -> None:
        self.chunk_type: int = chunk_type
        self.chunk_stream_id: int = stream_id
        self._length = 1

    def from_bytes(self, message: bytes) -> ChunkBasicHeader:
        self.chunk_type: int = message[0] >> 6
        self.chunk_stream_id: int = message[0] & 0x3f
        if self.chunk_stream_id == 0:
            if len(message) < 2:
                raise ChunkException(f'{self.__class__.__name__}: message too short {len(message)}')
            self.chunk_stream_id = int(message[1]) + 64
            self._length = 2
        elif self.chunk_stream_id == 1:
            if len(message) < 3:
                raise ChunkException(f'{self.__class__.__name__}: message too short {len(message)}')
            self.chunk_stream_id = int(message[2]) * 256 + int(message[1]) + 64
            self._length = 3
        return self

    def to_bytes(self) -> bytes:
        rc = [(self.chunk_type << 6)]
        if self.chunk_stream_id < 64:
            rc[0] |= self.chunk_stream_id
        else:
            stream_id = self.chunk_stream_id - 64
            rc.append(stream_id & 0xff)
            if self.chunk_stream_id > 319:
                rc.append(stream_id >> 8)
        return bytes(rc)

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

    def from_bytes(self, message: bytes) -> ChunkMessageHeader:
        """Parses three parts of Chunk Header"""
        basic_header: ChunkBasicHeader = ChunkBasicHeader()
        basic_header.from_bytes(message)
        self._length = len(basic_header)
        {
            0: self._type0,
            1: self._type1,
            2: self._type2,
        }.get(basic_header.chunk_type, self._type3)(message[self._length:self._length+11])
        if self.timestamp == 0xffffff:
            if len(message) < 16:
                raise ChunkException(f'{self.__class__.__name__}: message too short {len(message)}')
            self.timestamp = int(message[self._length:self._length+4])
            self._length += 4
        return self

    def to_bytes(self, basic_header: ChunkBasicHeader) -> bytes:
        return basic_header.to_bytes() +\
         {
            0: self._type0_to_bytes,
            1: self._type1_to_bytes,
            2: self._type2_to_bytes,
         }.get(basic_header.chunk_type, lambda: b'')()

    def _type0(self, message: bytes):
        if len(message) < 11:
            raise ChunkException(f'{self.__class__.__name__}: message too short {len(message)}')
        self._type1(message)
        self.message_stream_id = int.from_bytes(message[7:11], byteorder='little')
        self._length += 4

    def _type0_to_bytes(self) -> bytes:
        return self._type1_to_bytes() + self.message_stream_id.to_bytes(4, 'little')

    def _type1(self, message: bytes):
        if len(message) < 7:
            raise ChunkException(f'{self.__class__.__name__}: message too short {len(message)}')
        self._type2(message)
        self.message_length = int.from_bytes(message[3:6], byteorder='big')
        self.message_type_id = int(message[6])
        self._length += 4

    def _type1_to_bytes(self) -> bytes:
        return self._type2_to_bytes() +\
               self.message_length.to_bytes(3, 'big') +\
               self.message_type_id.to_bytes(1, 'big')

    def _type2(self, message: bytes):
        if len(message) < 3:
            raise ChunkException(f'{self.__class__.__name__}: message too short {len(message)}')
        self.timestamp += int.from_bytes(message[0:3], byteorder='big')
        self._length += 3

    def _type2_to_bytes(self) -> bytes:
        return self.timestamp.to_bytes(3, 'big')

    def _type3(self, message: bytes):
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
        self._header: defaultdict = defaultdict(lambda: ChunkMessageHeader())
        self._chunk_stream_id: int = 0
        self._data: bytearray = bytearray()
        self._cache: bytearray = bytearray()
        self._start_of_chunk: bool = True
        self._filled_part_of_chunk: int = 0

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        self._size = value

    def parse(self, buffer: bytes, callback, out_data):
        """Parses Chunk Header, Stores Chunk Data"""
        offset: int = 0
        self._cache += buffer
        while offset < len(self._cache):
            if self._start_of_chunk:
                self._filled_part_of_chunk = 0
                try:
                    self._chunk_stream_id = ChunkBasicHeader().from_bytes(self._cache[offset:offset+3]).chunk_stream_id
                    self._header[self._chunk_stream_id].from_bytes(self._cache[offset:offset+16])
                except ChunkException:
                    break
                offset += len(self._header[self._chunk_stream_id])
            rc: int = self._store_data(self._cache[offset:offset+self._free_part()])
            self._start_of_chunk = self._filled_part_of_chunk >= self._size
            offset += rc
            if self._ready():
                callback(self._header[self._chunk_stream_id], self._data, out_data)
                self._reset()
        self._cache = self._cache[offset:]

    def _free_part(self):
        free_in_chunk: int = self._size - self._filled_part_of_chunk
        free_in_message: int = self._header[self._chunk_stream_id].message_length - len(self._data)
        return free_in_chunk if free_in_chunk < free_in_message else free_in_message

    def _ready(self) -> bool:
        return len(self._data) == self._header[self._chunk_stream_id].message_length

    def _store_data(self, buffer: bytes) -> int:
        self._data += buffer
        self._filled_part_of_chunk += len(buffer)
        return len(buffer)

    def _reset(self):
        self._start_of_chunk = True
        self._filled_part_of_chunk = 0
        self._data = b''
