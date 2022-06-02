"""RTP interleaved protocol entities"""
import abc
import time
import random
import logging


class AUHeaderSimpleSection:
    """AUHeader according to rfc3640"""
    def __init__(self, index, size):
        self._value = ((size & 0x1fff) << 3) | (index & 7)

    def to_bytes(self):
        """Returns header as bytestream, ready to be sent to socket."""
        return int(16).to_bytes(2, byteorder='big') + self._value.to_bytes(2, byteorder='big')

    def size(self):
        """Returns AUHeader size"""
        return self._value >> 3


class InterleavedHeader:
    """RTP (+interleaved) header: rfc7826"""
    _first_byte = bytes([0x80])

    def __init__(self, payload_type, channel, synchro_source):
        self._sequence_number = 0
        self._payload_type = payload_type
        self._interleaved_sign = bytes([0x24, channel])
        self._synchro_source = synchro_source.to_bytes(4, 'big')

    @property
    def sequence_number(self):
        """Returns sequence number of a frame"""
        return self._sequence_number

    def to_bytes(self, marker, timestamp, data_size):
        """Returns the header as bytestream, ready to be sent to socket.
           Data size includes media data + 12 bytes of rtp header"""
        ret = self._interleaved_sign + \
            (data_size+12).to_bytes(2, 'big') +\
            self.__class__._first_byte + \
            (marker << 7 | self._payload_type).to_bytes(1, 'big') + \
            self._sequence_number.to_bytes(2, 'big') + \
            timestamp.to_bytes(4, 'big') + \
            self._synchro_source
        self._sequence_number = (self._sequence_number + 1) % 0xffff
        return ret


class FragmentMaker:  # pylint: disable=too-few-public-methods
    """Fragments data on Fragmented Units"""
    def __init__(self, sample, offset, chunk_size=1472):
        self._sample = sample
        self._offset = offset
        self._chunk_size = chunk_size

    def __next__(self):
        if self._offset >= len(self._sample):
            raise StopIteration
        if len(self._sample) <= self._chunk_size:
            self._offset = len(self._sample)
            return 1, self._sample
        next_size = self._chunk_size
        marker = 0
        if self._offset + next_size >= len(self._sample):
            next_size = len(self._sample) - self._offset
            marker = 1
            self._set_last()
        elif self._offset > 2:
            self._set_next()
        self._offset += next_size
        return marker, self._to_bytes() + self._sample[self._offset-next_size:self._offset]

    def __iter__(self):
        return self

    @abc.abstractmethod
    def _set_next(self):
        """Marks FU packet as not first"""

    @abc.abstractmethod
    def _set_last(self):
        """Marks FU packet as last"""

    @abc.abstractmethod
    def _to_bytes(self):
        """Returns FU header as bytestream, ready to be sent to socket."""


class AvcFragmentMaker(FragmentMaker):  # pylint: disable=too-few-public-methods
    """Fragments AVC data on Fragmented Units rfc6184"""
    def __init__(self, sample, chunk_size=1472):
        super().__init__(sample, 1, chunk_size)
        self._indicator = (sample[0] & 0xe0) | 28
        self._header = 0x80 | (sample[0] & 0x1f)

    def _set_next(self):
        """Marks AVC FU packet as not first"""
        self._header &= 0x1f

    def _set_last(self):
        """Marks AVC FU packet as last"""
        self._header = 0x40 | (self._header & 0x1f)

    def _to_bytes(self):
        """Returns AVC FU header as bytestream, ready to be sent to socket."""
        return self._indicator.to_bytes(1, 'big') + self._header.to_bytes(1, 'big')


class HevcFragmentMaker(FragmentMaker):  # pylint: disable=too-few-public-methods
    """Fragments HEVC data on Fragmented Units rfc7798"""
    def __init__(self, sample, chunk_size=1472):
        super().__init__(sample, 2, chunk_size)
        self._type = (sample[0] >> 1) & 0x3f
        self._indicator = bytes([(sample[0] & 0x81) | (0x31 << 1), sample[1]])
        self._header = 0x80 | self._type

    def _set_next(self):
        """Marks HEVC FU packet as not first"""
        self._header = self._type

    def _set_last(self):
        """Marks HEVC FU packet as last"""
        self._header = 0x40 | self._type

    def _to_bytes(self):
        """Returns HEVC FU header as bytestream, ready to be sent to socket."""
        return self._indicator + self._header.to_bytes(1, 'big')


class TrickPlay:
    """Parameters of trick play mode"""
    def __init__(self, applicable=False):
        self.scale = 1
        self._applicable = applicable

    @property
    def scale(self):
        """Returns current scale value"""
        return abs(self._scale)

    @scale.setter
    def scale(self, value):
        """Sets current scale value"""
        self._scale = value

    @property
    def forward(self):
        """Returns if direction is forward"""
        return self._scale > 0

    @property
    def active(self):
        """Verifies if play is in trick mode"""
        return self._scale != 1

    @property
    def applicable(self):
        """Verifies if trick mode can be applied to the stream"""
        return self._applicable


