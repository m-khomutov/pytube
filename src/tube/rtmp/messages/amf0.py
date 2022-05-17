"""A compact binary format that is used to serialize ActionScript object graphs"""
from __future__ import annotations
import struct
from enum import IntEnum
from typing import Dict, List, Any

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
    @staticmethod
    def make(data: bytes) -> Type:
        marker: TypeMarker = int(data[0])
        rc = {
            TypeMarker.Number: Number(),
            TypeMarker.Boolean: Boolean(),
            TypeMarker.String: String(),
            TypeMarker.Object: Object(),
            TypeMarker.Null: Null(),
            TypeMarker.EcmaArray: EcmaArray(),
        }.get(marker, lambda: None)
        rc.from_bytes(data[1:])
        return rc

    def __init__(self, marker: TypeMarker):
        self.marker: TypeMarker = marker
        self._value: Any = None
        self._size: int = 0

    def __len__(self):
        return self._size

    def __repr__(self):
        return f'{self.__class__.__name__}(value={self._value})'

    @property
    def value(self):
        return self._value

    def from_bytes(self, data: bytes) -> Type:
        raise NotImplementedError

    def to_bytes(self) -> bytes:
        raise NotImplementedError


class Number(Type):
    def __init__(self, value: float = 0.):
        super().__init__(TypeMarker.Number)
        self._value = value
        self._size = 9

    def from_bytes(self, data: bytes) -> Type:
        self._value = struct.unpack('>d', data[:8])[0]
        return self

    def to_bytes(self) -> bytes:
        return struct.pack('>Bd', int(self.marker), float(self._value))


class Boolean(Type):
    def __init__(self, value: bool = False):
        super().__init__(TypeMarker.Boolean)
        self._value = value
        self._size = 2

    def from_bytes(self, data: bytes) -> Type:
        self._value = data[0] != b'\x00'
        return self

    def to_bytes(self) -> bytes:
        return b'\x01' if self._value else b'\x00'


class String(Type):
    def __init__(self, value: str = ''):
        super().__init__(TypeMarker.String)
        self._value = value
        self._size = 3 + len(value)

    def from_bytes(self, data: bytes) -> Type:
        size: int = struct.unpack('>H', data[:2])[0]
        self._value = data[2:2+size].decode('utf-8')
        self._size = 3 + len(self._value)
        return self

    def to_bytes(self) -> bytes:
        return struct.pack('>BH', int(self.marker), len(self._value)) + self._value.encode('utf-8')


class Object(Type):
    def __init__(self, value: Dict[str: Any, ...] = None):
        super().__init__(TypeMarker.Object)
        self._value = value if value else dict()
        self._size = 4
        for item in self._value.items():
            self._size += len(item[0]) + 2 + len(item[1])

    def from_bytes(self, data: bytes) -> Type:
        self._value = dict()
        off: int = 0
        while True:
            key: str = String().from_bytes(data[off:]).value
            off += len(key) + 2
            self._value[key]: Type = Type.make(data[off:])
            off += len(self._value[key])
            if data[off] == data[off + 1] == 0 and data[off + 2] == TypeMarker.ObjectEnd:
                break
        self._size = off + 4
        return self

    def to_bytes(self) -> bytes:
        rc: bytes = struct.pack('B', int(self.marker))
        for item in self._value.items():
            rc += struct.pack('>H', len(item[0])) + item[0].encode('utf-8') + item[1].to_bytes()
        return rc + b'\x00\x00' + struct.pack('B', int(TypeMarker.ObjectEnd))


class Null(Type):
    def __init__(self):
        super().__init__(TypeMarker.Null)
        self._size = 1

    def from_bytes(self, data: bytes) -> Type:
        return self

    def to_bytes(self) -> bytes:
        return struct.pack('B', int(self.marker))


class Reference(Type):
    def __init__(self, value: int = 0):
        super().__init__(TypeMarker.Reference)
        self._value = value
        self._size = 3

    def from_bytes(self, data: bytes) -> Type:
        self._value = struct.unpack('>H', data[:2])[0]
        return self

    def to_bytes(self) -> bytes:
        return struct.pack('>BH', int(self.marker), self._value)


class EcmaArray(Type):
    def __init__(self, value: Dict[str: Any, ...] = None):
        super().__init__(TypeMarker.EcmaArray)
        self._value = value if value else dict()
        self._size = 4
        for item in self._value.items():
            self._size += len(item[0]) + 2 + len(item[1])

    def from_bytes(self, data: bytes) -> Type:
        self._value = dict()
        count: int = struct.unpack('>I', data[:4])[0]
        off: int = 4
        for _ in range(count):
            key: str = String().from_bytes(data[off:]).value
            off += len(key) + 2
            self._value[key]: Type = Type.make(data[off:])
            off += len(self._value[key])
        self._size = off
        return self

    def to_bytes(self) -> bytes:
        rc: bytes = struct.pack('>BI', int(self.marker), len(self._value))
        for item in self._value.items():
            rc += struct.pack('>H', len(item[0])) + item[0].encode('utf-8') + item[1].to_bytes()
        return rc


class StrictArray(Type):
    def __init__(self, value: List[Type] = None):
        super().__init__(TypeMarker.StrictArray)
        self._value = value if value else []
        self._size = 4
        for item in self._value:
            self._size += len(item)

    def from_bytes(self, data: bytes) -> Type:
        self._value = []
        count: int = struct.unpack('>I', data[:4])[0]
        off: int = 4
        for _ in range(count):
            self._value.append(Type.make(data[off:]))
            off += len(self._value[-1])
        self._size = off
        return self

    def to_bytes(self) -> bytes:
        rc: bytes = struct.pack('>BI', int(self.marker), len(self._value))
        for item in self._value:
            rc += item.to_bytes()
        return rc


class Date(Type):
    def __init__(self, value: float = 0.):
        super().__init__(TypeMarker.Date)
        self._value = value
        self._size = 11

    def from_bytes(self, data: bytes) -> Type:
        # time-zone = S16 ; reserved, not supported should be set to 0x0000
        self._value = struct.unpack('>d', data[2:10])[0]
        return self

    def to_bytes(self) -> bytes:
        return struct.pack('B', int(self.marker)) + b'\x00\x00' + struct.pack('>d', float(self._value))


class LongString(Type):
    def __init__(self, value: str = ''):
        super().__init__(TypeMarker.LongString)
        self._value = value
        self._size = 5 + len(value)

    def from_bytes(self, data: bytes) -> Type:
        size: int = struct.unpack('>I', data[:4])[0]
        self._value = data[4:4+size].decode('utf-8')
        self._size = 5 + len(self._value)
        return self

    def to_bytes(self) -> bytes:
        return struct.pack('>BI', int(self.marker), len(self._value)) + self._value.encode('utf-8')


class TypedObject(Type):
    def __init__(self, name: str, value: Object = Object()):
        super().__init__(TypeMarker.TypedObject)
        self._value = value
        self._name: str = name
        self._size = len(self._name) + 2 + len(self._value)

    def from_bytes(self, data: bytes) -> Type:
        self._value = Object()
        off: int = struct.unpack('>H', data[:2])[0]
        self._name = data[2:2+off].decode('utf-8')
        off += 2
        self._value = Object().from_bytes(data[off:])
        self._size = off + len(self._value)
        return self

    def to_bytes(self) -> bytes:
        return struct.pack('>BH', int(self.marker), len(self._name)) +\
               self._name.encode('utf-8') +\
               self._value.to_bytes()[1:]
