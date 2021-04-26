from .reader import Reader
from .writer import Writer
from .atom import mdat
import logging
import platform
import math

class Segment:
    def __init__(self, seqnum, duration):
        self.moof=[]
        self.data=[]
        self.seqnum=seqnum
        self.duration=duration

class Segmenter:
    def __init__(self, filename, path, server_address, verbal):
        self._filename=filename
        self.segment_url='http://'+platform.node()+':'+str(server_address[1])+path;
        self.media_segments={}
        self.reader=Reader(filename)
        if verbal:
            logging.info(self.reader)
        self._prepare_playlist()
        pass
    def playlist(self):
        return self._playlist
    def init(self):
        return self.writer.init()
    def segment(self, index):
        if index >= len(self.media_segments):
            raise ValueError
        ret=bytes()
        for i in range(len(self.media_segments[index].moof)):
            ret += self.media_segments[index].moof[i]
            mdat_box = mdat.Box(type='mdat')
            for dt in self.media_segments[index].data[i]:
                mdat_box.append(self.reader.sample(dt.offset, dt.size))
            ret += mdat_box.encode()
        return ret
    def _prepare_playlist(self):
        self.writer = Writer(self.reader)
        segment=Segment(seqnum=0, duration=.0)
        targetduration=.0
        while True:
            try:
                segment.moof.append(self.writer.fragment_moof())
                segment.data.append(self.writer.fragment_data)
                segment.duration += self.writer.chunk_duration
                if segment.duration > 6 or self.writer.last_chunk == True:
                    if targetduration < segment.duration:
                        targetduration = segment.duration
                    self.media_segments[segment.seqnum] = segment
                    segment=Segment(seqnum=segment.seqnum+1,duration=.0)
                if self.writer.last_chunk:
                    break
            except:
                break
        self._playlist='#EXTM3U\n' \
                       '#EXT-X-TARGETDURATION:'+str(math.ceil(targetduration))+\
                       '\n#EXT-X-PLAYLIST-TYPE:VOD\n'+\
                       '#EXT-X-MAP:URI='+self.segment_url+'_init.mp4\n'
        for key in self.media_segments.keys():
            self._playlist += '#EXTINF:'+"{:.3f}".format(self.media_segments[key].duration)+'\n'+\
                              self.segment_url+'_sn'+str(self.media_segments[key].seqnum)+'.m4s\n'
        self._playlist += '#EXT-X-ENDLIST\n'