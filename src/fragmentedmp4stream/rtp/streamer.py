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
    _sequence_number = 0

    def __init__(self, payload_type, channel, synchro_source):
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
            self._first_byte + \
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
    _scale = 1
    _backward = False

    def off(self):
        """Verifies if play is in trick mode"""
        return self._scale == 1

    def tweak(self, value):
        """Corrects value according to trick play mode"""
        return self._scale * value


class Streamer:
    """Streams media data in RTP interleaved protocol"""
    _last_frame_time_sec, _frame_duration_sec = 0., 0.
    _position = 0.
    _rtp_header = None
    _decoding_time = random.randint(0, 0xffffffff)

    def __init__(self, payload_type):
        self._payload_type = payload_type
        self._trick_play = TrickPlay()

    def next_frame(self, reader, track_id, end_time, verbal):
        """Reads and returns next frame from mp4 file"""
        ret = b''
        if self._rtp_header is None or self._position >= end_time:
            return ret
        current_time = time.time()
        if current_time - self._last_frame_time_sec >= \
                self._trick_play.tweak(self._frame_duration_sec):
            timescale = reader.media_header[track_id].timescale
            timescale_multiplier = reader.samples_info[track_id].timescale_multiplier
            sample = reader.next_sample(track_id)
            if verbal:
                logging.info(str(sample))
            self._position += self._frame_duration_sec
            self._frame_duration_sec = sample.duration / timescale
            composition_time = self._decoding_time
            if sample.composition_time is not None:
                composition_time += sample.composition_time * timescale_multiplier
            ret = self._frame_to_bytes(sample, self._trick_play.tweak(composition_time), verbal)
            self._decoding_time += sample.duration * timescale_multiplier
            self._last_frame_time_sec = current_time
        return ret

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


class AvcStreamer(Streamer):
    """Streams video data in RTP interleaved protocol"""
    def __init__(self, payload_type, param_sets=()):
        super().__init__(payload_type)
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
        super().__init__(payload_type)
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
