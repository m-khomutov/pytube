"""RTMP protocol network connection"""
import secrets
from datetime import datetime
from enum import IntEnum
from typing import Union
from .chunk import CS0, CSn, Chunk, ChunkMessageHeader
from .messages.amf0 import Number, String
from .messages.command import Command, ResultCommand, Publish
from .messages.control import SetChunkSize
from .messages.control import WindowAcknowledgementSize, SetPeerBandwidth, UserControlMessage, UserControlEventType
from .messages.data import DataMessageException, Data, VideoData, AudioData, PacketType

State: IntEnum = IntEnum('State', ('Initial',
                                   'Handshake'
                                   )
                         )


class ConnectionException(ValueError):
    """Exception, raised on connection errors"""
    pass


class Connection:
    """Manages RTMP protocol network connection activity"""
    @staticmethod
    def version():
        return 3

    def __init__(self, address, params):
        self._root: str = params.get("root", ".")
        self._verbal: bool = params.get("verb", False)
        self._address: str = address
        self._c1: CSn = CSn(0, 0, b'')
        self._s1: CSn = CSn(int(datetime.now().timestamp()), 0, secrets.token_bytes(1528))
        self._state: State = State.Initial
        self._chunk: Chunk = Chunk()
        self._stream_id: float = 1.
        self._publishing_name: str = ''
        print(f'RTMP connect from {self._address}')

    def on_read_event(self, key, buffer):
        """Manager read socket event"""
        if buffer:
            self._on_new_data(buffer, key.data)
            key.data.inb = b''
            return
        raise EOFError()

    def on_write_event(self, key):
        """Manager write socket event"""
        if key.data.outb:
            sent = key.fileobj.send(key.data.outb)  # Should be ready to write
            key.data.outb = key.data.outb[sent:]

    def _on_new_data(self, buffer, data):
        if not self._c1.random:
            self._on_c0(buffer, data)
        elif self._state == State.Initial and len(buffer) >= 1536:
            self._on_c2(buffer)
        else:
            self._chunk.parse(buffer, self._on_new_chunk, data)

    def _on_c0(self, buffer, data):
        c0: CS0 = CS0(buffer[0])
        if c0.version != Connection.version():
            raise ConnectionException(f'unsupported protocol version {c0.version}')
        self._c1 = CSn(int.from_bytes(buffer[1:5], byteorder='big'),
                       int.from_bytes(buffer[5:9], byteorder='big'),
                       buffer[9:])
        s0: bytes = Connection.version().to_bytes(1, 'big')
        s1: bytes = self._s1.time.to_bytes(4, 'big') + self._s1.time2.to_bytes(4, 'big') + self._s1.random
        s2: bytes = self._c1.time.to_bytes(4, 'big') + self._s1.time.to_bytes(4, 'big') + self._c1.random
        data.outb = s0 + s1 + s2

    def _on_c2(self, buffer):
        c2: CSn = CSn(int.from_bytes(buffer[0:4], byteorder='big'),
                      int.from_bytes(buffer[4:8], byteorder='big'),
                      buffer[8:])
        time_ok, time2_ok, random_ok = c2.time == self._s1.time,\
            c2.time2 == self._c1.time,\
            c2.random == self._s1.random
        if not (time_ok and time2_ok and random_ok):
            raise ConnectionException(f'Handshake failed: time {time_ok}, time2 {time2_ok} random {random_ok}')
        self._state = State.Handshake

    def _on_new_chunk(self, header: ChunkMessageHeader, data: bytes, out_data):
        print(header)
        {
            SetChunkSize.type_id: self._on_control,
            Command.amf0_type_id: self._on_command,
            Data.amf0_type_id: self._on_metadata,
            Data.video_type_id: self._on_video_packet,
            Data.audio_type_id: self._on_audio_packet,
        }.get(header.message_type_id)(data, out_data=out_data)

    def _on_control(self, data: bytes, **kwargs) -> None:
        self._chunk.size = SetChunkSize().from_bytes(data).chunk_size
        print(f'new chunk size={self._chunk.size}')
        out_data = kwargs.get('out_data')
        if out_data:
            out_data.outb = ResultCommand(0., self._chunk.size,
                                          additional=Number(8192.).to_bytes(),
                                          name='onBWDone').to_bytes()

    def _on_command(self, data: bytes, **kwargs) -> None:
        command: Union[Command, None] = Command.make(data, self._chunk.size)
        if command:
            print(command)
            out_data = kwargs.get('out_data')
            if out_data:
                {
                    'connect': self._on_connect,
                    'releaseStream': self._on_release_stream,
                    'FCPublish': self._on_fc_publish,
                    'createStream': self._on_create_stream,
                    '_checkbw': self._on_check_bw,
                    'publish': self._on_publish,
                }.get(command.type, None)(command, out_data)

    def _on_connect(self, command: Command, out_data) -> None:
        out_data.outb = WindowAcknowledgementSize().to_bytes() + \
                        SetPeerBandwidth().to_bytes() + \
                        UserControlMessage().to_bytes() + \
                        SetChunkSize().to_bytes() + \
                        ResultCommand(command.transaction_id, self._chunk.size,
                                      object={
                                          'fmsVer': String('FMS/3,0,1,123'),
                                          'capabilities': Number(31.)
                                      },
                                      args={
                                          'level': String('status'),
                                          'code': String('NetConnection.Connect.Success'),
                                          'description': String('Connection succeeded.'),
                                          'objectEncoding': Number(0.)
                                      }).to_bytes()

    def _on_release_stream(self, command: Command, out_data) -> None:
        out_data.outb = ResultCommand(command.transaction_id, self._chunk.size).to_bytes()

    def _on_fc_publish(self, command: Command, out_data) -> None:
        out_data.outb = ResultCommand(command.transaction_id, self._chunk.size, name='onFCPublish').to_bytes()

    def _on_create_stream(self, command: Command, out_data) -> None:
        out_data.outb = ResultCommand(command.transaction_id, self._chunk.size,
                                      additional=Number(self._stream_id).to_bytes()).to_bytes()

    def _on_check_bw(self, command: Command, out_data) -> None:
        out_data.outb = ResultCommand(command.transaction_id, self._chunk.size).to_bytes()

    def _on_publish(self, command: Publish, out_data) -> None:
        self._publishing_name = command.publishing_name
        out_data.outb = UserControlMessage(UserControlEventType.StreamBegin, [1, 0]).to_bytes() +\
            ResultCommand(0, self._chunk.size,
                          args={
                              'level': String('status'),
                              'code': String('NetStream.Publish.Start'),
                              'description': String(f'{command.publishing_name} is now published'),
                              'details': String(command.publishing_name)
                          },
                          name='onStatus').to_bytes()

    def _on_metadata(self, data: bytes, **kwargs) -> None:
        metadata: Union[Data, None] = Data.make(data)
        print(f'{metadata}')

    def _on_video_packet(self, data: bytes, **kwargs) -> None:
        try:
            VideoData(data, self._video_callback)
        except DataMessageException as ex:
            print(ex)

    def _video_callback(self, packet_type: PacketType, payload: bytes) -> None:
        if packet_type == PacketType.SequenceHeader:
            print(VideoData.configuration)
        for i in payload[:10]:
            print(f'{i:x}', end=' ')
        print(f' of {len(payload)}')

    def _on_audio_packet(self, data: bytes, **kwargs) -> None:
        AudioData(data, self._audio_callback)

    def _audio_callback(self, packet_type: PacketType, payload: bytes) -> None:
        for i in payload[:5]:
            print(f'{i:x}', end=' ')
        print(f' of {len(payload)}')
