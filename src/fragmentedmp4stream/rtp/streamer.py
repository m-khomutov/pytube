"""RTP interleaved protocol entities"""
import time
import random
import logging


class Header:
    """RTP (+interleaved) header according to rfc7826"""
    _first_byte = bytes([0x80])
    _sequence_number = 0

    def __init__(self, payload_type, channel, synchro_source):
        self._payload_type = payload_type
        self._interleaved_sign = bytes([0x24, channel])
        self._synchro_source = synchro_source.to_bytes(4, 'big')

    @property
    def synchronization_source(self):
        """Returns synchronization source identifier"""
        return self._synchro_source

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
    def __init__(self, sample, chunk_size=1472):
        self._sample = sample
        self._offset = 1
        self._chunk_size = chunk_size
        self._indicator = (sample[0] & 0xe0) | 28
        self._header = 0x80 | (sample[0] & 0x1f)

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
            self._header = 0x40 | (self._header & 0x1f)
        elif self._offset > 1:
            self._header &= 0x1f
        self._offset += next_size
        return marker, \
            self._indicator.to_bytes(1, 'big') + \
            self._header.to_bytes(1, 'big') +\
            self._sample[self._offset-next_size:self._offset]

    def __iter__(self):
        return self


class Streamer:
    """Streams media data in RTP interleaved protocol"""
    _last_frame_time_ms, _frame_duration_ms = 0, 0
    _duration_error = 0.

    def __init__(self, reader, verbal):
        self._verbal = verbal
        self._timestamp = random.randint(0, 0xffffffff)
        self._reader = reader
        if self._verbal:
            logging.info(self._reader)
        self._rtp_header = Header(96, 0, random.randint(0, 0xffffffff))

    def next_frame(self):
        """Reads and returns next frame from mp4 file"""
        ret = b''
        current_time_ms = int(round(time.time() * 1000))
        if current_time_ms - self._last_frame_time_ms >= self._frame_duration_ms:
            track_id = 1
            timescale = self._reader.timescale[track_id]
            sample = self._reader.next_sample(track_id)
            if self._verbal:
                print(str(sample))
            for chunk in sample:
                for marker, data_unit in FragmentMaker(chunk):
                    packet = self._rtp_header.to_bytes(marker,
                                                       self._timestamp,
                                                       len(data_unit)) + \
                           data_unit
                    if self._verbal:
                        print(' '.join(map(lambda x, p=packet: '{:02x}'.format(p[x]), range(19))))
                    ret += packet
            self._frame_duration_ms = int(sample.duration * 1000 / timescale)
            self._duration_error += (sample.duration * 1000 / timescale) - self._frame_duration_ms
            if self._duration_error > 1:
                self._frame_duration_ms += int(self._duration_error)
                self._duration_error -= int(self._duration_error)
            self._timestamp += self._frame_duration_ms
            self._last_frame_time_ms = current_time_ms
        return ret

    @property
    def reader(self):
        """Returns mp4 file reader"""
        return self._reader
