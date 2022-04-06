"""AMF encoded exchange commands"""
from __future__ import annotations
from typing import Union
from .amf0 import Type as Amf0


class CommandMessageException(Exception):
    pass


class Command:
    amf0_type_id = 20

    @staticmethod
    def make(data: bytes) -> Union[Command, None]:
        type_: Amf0 = Amf0(data)
        return {
            'connect': lambda d: Connect(d),
        }.get(type_.value, lambda d: None)(data)


class Connect(Command):
    def __init__(self, data: bytes):
        type_: Amf0 = Amf0(data)
        if type_.value != 'connect':
            raise CommandMessageException(f'invalid type: {type_.value}. Connect expected')
        self._size = len(type_)
        type_ = Amf0(data[self._size:])
        self._size = self._size + len(type_)
        self._transaction_id: float = type_.value
        type_ = Amf0(data[self._size:])
        self._size = self._size + len(type_)
        self._command_object = type_.value

    def __len__(self) -> int:
        return self._size

    def __repr__(self):
        return f'{self.__class__.__name__}(transaction={self._transaction_id}, object={self._command_object})'
