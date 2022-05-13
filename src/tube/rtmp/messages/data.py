"""The client or the server sends this message to send Metadata or any
    user data to the peer. Metadata includes details about the
    data(audio, video etc.) like creation time, duration, theme and so
    on. These messages have been assigned message type value of 18 for
    AMF0 and message type value of 15 for AMF3.
"""
from __future__ import annotations
from .amf0 import Type as Amf0
from .amf0 import TypeMarker, Number, String, Object, Null


class Metadata:
    amf0_type_id = 18

    def __init__(self, data: bytes) -> None:
        type_: Amf0 = Amf0.make(data)
        print(f'Data: {type_.value}')
