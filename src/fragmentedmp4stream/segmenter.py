from .reader import Reader
from .writer import Writer
from .atom import mdat
import os
import logging
import platform
import math

class Segment:
    def __init__(self, seqnum, duration):
        self.moof=[]
        self.seqnum=seqnum
        self.duration=duration

class Segmenter:
    def __init__(self, filename, path, server_address, segment_duration, save_to_cache, verbal):
        self._filename=filename
        self.segment_url='http://'+platform.node()+':'+str(server_address[1])+path;
        self._segment_duration = segment_duration
        self._save_to_cache = save_to_cache
        self.media_segments=[]
        if os.path.isfile(self._filename+'.cache'):
            self._readcache()
        self.reader=Reader(filename)
        if verbal:
            logging.info(self.reader)
        self._prepare_playlist()
    def media_playlist(self):
        return self._media_playlist
    def init(self):
        return self.writer.init()
    def segment(self, index):
        if index >= len(self.media_segments):
            raise ValueError
        ret=bytes()
        for i in range(len(self.media_segments[index].moof)):
            ret += self.media_segments[index].moof[i].encode()
            mdat_box = mdat.Box(type='mdat')
            trun=self.media_segments[index].moof[i].find('trun')
            for tr in trun:
                for sample in tr.samples:
                    mdat_box.append(self.reader.sample(sample.initial_offset, sample.size))
            ret += mdat_box.encode()
        return ret

    def _prepare_playlist(self):
        self.writer = Writer(self.reader)
        segment=Segment(seqnum=0, duration=.0)
        targetduration=.0
        while True:
            try:
                segment.moof.append(self.writer.fragment_moof())
                segment.duration += self.writer.chunk_duration
                if segment.duration > self._segment_duration or self.writer.last_chunk == True:
                    if targetduration < segment.duration:
                        targetduration = segment.duration
                    self.media_segments.append(segment)
                    segment=Segment(seqnum=segment.seqnum+1,duration=.0)
                if self.writer.last_chunk:
                    break
            except:
                break
        self._media_playlist='#EXTM3U\n' \
                       '#EXT-X-TARGETDURATION:'+str(math.ceil(targetduration))+\
                       '\n#EXT-X-PLAYLIST-TYPE:VOD\n'+\
                       '#EXT-X-MAP:URI='+self.segment_url+'_init.mp4\n'
        for segment in self.media_segments:
            self._media_playlist += '#EXTINF:'+"{:.3f}".format(segment.duration)+'\n'+\
                              self.segment_url+'_sn'+str(segment.seqnum)+'.m4s\n'
        self._media_playlist += '#EXT-X-ENDLIST\n'
        if self._save_to_cache:
            self._cache()
    def _cache(self):
        with open(self._filename+'.cache', 'wb') as f:
            f.write(self.writer.init())
            for segment in self.media_segments:
                for i in range(len(segment.moof)):
                    f.write(segment.moof[i].encode())
            f.close()
    def _readcache(self):
        r=Reader(self._filename+'.cache')