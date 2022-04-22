"""An improved compact binary format that is used to serialize ActionScript object graphs"""
from enum import IntEnum
import struct

TypeMarker: IntEnum = IntEnum('TypeMarker', ('Undefined',
                                             'Null',
                                             'False',
                                             'True',
                                             'Integer',
                                             'Double',
                                             'String',
                                             'XmlDoc',
                                             'Date',
                                             'Array',
                                             'Object',
                                             'Xml',
                                             'ByteArray'),
                              start=0
                              )


class Type:
    def __init__(self, data: bytes) -> None:
        self._marker: TypeMarker = int(data[0])
        {
            TypeMarker.Integer: self._integer,
            TypeMarker.Double: self._double
        }.get(self._marker, self._no_information)(data[1:])

    def _no_information(self, data: bytes):
        pass

    def _integer(self, data: bytes):
        self._value = int.from_bytes(data[:4], 'big')

    def _double(self, data: bytes):
        self._value = struct.unpack('d', data[:8])
