"""The client or the server sends this message to send Metadata or any
    user data to the peer. Metadata includes details about the
    data(audio, video etc.) like creation time, duration, theme and so
    on. These messages have been assigned message type value of 18 for
    AMF0 and message type value of 15 for AMF3.
"""
from __future__ import annotations
from typing import Union
from .amf0 import Type as Amf0


class DataMessageException(Exception):
    pass


class Data:
    amf0_type_id = 18

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
        self._object: Amf0 = Amf0.make(data[self._size:])

    def __repr__(self):
        return f'{self.__class__.__name__}(object={self._object})'
