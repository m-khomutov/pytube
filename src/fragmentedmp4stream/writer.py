"""generates fragmented MP4 format"""
from .atom.atom import Box, FullBox
from .atom import trex, stco, stsc, mfhd, stts, stsd, mdat, trun, tfhd, stsz, hvcc


class Writer:
    """Fragmented MP4 format generator"""
    def __init__(self, reader):
        self.last_chunk = False
        self._sequence_number = 0
        self._reader = reader
        self._initializer = self._set_ftyp() + self._set_moov()
        self.first_video_frame = trun.Frame()

    @property
    def initializer(self):
        """Returns meta fragmented MP4 atoms"""
        return self._initializer

    def fragment_moof(self):
        """Returns moof box with next fragment"""
        if self.last_chunk:
            raise StopIteration from None
        return self._set_moof()

    def __next__(self):
        moof_box, mdat_box, duration = self.fragment_moof()
        return moof_box.to_bytes() + mdat_box.to_bytes(), duration

    def __iter__(self):
        return self

    def _set_ftyp(self):
        """get ftyp atom from MP4 reader"""
        try:
            ftyp = self._reader.find_box('ftyp')[0]
        except IndexError as index_error:
            raise SyntaxError("ftyp is not found") from index_error
        self.base_offset = ftyp.full_size()
        return ftyp.to_bytes()

    def _set_moov(self):
        """get moov atom from MP4 reader"""
        moov = Box(type='moov')
        moov.add_inner_box(self._reader.find_box('mvhd')[0])
        self._stts_params = {}  # (track_id, hdlr, stts)
        stts_params_key = 1
        for track in self._reader.find_box('trak'):
            track_box = Box(type='trak')
            tkhd = track.find_inner_boxes('tkhd')[0]
            track_box.add_inner_box(tkhd)
            track_box.add_inner_box(Box(type='mdia'))
            track_box.add_inner_box(track.find_inner_boxes('mdhd')[0], 'mdia')
            hdlr = track.find_inner_boxes('hdlr')[0]
            if hdlr.handler_type == 'vide':  # should go first - to calculate chunk duration
                self._stts_params[0] = (tkhd.track_id,
                                        hdlr.handler_type,
                                        track.find_inner_boxes('stts')[0])
            elif hdlr.handler_type == 'soun' or hdlr.handler_type == 'text':
                self._stts_params[stts_params_key] = (tkhd.track_id,
                                                      hdlr.handler_type,
                                                      track.find_inner_boxes('stts')[0])
                stts_params_key += 1
            track_box.add_inner_box(hdlr, 'mdia')
            track_box.add_inner_box(Box(type='minf'), 'mdia')
            if hdlr.handler_type == 'vide':
                track_box.add_inner_box(track.find_inner_boxes('vmhd')[0], 'minf')
            elif hdlr.handler_type == 'soun':
                track_box.add_inner_box(track.find_inner_boxes('smhd')[0], 'minf')
            elif hdlr.handler_type == 'text':
                track_box.add_inner_box(FullBox(type='nmhd'), 'minf')
            track_box.add_inner_box(Box(type='dinf'), 'minf')
            track_box.add_inner_box(track.find_inner_boxes('dref')[0], 'dinf')
            track_box.add_inner_box(Box(type='stbl'), 'minf')
            track_box.add_inner_box(stts.Box(), 'stbl')
            stsd_box = track.find_inner_boxes('stsd')
            if stsd_box:
                stsd_box[0].normalize()
                track_box.add_inner_box(stsd_box[0], 'stbl')
            track_box.add_inner_box(stsz.Box(), 'stbl')
            track_box.add_inner_box(stsc.Box(), 'stbl')
            track_box.add_inner_box(stco.Box(), 'stbl')
            moov.add_inner_box(track_box)
        moov.add_inner_box(Box(type='mvex'))
        for key in sorted(self._stts_params.keys()):
            track_id = self._stts_params[key][0]
            moov.add_inner_box(trex.Box(track_id=track_id), 'mvex')
        self.base_offset += moov.full_size()
        return moov.to_bytes()

    def _set_moof(self):
        moof_box = Box(type='moof')
        mdat_box = mdat.Box(type='mdat')
        chunk_duration = 0
        moof_box.add_inner_box(mfhd.Box())
        tf_flags = tfhd.Flags.BASE_DATA_OFFSET_PRESENT |\
            tfhd.Flags.DEFAULT_SAMPLE_DURATION_PRESENT |\
            tfhd.Flags.DEFAULT_SAMPLE_FLAGS_PRESENT
        trun_boxes = {}
        mdat_size = {}
        for key in sorted(self._stts_params.keys()):
            track_id, hdlr, stts_box = self._stts_params[key]
            traf_box = Box(type='traf')
            moof_box.add_inner_box(traf_box)
            sample_flags = trex.SampleFlags(1, True)
            tr_flags = trun.Flags.DATA_OFFSET | \
                trun.Flags.FIRST_SAMPLE_FLAGS | \
                trun.Flags.SAMPLE_SIZE
            if hdlr == 'vide':
                if self._reader.has_composition_time(track_id):
                    tr_flags |= trun.Flags.SAMPLE_COMPOSITION_TIME_OFFSETS
            elif hdlr == 'soun':
                sample_flags = trex.SampleFlags(2, False)
                tr_flags = trun.Flags.DATA_OFFSET | \
                    trun.Flags.SAMPLE_DURATION | \
                    trun.Flags.SAMPLE_SIZE
            elif hdlr == 'text':
                tf_flags = tfhd.Flags.BASE_DATA_OFFSET_PRESENT
                tr_flags = trun.Flags.DATA_OFFSET | \
                    trun.Flags.SAMPLE_SIZE | \
                    trun.Flags.SAMPLE_DURATION
                sample_flags = trex.SampleFlags(0, False)
            traf_box.add_inner_box(
                tfhd.Box(flags=tf_flags,
                         track_id=track_id,
                         data_offset=self.base_offset,
                         default_sample_duration=stts_box.entries[0].delta,
                         default_sample_flags=int(sample_flags))
            )
            trun_boxes[track_id] = trun.Box(flags=tr_flags,
                                            first_sample_flags=int(trex.SampleFlags(2, False)))
            traf_box.add_inner_box(trun_boxes[track_id])
            if hdlr == 'vide':
                mdat_size[track_id], chunk_duration = \
                    self._set_video_chunk(track_id,
                                          trun_boxes[track_id],
                                          mdat_box)
            elif hdlr == 'soun':
                mdat_size[track_id] = self._set_audio_sample(track_id,
                                                             trun_boxes[track_id],
                                                             mdat_box,
                                                             chunk_duration)
            elif hdlr == 'text':
                mdat_size[track_id] = self._set_text_sample(track_id,
                                                            trun_boxes[track_id],
                                                            mdat_box,
                                                            chunk_duration)
        trun_data_offset = moof_box.full_size() + 8
        for track_id in trun_boxes:
            trun_boxes[track_id].data_offset = trun_data_offset
            trun_data_offset += mdat_size[track_id]
        self.base_offset += moof_box.full_size() + mdat_box.size
        moof_box.find_inner_boxes('mfhd')[0].sequence_number = self._sequence_number
        self._sequence_number += 1
        return moof_box, mdat_box, chunk_duration

    def _set_video_chunk(self, track_id, trun_box, fragment_mdat):
        chunk_duration = 0
        chunk_size = 0
        if self.first_video_frame.size > 0:
            if self.first_video_frame.composition_time is not None:
                trun_box.add_sample(size=self.first_video_frame.size,
                                    time_offsets=self.first_video_frame.composition_time,
                                    initial_offset=self.first_video_frame.offset)
            else:
                trun_box.add_sample(size=self.first_video_frame.size,
                                    initial_offset=self.first_video_frame.offset)
            fragment_mdat.append(self.first_video_frame.data)
            chunk_size += self.first_video_frame.size
        while True:
            try:
                video_frame = self._reader.next_sample(track_id)
                if len(video_frame.data) == video_frame.size:
                    if self._keyframe(video_frame) and not fragment_mdat.empty():
                        self.first_video_frame = video_frame
                        chunk_duration /= self._reader.media_header[track_id].timescale
                        break
                    if video_frame.composition_time is not None:
                        trun_box.add_sample(size=video_frame.size,
                                            time_offsets=video_frame.composition_time,
                                            initial_offset=video_frame.offset)
                    else:
                        trun_box.add_sample(size=video_frame.size,
                                            initial_offset=video_frame.offset)
                    fragment_mdat.append(video_frame.data)
                    chunk_duration += video_frame.duration
                    chunk_size += video_frame.size
            except IndexError:
                chunk_duration /= self._reader.media_header[track_id].timescale
                self.last_chunk = True
                break
            except TypeError:
                pass
        return chunk_size, chunk_duration

    def _set_audio_sample(self, track_id, trun_box, fragment_mdat, chunk_duration):
        sample_size = 0
        duration = 0
        while duration < chunk_duration:
            try:
                sample = self._reader.next_sample(track_id)
                if not self.last_chunk:
                    duration += sample.duration / self._reader.media_header[track_id].timescale
                trun_box.add_sample(size=sample.size,
                                    duration=sample.duration,
                                    initial_offset=sample.offset)
                fragment_mdat.append(sample.data)
                sample_size += sample.size
            except IndexError:
                break
        return sample_size

    def _set_text_sample(self, track_id, trun_box, fragment_mdat, chunk_duration):
        size = 0
        duration = 0
        while duration < chunk_duration:
            try:
                sample = self._reader.next_sample(track_id)
                if not self.last_chunk:
                    duration += sample.duration / self._reader.media_header[track_id].timescale
                trun_box.add_sample(size=sample.size,
                                    duration=sample.duration,
                                    initial_offset=sample.offset)
                fragment_mdat.append(sample.data)
                size += sample.size
            except IndexError:
                trun_box.add_sample(
                    size=2,
                    duration=int(chunk_duration * self._reader.media_header[track_id].timescale)
                )
                fragment_mdat.append(int(0).to_bytes(2, 'big'))
                size = 2
                break
        return size

    def _keyframe(self, frame):
        for chunk in frame:
            if self._reader.video_stream_type == stsd.VideoCodecType.AVC:
                if chunk[0] & 0x1f == 5:
                    return True
                if chunk[0] & 0x1f == 1:
                    return False
            if self._reader.video_stream_type == stsd.VideoCodecType.HEVC:
                return hvcc.NetworkUnitHeader(chunk[:2]).keyframe()
        raise TypeError
