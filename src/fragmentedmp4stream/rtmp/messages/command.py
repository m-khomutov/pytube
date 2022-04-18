"""AMF encoded exchange commands"""
from __future__ import annotations
from typing import Union
from .amf0 import Type as Amf0
from .amf0 import TypeMarker as Amf0Marker
from ..chunk import ChunkBasicHeader, ChunkMessageHeader


class CommandMessageException(Exception):
    pass


class CommandStream:
    chunk_id: int = 0
    stream_id: int = 3


class Command:
    amf0_type_id = 20

    @staticmethod
    def make(data: bytes) -> Union[Command, None]:
        type_: Amf0 = Amf0()
        type_.from_bytes(data)
        return {
            'connect': Command.make_connect_command,
        }.get(type_.value, lambda d: None)(data)

    @staticmethod
    def make_connect_command(data: bytes) -> Command:
        command: Connect = Connect()
        command.from_bytes(data)
        return command

    def __init__(self):
        self._size: int = 0
        self._type: str = ''
        self.transaction_id: float = .0
        self._command_object: Amf0 = Amf0(Amf0Marker.Object)
        self._optional_arguments: Amf0 = Amf0(Amf0Marker.Object)

    @property
    def type(self):
        return self._type

    def from_bytes(self, data: bytes) -> None:
        field: Amf0 = Amf0()
        field.from_bytes(data)
        self._type = field.value
        self._size = len(field)
        field.from_bytes(data[self._size:])
        self._size = self._size + len(field)
        self.transaction_id = field.value
        field.from_bytes(data[self._size:])
        self._size = self._size + len(field)
        self._command_object = field.value
        if self._size < len(data):
            field.from_bytes(data[self._size:])
            self._size = self._size + len(field)
            self._optional_arguments = field.value

    def to_bytes(self) -> bytes:
        bh: ChunkBasicHeader = ChunkBasicHeader(CommandStream.chunk_id, CommandStream.stream_id)
        header: ChunkMessageHeader = ChunkMessageHeader()
        header.message_type_id = Command.amf0_type_id
        field: Amf0 = Amf0(Amf0Marker.String, self._type)
        header.message_length = len(field)
        ret: bytes = field.to_bytes()
        field = Amf0(Amf0Marker.Number, self.transaction_id)
        header.message_length += len(field) + len(self._command_object)
        ret += field.to_bytes()
        if len(self._command_object) > 0:
            ret += self._command_object.to_bytes()
        return header.to_bytes(bh) + ret


class Connect(Command):
    def __init__(self) -> None:
        super().__init__()

    def from_bytes(self, data: bytes) -> None:
        super().from_bytes(data)
        if self._type != 'connect':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')

    def __len__(self) -> int:
        return self._size

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self.transaction_id}, object={str(self._command_object)})'


class ResultCommand(Command):
    def __init__(self, transaction_id: float) -> None:
        super().__init__()
        self._type = '_result'
        self.transaction_id = transaction_id

    def to_bytes(self) -> bytes:
        return super().to_bytes()
