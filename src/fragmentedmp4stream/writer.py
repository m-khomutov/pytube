from .atom.atom import Box, FullBox
from .atom import trex, stco, stsc, mfhd, stts, stsd, mdat, trun, tfhd, stsz, hvcc
from .reader import FragmentationFinished


class Writer:
    def __init__(self, reader):
        self.last_chunk = False
        self._sequence_number = 0
        self.reader = reader
        self._set_ftyp()
        self._set_moov()

    def init(self):
        return self.ftyp.to_bytes() + self.moov.to_bytes()

    def fragment(self):
        if self.last_chunk:
            raise FragmentationFinished("done")
        self._set_moof()
        self.moof.find_inner_boxes('mfhd')[0].sequence_number = self._sequence_number
        self._sequence_number += 1
        ret = self.moof.to_bytes() + self.mdat.to_bytes()
        return ret

    def fragment_moof(self):
        if self.last_chunk == True:
            raise FragmentationFinished("done")
        self._set_moof()
        self.moof.find_inner_boxes('mfhd')[0].sequence_number = self._sequence_number
        self._sequence_number += 1
        return self.moof
    def _set_ftyp(self):
        ftyp = self.reader.find('ftyp')
        if len(ftyp) != 1:
            raise SyntaxError( "ftyp is not found" )
        self.ftyp = ftyp[0]
        self.base_offset = self.ftyp.full_size()
    def _set_moov(self):
        self.moov = Box(type='moov')
        self.moov.add_inner_box(self.reader.find('mvhd')[0])
        self.trakmap = {}
        self.sttsmap = {}
        self.first_vframe = trun.Frame()
        itrak = self.reader.find('trak')
        for tr in itrak:
            otrak = Box(type='trak')
            tkhd = tr.find_inner_boxes('tkhd')[0]
            otrak.add_inner_box(tkhd)
            otrak.add_inner_box(Box(type='mdia'))
            otrak.add_inner_box(tr.find_inner_boxes('mdhd')[0], 'mdia')
            hdlr = tr.find_inner_boxes('hdlr')[0]
            self.trakmap[tkhd.track_id] = hdlr.handler_type
            self.sttsmap[tkhd.track_id] = tr.find_inner_boxes('stts')[0]
            otrak.add_inner_box(hdlr, 'mdia')
            otrak.add_inner_box(Box(type='minf'), 'mdia')
            if hdlr.handler_type == 'vide':
                otrak.add_inner_box(tr.find_inner_boxes('vmhd')[0], 'minf')
            elif hdlr.handler_type == 'soun':
                otrak.add_inner_box(tr.find_inner_boxes('smhd')[0], 'minf')
            elif hdlr.handler_type == 'text':
                otrak.add_inner_box(FullBox(type='nmhd'), 'minf')
            otrak.add_inner_box(Box(type='dinf'), 'minf')
            otrak.add_inner_box(tr.find_inner_boxes('dref')[0], 'dinf')
            otrak.add_inner_box(Box(type='stbl'), 'minf')
            otrak.add_inner_box(stts.Box(), 'stbl')
            stsd=tr.find_inner_boxes('stsd')
            if len(stsd) > 0:
                stsd[0].normalize()
                otrak.add_inner_box(stsd[0], 'stbl')
            otrak.add_inner_box(stsz.Box(), 'stbl')
            otrak.add_inner_box(stsc.Box(), 'stbl')
            otrak.add_inner_box(stco.Box(), 'stbl')
            self.moov.add_inner_box(otrak)
        self.moov.add_inner_box(Box(type='mvex'))
        for id in self.trakmap.keys():
            self.moov.add_inner_box(trex.Box(track_id=id), 'mvex')
        self.base_offset += self.moov.full_size()
    def _set_moof(self):
        self.moof=Box(type='moof')
        self.moof.add_inner_box(mfhd.Box())
        tf_flags = tfhd.Flags.BASE_DATA_OFFSET_PRESENT |\
                   tfhd.Flags.DEFAULT_SAMPLE_DURATION_PRESENT |\
                   tfhd.Flags.DEFAULT_SAMPLE_FLAGS_PRESENT
        trun_boxes = {}
        mdat_size = {}
        for id in self.trakmap.keys():
            traf = Box(type='traf')
            self.moof.add_inner_box(traf)
            sample_flags = trex.SampleFlags(1, True)
            tr_flags = trun.Flags.DATA_OFFSET | trun.Flags.FIRST_SAMPLE_FLAGS | trun.Flags.SAMPLE_SIZE
            if self.trakmap[id] == 'vide':
                if self.reader.hasCT(id):
                    tr_flags |= trun.Flags.SAMPLE_COMPOSITION_TIME_OFFSETS
            elif self.trakmap[id] == 'soun':
                sample_flags = trex.SampleFlags(2, False)
                tr_flags = trun.Flags.DATA_OFFSET | trun.Flags.SAMPLE_DURATION | trun.Flags.SAMPLE_SIZE
            elif self.trakmap[id] == 'text':
                tf_flags = tfhd.Flags.BASE_DATA_OFFSET_PRESENT
                tr_flags = trun.Flags.DATA_OFFSET | trun.Flags.SAMPLE_SIZE | trun.Flags.SAMPLE_DURATION
                sample_flags = trex.SampleFlags(0, False)
            traf.add_inner_box(tfhd.Box(flags=tf_flags,
                                        track_id=id,
                                        data_offset=self.base_offset,
                                        default_sample_duration=self.sttsmap[id].entries[0].delta,
                                        default_sample_flags=int(sample_flags)))
            first_sample_flags = trex.SampleFlags(2, False)
            trun_boxes[id] = trun.Box(flags=tr_flags, first_sample_flags=int(first_sample_flags))
            traf.add_inner_box(trun_boxes[id])
            if self.trakmap[id] == 'vide':
                mdat_size[id]=self._set_video_chunk(id, trun_boxes[id])
            elif self.trakmap[id] == 'soun':
                mdat_size[id]=self._set_audio_sample(id, trun_boxes[id])
            else:
                mdat_size[id]=self._set_text_sample(id, trun_boxes[id])
        trun_data_offset = self.moof.full_size() + 8
        for id in trun_boxes.keys():
            trun_boxes[id].data_offset = trun_data_offset
            trun_data_offset += mdat_size[id]
        self.base_offset += self.moof.full_size() + self.mdat.size
    def _set_video_chunk(self, trakid, trun_box):
        self.mdat = mdat.Box(type='mdat')
        self.chunk_duration = 0
        vsize = 0
        if self.first_vframe.size > 0:
            if self.first_vframe.composition_time != None:
                trun_box.add_sample(size=self.first_vframe.size, time_offsets=self.first_vframe.composition_time, initial_offset=self.first_vframe.offset)
            else:
                trun_box.add_sample(size=self.first_vframe.size, initial_offset=self.first_vframe.offset)
            self.mdat.append(self.first_vframe.data)
            vsize += self.first_vframe.size
        while True:
            try:
                vframe = self.reader.nextSample(trakid)
                if len(vframe.data) == vframe.size:
                    if self._keyframe(vframe.data) and not self.mdat.empty():
                        self.first_vframe = vframe
                        self.chunk_duration /= self.reader.timescale[trakid]
                        break
                    if vframe.composition_time != None:
                        trun_box.add_sample(size=vframe.size, time_offsets=vframe.composition_time, initial_offset=vframe.offset)
                    else:
                        trun_box.add_sample(size=vframe.size, initial_offset=vframe.offset)
                    self.mdat.append(vframe.data)
                    self.chunk_duration += vframe.duration
                    vsize += vframe.size
            except:
                self.chunk_duration /= self.reader.timescale[trakid]
                self.last_chunk = True
                break
        return vsize
    def _set_audio_sample(self, trakid, trun_box):
        asize = 0
        duration = 0
        while duration < self.chunk_duration:
            try:
                sample = self.reader.nextSample(trakid)
                if self.last_chunk == False:
                    duration += sample.duration / self.reader.timescale[trakid]
                trun_box.add_sample(size=sample.size, duration=sample.duration, initial_offset=sample.offset)
                self.mdat.append(sample.data)
                asize += sample.size
            except:
                break
        return asize
    def _set_text_sample(self, trakid, trun_box):
        size = 0
        duration = 0
        while duration < self.chunk_duration:
            try:
                sample = self.reader.nextSample(trakid)
                if self.last_chunk == False:
                    duration += sample.duration / self.reader.timescale[trakid]
                trun_box.add_sample(size=sample.size, duration=sample.duration, initial_offset=sample.offset)
                self.mdat.append(sample.data)
                size += sample.size
            except:
                trun_box.add_sample(size=2,duration=int(self.chunk_duration*self.reader.timescale[trakid]))
                self.mdat.append(int(0).to_bytes(2, 'big'))
                size=2
                break
        return size

    def _keyframe(self, frame):
        if self.reader.vstream_type == stsd.VideoCodecType.AVC:
            return frame[4] & 0x1f != 1
        elif self.reader.vstream_type == stsd.VideoCodecType.HEVC:
            return hvcc.NetworkUnitHeader(frame[4:6]).keyframe()
        raise TypeError
