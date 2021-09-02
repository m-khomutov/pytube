"""Prepares media streaming in HLS format"""
import os
import logging
import platform
import math
from .reader import Reader
from .writer import Writer
from .atom import mdat


class Segment:
    """HLS segment instance"""
    def __init__(self, sequence_number, duration):
        self.moof = []
        self._sequence_number = sequence_number
        self._duration = duration

    @property
    def sequence_number(self):
        """Returns segment sequence number"""
        return self._sequence_number

    @property
    def duration(self):
        """Return segment duration"""
        return self._duration

    @duration.setter
    def duration(self, value):
        """Sets segment duration"""
        self._duration = value

    def to_bytes(self):
        """Returns segment as bytestream, ready to be sent to socket"""
        ret = bytes()
        for moof in self.moof:
            ret += moof.to_bytes()


class SegmentMaker:
    """Prepares stream as a set of segments"""
    def __init__(self, filename, path, server_address, **kwargs):
        self._filename = filename
        self.segment_url = 'http://'+platform.node()+':'+str(server_address[1])+path
        self._segment_duration = kwargs.get('segment_duration', 6.)
        self.media_segments = []
        if os.path.isfile(self._filename+'.cache'):
            self._read_cache()
        self.reader = Reader(filename)
        verbal = kwargs.get('verbal', False)
        if verbal:
            logging.info(self.reader)
        self._prepare_playlist()

    def media_playlist(self):
        """Returns prepared HLS playlist"""
        return self._media_playlist

    def init(self):
        """Returns prepared MP4 metadata boxes"""
        return self.writer.initializer

    def segment(self, index):
        """Return prepared indexed segment"""
        if index >= len(self.media_segments):
            raise ValueError
        ret = bytes()
        for moof in self.media_segments[index].moof:
            ret += moof.to_bytes()
            mdat_box = mdat.Box(type='mdat')
            trun_box = moof.find_inner_boxes('trun')
            for trun in trun_box:
                for sample in trun.samples:
                    mdat_box.append(self.reader.sample(sample.initial_offset, sample.fields[1]))
            ret += mdat_box.to_bytes()
        return ret

    def _prepare_playlist(self):
        self.writer = Writer(self.reader)
        segment = Segment(0, .0)
        target_duration = .0
        while True:
            try:
                moof_box, mdat_box, duration = self.writer.fragment_moof()
                if mdat_box.size > 0:
                    segment.moof.append(moof_box)
                    segment.duration += duration
                    if segment.duration > self._segment_duration or self.writer.last_chunk is True:
                        if target_duration < segment.duration:
                            target_duration = segment.duration
                        self.media_segments.append(segment)
                        segment = Segment(segment.sequence_number + 1, .0)
                if self.writer.last_chunk:
                    break
            except StopIteration:
                break
        self._media_playlist = '#EXTM3U\n' \
            '#EXT-X-TARGETDURATION:'+str(math.ceil(target_duration)) + \
            '\n#EXT-X-PLAYLIST-TYPE:VOD\n' + \
            '#EXT-X-MAP:URI='+self.segment_url+'_init.mp4\n'
        for segment in self.media_segments:
            self._media_playlist +=\
                '#EXTINF:' + "{:.3f}".format(segment.duration) + '\n' + \
                self.segment_url + '_sn' + str(segment.sequence_number) + '.m4s\n'
        self._media_playlist += '#EXT-X-ENDLIST\n'

    def _cache(self):
        with open(self._filename+'.cache', 'wb') as file:
            file.write(self.writer.initializer)
            for segment in self.media_segments:
                file.write(segment.to_bytes())
            file.close()

    def _read_cache(self):
        Reader(self._filename+'.cache')
