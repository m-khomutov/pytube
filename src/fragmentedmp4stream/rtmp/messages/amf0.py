"""A compact binary format that is used to serialize ActionScript object graphs"""
from __future__ import annotations
import struct
from enum import IntEnum
from functools import reduce
from typing import Dict, List, Tuple, Union

TypeMarker: IntEnum = IntEnum('TypeMarker', ('Number',
                                             'Boolean',
                                             'String',
                                             'Object',
                                             'MovieClip',
                                             'Null',
                                             'Undefined',
                                             'Reference',
                                             'EcmaArray',
                                             'ObjectEnd',
                                             'StrictArray',
                                             'Date',
                                             'LongString',
                                             'Unsupported',
                                             'RecordSet',
                                             'XmlDocument',
                                             'TypedObject',
                                             'AvmPlusObject'),
                              start=0
                              )


class Null:
    pass


class Type:
    def __init__(self, value: Union[float, bool, str, Dict, Null]):
        self._marker: TypeMarker = {
            'float': TypeMarker.Number,
            'str': TypeMarker.String,
            'dict': TypeMarker.Object,
            'Null': TypeMarker.Null,
        }.get(value.__class__.__name__, TypeMarker.Undefined)
        self._size: int = \
            {
                TypeMarker.Number: lambda v: 9,
                TypeMarker.String: lambda v: 3 + len(v),
                TypeMarker.Object: lambda v: 4 + reduce(lambda s, item:
                                                        s + len(item[0]) + 2 + len(Type(item[1])), v.items(), 0),
            }.get(self._marker, lambda v: 1)(value)
        self._value = value

    def from_bytes(self, data: bytes) -> None:
        if data:
            self._marker = int(data[0])
            self._size = 1
        if len(data) > 1:
            self._value = {
                TypeMarker.Number: self._number,
                TypeMarker.Boolean: self._boolean,
                TypeMarker.String: self._string,
                TypeMarker.Object: self._object,
                TypeMarker.Reference: self._reference,
                TypeMarker.EcmaArray: self._ecma_array,
                TypeMarker.StrictArray: self._strict_array,
                TypeMarker.Date: self._date,
                TypeMarker.LongString: self._long_string,
                TypeMarker.XmlDocument: self._long_string,
                TypeMarker.TypedObject: self._typed_object
            }.get(self._marker, self._no_information)(data[1:])

    def to_bytes(self) -> bytes:
        return self._marker.to_bytes(1, byteorder='big') +\
            {
                TypeMarker.Number: self._number_to_bytes,
                TypeMarker.Boolean: self._boolean_to_bytes,
                TypeMarker.String: self._string_to_bytes,
                TypeMarker.Object: self._object_to_bytes,
                TypeMarker.Reference: self._reference_to_bytes,
                TypeMarker.EcmaArray: self._ecma_array_to_bytes,
                TypeMarker.StrictArray: self._strict_array_to_bytes,
                TypeMarker.Date: self._date_to_bytes,
                TypeMarker.LongString: self._long_string_to_bytes,
                TypeMarker.XmlDocument: self._long_string_to_bytes,
                TypeMarker.TypedObject: self._typed_object_to_bytes,
            }.get(self._marker, lambda: b'')()

    def __len__(self):
        return self._size

    def __repr__(self):
        return f'{self.__class__.__name__}(marker={self._marker}, value={str(self._value)})'

    @property
    def value(self) -> Union[float, bool, str, Dict]:
        return self._value

    def _number(self, data: bytes) -> float:
        self._size = self._size + 8
        return struct.unpack('>d', data[:8])[0]

    def _number_to_bytes(self) -> bytes:
        return struct.pack('>d', float(self._value))

    def _boolean(self, data: bytes) -> bool:
        self._size = self._size + 1
        return data[0] != b'\x00'

    def _boolean_to_bytes(self) -> bytes:
        return b'\x01' if self._value else b'\x00'

    def _string(self, data: bytes) -> str:
        size = struct.unpack('>H', data[:2])[0]
        self._size = self._size + 2 + size
        return data[2:2+size].decode('utf-8')

    def _string_to_bytes(self) -> bytes:
        return struct.pack('>H', len(self._value)) + str(self._value).encode('utf-8')

    def _object(self, data: bytes) -> Dict[str, ...]:
        object_: Dict[str, ...] = {}
        while True:
            key: str = self._string(data[self._size-1:])
            object_[key]: Type = Type(.0)
            object_[key].from_bytes(data[self._size-1:])
            self._size = self._size + len(object_[key])
            if data[self._size-1] == data[self._size] == 0 and data[self._size+1] == TypeMarker.ObjectEnd:
                self._size = self._size + 3
                break
        return object_

    def _object_to_bytes(self) -> bytes:
        rc = b''
        for item in self._value.items():
            rc += Type(item[0]).to_bytes()[1:] + Type(item[1]).to_bytes()
        return rc + b'\x00\x00\x09'

    def _reference(self, data: bytes) -> int:
        self._size = self._size + 2
        return struct.unpack('>H', data[:2])[0]

    def _reference_to_bytes(self) -> bytes:
        return struct.pack('>H', self._value)

    def _ecma_array(self, data: bytes) -> Dict[str, ...]:
        array_: Dict[str, ...] = {}
        count: int = struct.unpack('>I', data[:4])[0]
        self._size = self._size + 4
        for _ in range(count):
            key: str = self._string(data[self._size-1:])
            array_[key]: Type = Type(.0)
            array_[key].from_bytes(data[self._size-1:])
            self._size = self._size + len(array_[key])
        return array_

    def _ecma_array_to_bytes(self) -> bytes:
        return b''

    def _strict_array(self, data: bytes) -> List[Type]:
        array_: List = [Type]
        count: int = struct.unpack('>I', data[:4])[0]
        self._size = self._size + 4
        for _ in range(count):
            entry: Type = Type(.0)
            entry.from_bytes(data[self._size - 1:])
            array_.append(entry)
            self._size = self._size + len(array_[-1])
        return array_

    def _strict_array_to_bytes(self) -> bytes:
        return b''

    def _date(self, data: bytes) -> float:
        self._size = self._size + 2
        return self._number(data)

    def _date_to_bytes(self) -> bytes:
        return b''

    def _long_string(self, data: bytes) -> str:
        size = struct.unpack('>I', data[:4])[0]
        self._size = self._size + 4 + size
        return data[4:4+size].decode('utf-8')

    def _long_string_to_bytes(self) -> bytes:
        return b''

    def _typed_object(self, data: bytes) -> Tuple[str, Dict[str, ...]]:
        name: str = self._string(data)
        return name, self._object(data[self._size-1:])

    def _typed_object_to_bytes(self) -> bytes:
        return b''

    def _no_information(self, data: bytes = b''):
        pass
