"""Network RTSP service session"""
import random
import string
import logging
from datetime import datetime
from ..reader import Reader
from ..rtp.streamer import AvcStreamer, HevcStreamer, AudioStreamer
from ..atom.hvcc import NetworkUnitType


class PlayRange:
    """Parameters of trick play mode"""

    def __init__(self, track_id, duration):
        self.track_id = track_id
        self._duration = duration
        self._start_clock = datetime.now().timestamp() - int(duration) - 1
        self.npt_range = [0., duration]

    @property
    def npt(self):
        """Returns play range as npt"""
        return 'npt={:.03f}-{:.03f}\r\n'.format(self.npt_range[0], self.npt_range[1])

    @npt.setter
    def npt(self, value):
        """Sets play range as npt"""
        start, end = value
        self.npt_range = [float(start) if start else 0.,
                          float(end) if end else self._duration]
        self._duration = self.npt_range[1] - self.npt_range[0]

    @property
    def clock(self):
        """Returns media duration in Clock format"""
        fraction = int((self._duration - int(self._duration)) * 1000)
        start = self._start_clock + self.npt_range[0]
        end = self._start_clock + self.npt_range[1]
        ret = 'clock=' + \
            datetime.fromtimestamp(start).strftime('%Y%m%dT%H%M%SZ-') + \
            datetime.fromtimestamp(end).strftime('%Y%m%dT%H%M%S') + \
            ('.' + str(fraction) if fraction else '') + 'Z\r\n'
        return ret

    @clock.setter
    def clock(self, value):
        """Sets play range as npt"""
        start, end = value
        if start:
            start_ts = datetime.strptime(start, "%Y%m%dT%H%M%SZ").timestamp()
            if self._start_clock > start_ts:
                self._start_clock = start_ts
            self.npt_range[0] = start_ts - self._start_clock
        if end:
            pos = end.find('.')
            if pos != -1:
                end = end[:pos] + 'Z'
            self.npt_range[1] = \
                datetime.strptime(end, "%Y%m%dT%H%M%SZ").timestamp() \
                - self._start_clock
        self._duration = self.npt_range[1] - self.npt_range[0]

    def clock_position(self, offset):
        """Returns position in media stream in Clock format"""
        position = self._start_clock + offset
        return 'clock=' + \
               datetime.fromtimestamp(position).strftime('%Y%m%dT%H%M%SZ-\r\n')


