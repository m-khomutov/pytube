"""AMF encoded exchange commands"""
from __future__ import annotations
from typing import Union
from .amf0 import Type as Amf0
from .amf0 import TypeMarker, Number, String, Object, Null
from ..chunk import ChunkBasicHeader, ChunkMessageHeader


class CommandMessageException(Exception):
    pass


class CommandStream:
    chunk_id: int = 0
    stream_id: int = 3


class Command:
    amf0_type_id = 20

    @staticmethod
    def make(data: bytes, chunk_size: int) -> Union[Command, None]:
        type_: Amf0 = Amf0.make(data)
        return {
            'connect': Command.make_connect_command,
            'releaseStream': Command.make_release_command,
        }.get(type_.value, lambda d, sz: None)(data, chunk_size)

    @staticmethod
    def make_connect_command(data: bytes, chunk_size: int) -> Command:
        command: Connect = Connect(chunk_size)
        command.from_bytes(data)
        return command

    @staticmethod
    def make_release_command(data: bytes, chunk_size: int) -> Command:
        command: ReleaseStream = ReleaseStream(chunk_size)
        command.from_bytes(data)
        return command

    def __init__(self, chunk_size: int) -> None:
        self._chunk_size: int = chunk_size
        self._size: int = 0
        self._type: str = ''
        self.transaction_id: float = .0
        self._command_object: Object = Object()
        self._optional_arguments: Object = Object()
        self._additional_fields: bytes = b''

    @property
    def type(self):
        return self._type

    def from_bytes(self, data: bytes) -> None:
        field: Amf0 = Amf0.make(data)
        self._type = field.value
        self._size = len(field)
        field = Amf0.make(data[self._size:])
        self._size += len(field)
        self.transaction_id = field.value
        field = Amf0.make(data[self._size:])
        self._size += len(field)
        if field.marker == TypeMarker.Object:
            self._command_object = field.value
            if self._size < len(data):
                field = Amf0.make(data[self._size:])
                self._size += len(field)
                self._optional_arguments = field.value

    def to_bytes(self) -> bytes:
        bh: ChunkBasicHeader = ChunkBasicHeader(CommandStream.chunk_id, CommandStream.stream_id)
        header: ChunkMessageHeader = ChunkMessageHeader()
        header.message_type_id = Command.amf0_type_id
        header.message_length = len(self._additional_fields)
        field: String = String(self._type)
        header.message_length += len(field)
        ret: bytes = field.to_bytes()
        field: Number = Number(self.transaction_id)
        header.message_length += len(field)
        ret += field.to_bytes()
        if len(self._command_object) > 4:
            header.message_length += len(self._command_object)
            ret += self._command_object.to_bytes()
            if len(self._optional_arguments) > 4:
                header.message_length += len(self._optional_arguments)
                ret += self._optional_arguments.to_bytes()
        else:
            header.message_length += len(Null())
            ret += Null().to_bytes()
        return header.to_bytes(bh) + self._bytes_to_chunk_size(ret + self._additional_fields)

    def _bytes_to_chunk_size(self, data: bytes) -> bytes:
        if len(data) <= self._chunk_size:
            return data
        rc: bytes = b''
        offset: int = 0
        chunk_size: int = self._chunk_size
        while offset < len(data):
            sz = chunk_size if offset + chunk_size < len(data) else len(data) - offset
            rc += data[offset:offset + sz]
            if offset + sz < len(data):
                rc += ChunkMessageHeader().to_bytes(ChunkBasicHeader(3, 3))
            chunk_size -= 1
            offset += sz
        return rc


class Connect(Command):
    def __init__(self, chunk_size: int) -> None:
        super().__init__(chunk_size)

    def from_bytes(self, data: bytes) -> None:
        super().from_bytes(data)
        if self._type != 'connect':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')

    def __len__(self) -> int:
        return self._size

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self.transaction_id}, object={str(self._command_object)})'


class ResultCommand(Command):
    def __init__(self, transaction_id: float, chunk_size: int, object_: dict = None, args: dict = None) -> None:
        super().__init__(chunk_size)
        self._type = '_result'
        self.transaction_id = transaction_id
        if object_:
            self._command_object = Object(object_)
            if args:
                self._optional_arguments = Object(args)

    def to_bytes(self) -> bytes:
        return super().to_bytes()


class OnBWDoneCommand(Command):
    def __init__(self, transaction_id: float, chunk_size: int, bw: float = 8192.) -> None:
        super().__init__(chunk_size)
        self._type = 'onBWDone'
        self.transaction_id = transaction_id
        self._bw: float = bw

    def to_bytes(self) -> bytes:
        self._additional_fields = Null().to_bytes() + Number(self._bw).to_bytes()
        return super().to_bytes()


class ReleaseStream(Command):
    def __init__(self, chunk_size: int) -> None:
        super().__init__(chunk_size)
        self._stream_name: str = ''

    def from_bytes(self, data: bytes) -> None:
        super().from_bytes(data)
        if self._type != 'releaseStream':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')
        field: Amf0 = Amf0.make(data[self._size:])
        self._size += len(field)
        self._stream_name = field.value

    def __len__(self) -> int:
        return self._size

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self.transaction_id}, stream={str(self._stream_name)})'
