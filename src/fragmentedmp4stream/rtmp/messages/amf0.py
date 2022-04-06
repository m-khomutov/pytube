"""A compact binary format that is used to serialize ActionScript object graphs"""
from __future__ import annotations
import struct
from enum import IntEnum
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


class Type:
    def __init__(self, data: bytes) -> None:
        self._marker: TypeMarker = int(data[0])
        self._size: int = 1
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

    def _boolean(self, data: bytes) -> bool:
        self._size = self._size + 1
        return data[0] != b'\x00'

    def _string(self, data: bytes) -> str:
        size = struct.unpack('>H', data[:2])[0]
        self._size = self._size + 2 + size
        return data[2:2+size].decode('utf-8')

    def _object(self, data: bytes) -> Dict[str, ...]:
        object_: Dict[str, ...] = {}
        while True:
            key: str = self._string(data[self._size-1:])
            object_[key] = Type(data[self._size-1:])
            self._size = self._size + len(object_[key])
            if data[self._size-1] == data[self._size] == 0 and data[self._size+1] == TypeMarker.ObjectEnd:
                self._size = self._size + 3
                break
        return object_

    def _reference(self, data: bytes) -> int:
        self._size = self._size + 2
        return struct.unpack('>H', data[:2])[0]

    def _ecma_array(self, data: bytes) -> Dict[str, ...]:
        array_: Dict[str, ...] = {}
        count: int = struct.unpack('>I', data[:4])[0]
        self._size = self._size + 4
        for _ in range(count):
            key: str = self._string(data[self._size-1:])
            array_[key] = Type(data[self._size-1:])
            self._size = self._size + len(array_[key])
        return array_

    def _strict_array(self, data: bytes) -> List[Type]:
        array_: List = [Type]
        count: int = struct.unpack('>I', data[:4])[0]
        self._size = self._size + 4
        for _ in range(count):
            array_.append(Type(data[self._size-1:]))
            self._size = self._size + len(array_[-1])
        return array_

    def _date(self, data: bytes) -> float:
        self._size = self._size + 2
        return self._number(data)

    def _long_string(self, data: bytes) -> str:
        size = struct.unpack('>I', data[:4])[0]
        self._size = self._size + 4 + size
        return data[4:4+size].decode('utf-8')

    def _typed_object(self, data: bytes) -> Tuple[str, Dict[str, ...]]:
        name: str = self._string(data)
        return name, self._object(data[self._size-1:])

    def _no_information(self, data: bytes):
        pass