class Streamer:
    """Streams media data in RTP interleaved protocol"""
    def __init__(self, payload_type, trick_play=TrickPlay()):
        self._last_frame_time_sec, self._frame_duration_sec = 0., 0.
        self._position = 0.
        self._rtp_header = None
        self._decoding_time = random.randint(0, 0xffffffff)
        self._payload_type = payload_type
        self.trick_play = trick_play

    def prev_frame(self, reader, track_id, start_time, verbal):
        """Reads and returns previous frame from mp4 file"""
        if self._rtp_header is None or self._position <= start_time:
            return b''
        return self._frame(reader, track_id, verbal)

    def next_frame(self, reader, track_id, end_time, verbal):
        """Reads and returns next frame from mp4 file"""
        if not self._rtp_header or self._position >= end_time:
            return b''
        return self._frame(reader, track_id, verbal)

    def to_bytes(self, marker, chunk, composition_time, verbal):
        """Returns chunk as bytestream, ready to be sent to socket"""
        ret = self._rtp_header.to_bytes(marker,
                                        composition_time,
                                        len(chunk)) + \
            chunk
        if verbal:
            print(' '.join(map(lambda x, p=ret: '{:02x}'.format(p[x]), range(19))) +
                  ' of ' + str(len(ret)))
        return ret

    def set_transport(self, transport):
        """Sets streamer stream transport"""
        self._rtp_header = \
            InterleavedHeader(self._payload_type,
                              int(transport.split('interleaved=')[-1].split('-')[0]),
                              random.randint(0, 0xffffffff))

    def is_nth_frame_in_group(self, group_size):
        """Returns frame number in a group of frames"""
        if self._rtp_header is not None:
            return self._rtp_header.sequence_number % group_size
        raise UnboundLocalError('Transport is None')

    @property
    def position(self):
        """Returns current position as duration of all written frames"""
        return self._position

    @position.setter
    def position(self, value):
        """Sets current position as duration of all written frames"""
        self._position = value

    @abc.abstractmethod
    def _frame_to_bytes(self, sample, composition_time, verbal) -> bytes:
        """Returns media sample as bytestream, ready to be sent to socket"""
        return b''

    def _frame(self, reader, track_id, verbal):
        ret = b''
        if self.trick_play.active and not self.trick_play.applicable:
            return ret
        current_time = time.time()
        if current_time - self._last_frame_time_sec >= \
                self._frame_duration_sec / self.trick_play.scale:
            timescale = reader.media_header[track_id].timescale
            timescale_multiplier = reader.samples_info[track_id].timescale_multiplier
            sample = reader.next_sample(track_id, self.trick_play.forward)
            if verbal:
                logging.info(str(sample))
            if self.trick_play.forward:
                self._position += self._frame_duration_sec
            else:
                self._position -= self._frame_duration_sec
            self._frame_duration_sec = sample.duration / timescale
            composition_time = self._decoding_time
            if sample.composition_time is not None:
                composition_time += sample.composition_time * timescale_multiplier
            self._decoding_time += sample.duration * timescale_multiplier
            self._last_frame_time_sec = current_time
            if self.trick_play.active and not self.trick_play.forward:
                if not reader.is_keyframe(sample):
                    return ret
            ret = self._frame_to_bytes(sample,
                                       composition_time >> (self.trick_play.scale - 1),
                                       verbal)
        return ret


class AvcStreamer(Streamer):
    """Streams video data in RTP interleaved protocol"""
    def __init__(self, payload_type, param_sets=()):
        super().__init__(payload_type, TrickPlay(True))
        self.param_sets = param_sets

    def _frame_to_bytes(self, sample, composition_time, verbal):
        """Returns video sample as bytestream, ready to be sent to socket"""
        ret = b''
        for chunk in sample:
            for marker, data_unit in AvcFragmentMaker(chunk):
                ret += self.to_bytes(marker, data_unit, composition_time, verbal)
        return ret


class HevcStreamer(Streamer):
    """Streams video data in RTP interleaved protocol"""
    def __init__(self, payload_type, param_sets=()):
        super().__init__(payload_type, TrickPlay(True))
        self.param_sets = param_sets

    def _frame_to_bytes(self, sample, composition_time, verbal):
        """Returns video sample as bytestream, ready to be sent to socket"""
        ret = b''
        for chunk in sample:
            for marker, data_unit in HevcFragmentMaker(chunk):
                ret += self.to_bytes(marker, data_unit, composition_time, verbal)
        return ret


class AudioStreamer(Streamer):
    """Streams audio data in RTP interleaved protocol"""
    def _frame_to_bytes(self, sample, composition_time, verbal):
        """Returns audio sample as bytestream, ready to be sent to socket"""
        ret = b''
        for chunk in sample:
            data_unit = AUHeaderSimpleSection(0, len(chunk)).to_bytes() + chunk
            ret += self.to_bytes(1, data_unit, composition_time, verbal)
        return ret
