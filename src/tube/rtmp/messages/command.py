"""AMF encoded exchange commands"""
from __future__ import annotations
from typing import Optional
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
    def make(data: bytes, chunk_size: int) -> Optional[Command]:
        type_: Amf0 = Amf0.make(data)
        return {
            'connect': Connect,
            'releaseStream': ReleaseStream,
            'FCPublish': FCPublish,
            'createStream': CreateStream,
            '_checkbw': CheckBandwidth,
            'publish': Publish,
        }.get(type_.value, lambda d, sz: None)(data, chunk_size)

    def __init__(self, chunk_size: int, data: bytes = None) -> None:
        self._chunk_size: int = chunk_size
        self._size: int = 0
        self._type: str = ''
        self.transaction_id: float = .0
        self._command_object: Object = Object()
        self._optional_arguments: Object = Object()
        self._additional_fields: bytes = b''
        if data:
            self.from_bytes(data)

    def __len__(self) -> int:
        return self._size

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
        else:
            header.message_length += len(Null())
            ret += Null().to_bytes()
        if len(self._optional_arguments) > 4:
            header.message_length += len(self._optional_arguments)
            ret += self._optional_arguments.to_bytes()
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
    def __init__(self, data: bytes, chunk_size: int) -> None:
        super().__init__(chunk_size, data)
        if self._type != 'connect':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self.transaction_id}, object={str(self._command_object)})'


class ReleaseStream(Command):
    def __init__(self, data: bytes, chunk_size: int) -> None:
        super().__init__(chunk_size, data)
        if self._type != 'releaseStream':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')
        field: Amf0 = Amf0.make(data[self._size:])
        self._size += len(field)
        self._stream_name = field.value

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self.transaction_id}, stream={str(self._stream_name)})'


class FCPublish(Command):
    def __init__(self, data: bytes, chunk_size: int) -> None:
        super().__init__(chunk_size, data)
        if self._type != 'FCPublish':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')
        field: Amf0 = Amf0.make(data[self._size:])
        self._size += len(field)
        self._stream_name = field.value

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self.transaction_id}, stream={str(self._stream_name)})'


class CreateStream(Command):
    def __init__(self, data: bytes, chunk_size: int) -> None:
        super().__init__(chunk_size, data)
        if self._type != 'createStream':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self.transaction_id})'


class CheckBandwidth(Command):
    def __init__(self, data: bytes, chunk_size: int) -> None:
        super().__init__(chunk_size, data)
        if self._type != '_checkbw':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self.transaction_id})'


class Publish(Command):
    def __init__(self, data: bytes, chunk_size: int) -> None:
        super().__init__(chunk_size, data)
        if self._type != 'publish':
            raise CommandMessageException(f'invalid type: {self._type}. Connect expected')
        field: Amf0 = Amf0.make(data[self._size:])
        self._size += len(field)
        self.publishing_name = field.value
        field: Amf0 = Amf0.make(data[self._size:])
        self._size += len(field)
        self.publishing_type = field.value

    def __repr__(self):
        return f'{self.__class__.__name__}' \
               f'(transaction={self.transaction_id}, name={self.publishing_name}, type={self.publishing_type})'


class ResultCommand(Command):
    def __init__(self, transaction_id: float, chunk_size: int, **kwargs) -> None:
        super().__init__(chunk_size)
        self.transaction_id = transaction_id
        if kwargs.get('object'):
            self._command_object = Object(kwargs.get('object'))
        if kwargs.get('args'):
            self._optional_arguments = Object(kwargs.get('args'))
        if kwargs.get('additional'):
            self._additional_fields = kwargs.get('additional')
        if kwargs.get('name'):
            self._type = kwargs.get('name')
        else:
            self._type = '_result'

    def to_bytes(self) -> bytes:
        return super().to_bytes()