class Session:
    """RTSP Session parameters"""
    def __init__(self, content_base, filename, verbal):
        self._session_id = ''
        self._streamers = {}
        self._sdp = ''
        self._play_range = None
        self._content_base = content_base if content_base.endswith('/') else content_base + '/'
        self._reader = Reader(filename)
        self._verbal = verbal
        if self._verbal:
            logging.info(self._reader)
        for box in self._reader.find_box('trak'):
            track_id = box.find_inner_boxes('tkhd')[0].track_id
            box = box.find_inner_boxes('stsd')[0]
            if box.handler == 'vide':
                self._sdp += self._make_video_sdp(track_id, box.entries)
            elif box.handler == 'soun':
                self._sdp += self._make_audio_sdp(track_id, box.entries)

    def add_stream(self, headers):
        """Adds a controlled stream"""
        stream = int(headers[0].split()[1].split('/')[-1])
        transport = ''
        streamer = self._streamers.get(stream, None)
        if streamer is not None:
            transport = [k for k in headers if 'Transport: ' in k][0]
            streamer.set_transport(transport)
        return transport

    def valid_request(self, headers):
        """Verifies content and session identity"""
        content = headers[0].split()[1]
        return content == self._content_base and self.valid_session(headers)

    def valid_session(self, headers):
        """Verifies session identity"""
        session_id = [k for k in headers if 'Session: ' in k][0][9:]
        return session_id == self._session_id

    def get_next_frame(self):
        """If time has come writes next media frame"""
        ret = b''
        for key in self._streamers:
            if self._streamers[key].trick_play.forward:
                ret += self._streamers[key].next_frame(self._reader,
                                                       key,
                                                       self._play_range.npt_range[1],
                                                       self._verbal)
            else:
                ret += self._streamers[key].prev_frame(self._reader,
                                                       key,
                                                       self._play_range.npt_range[0],
                                                       self._verbal)
        return ret

    def set_play_range(self, headers, scale):
        """Returns media duration in Clock or NPT format"""
        ret = ''
        play_range = [x for x in headers if 'Range: ' in x]
        if play_range:
            values = play_range[0].split('=')
            if values[0][-3:] == 'npt':
                ret = self._set_play_range_as_npt(values[1])
            elif values[0][-5:] == 'clock':
                ret = self._set_play_range_as_clock(values[1])
            self._set_position(scale)
        return ret

    def set_scale(self, scale):
        """Sets playing media scale. Returns scale as Header"""
        if scale != 0:
            for key in self._streamers:
                self._streamers[key].trick_play.scale = scale
            return 'Scale: ' + str(scale) + '\r\n'
        return ''

    def position_absolute_time(self):
        """Returns current position in Clock format"""
        track_id = self._play_range.track_id
        return self._play_range.clock_position(self._streamers[track_id].position)

    @property
    def content_base(self):
        """Returns content base URL"""
        return self._content_base

    def identification(self, params: str = ''):
        """Returns session identification"""
        if not self._session_id:
            source = string.ascii_letters + string.digits
            self._session_id = ''.join(map(lambda x: random.choice(source), range(16)))
        return str.encode('Session: ' + self._session_id + params + '\r\n')

    @property
    def sdp(self):
        """Returns Session Description Properties"""
        return self._sdp

    @property
    def duration(self):
        """Returns video duration"""
        return self._reader.media_duration_sec

    def _make_video_sdp(self, track_id, stsd_boxes):
        ret = ''
        if stsd_boxes:
            ret += 'm=video 0 RTP/AVP 96\r\n'
            avc_box = stsd_boxes[0]['avcC']
            if avc_box is not None:
                ret += self._make_avc_sdp(track_id, avc_box)
            else:
                hevc_box = stsd_boxes[0]['hvcC']
                if hevc_box is not None:
                    ret += self._make_hevc_sdp(track_id, hevc_box)
        return ret

    def _make_avc_sdp(self, track_id, avc_box):
        self._streamers[track_id] = AvcStreamer(96, (avc_box.sps, avc_box.pps))
        self._play_range = PlayRange(track_id, self._reader.media_duration_sec)
        ret = 'a=rtpmap:96 H264/90000\r\n' + \
              'a=fmtp:96 packetization-mode=1' + \
              ';sprop-parameter-sets=' + avc_box.sprop_parameter_sets + \
              ';profile-level-id=' + \
              avc_box.profile_level_id + '\r\n' + \
              'a=range:' + self._play_range.clock
        return ret + 'a=control:' + str(track_id) + '\r\n'

    def _make_hevc_sdp(self, track_id, hevc_box):
        self._streamers[track_id] = HevcStreamer(96)
        self._play_range = PlayRange(track_id, self._reader.media_duration_sec)
        ret = 'a=rtpmap:96 H265/90000\r\na=fmtp:96 '
        for sprop_set in hevc_box.config_sets:
            if sprop_set.type.nal_unit_type == NetworkUnitType.VPS_NUT:
                ret += 'sprop-vps=' + sprop_set.base64_set + ';'
            elif sprop_set.type.nal_unit_type == NetworkUnitType.SPS_NUT.value:
                ret += 'sprop-sps=' + sprop_set.base64_set + ';'
            elif sprop_set.type.nal_unit_type == NetworkUnitType.PPS_NUT.value:
                ret += 'sprop-pps=' + sprop_set.base64_set + ';'
        return ret.rstrip(';') + '\r\na=control:' + str(track_id) + '\r\n'

    def _make_audio_sdp(self, track_id, stsd_boxes):
        ret = ''
        if stsd_boxes:
            ret += 'm=audio 0 RTP/AVP 97\r\n' + \
                   'a=rtpmap:97 ' + stsd_boxes[0].rtpmap + '\r\n' + \
                   'a=fmtp:97 profile-level-id=1;' \
                   'mode=AAC-hbr;sizelength=13;indexlength=3;indexdeltalength=3;' \
                   'config=' + stsd_boxes[0].config + '\r\n' + \
                   'a=control:' + str(track_id) + '\r\n'
            self._streamers[track_id] = AudioStreamer(97)
        return ret

    def _set_play_range_as_npt(self, values):
        """Returns media duration in NPT format"""
        self._play_range.npt = values.split('-')
        return 'Range: ' + self._play_range.npt

    def _set_play_range_as_clock(self, values):
        """Returns media duration in Clock format"""
        self._play_range.clock = values.split('-')
        return 'Range: ' + self._play_range.clock

    def _set_position(self, scale):
        fwd = 0 if scale >= 0 else 1
        start_ts = self._streamers[self._play_range.track_id].position
        if self._play_range.npt_range[fwd] >= start_ts:
            self._reader.move_to(self._play_range.npt_range[fwd] - start_ts)
        else:
            self._reader.move_back(start_ts - self._play_range.npt_range[fwd])
        for key in self._streamers:
            self._streamers[key].position = self._play_range.npt_range[fwd]
