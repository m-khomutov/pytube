"""Network RTSP service session"""
import random
import string
import logging
from datetime import datetime
from ..reader import Reader
from ..rtp.streamer import AvcStreamer, HevcStreamer, AudioStreamer
from ..atom.hvcc import NetworkUnitType


class Session:
    """RTSP Session parameters"""
    _session_id = ''
    _streamers = {}
    _sdp = ''

    def __init__(self, content_base, filename, verbal):
        self._content_base = content_base
        self._reader = Reader(filename)
        self._verbal = verbal
        self._range = (datetime.now().timestamp() - int(self.duration) - 1,
                       datetime.now().timestamp() - 1)
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
        session_id = [k for k in headers if 'Session: ' in k][0][9:]
        return content == self._content_base and session_id == self._session_id

    def get_next_frame(self):
        """If time has come writes next media frame"""
        ret = b''
        try:
            for key in self._streamers:
                ret += self._streamers[key].next_frame(self._reader, key, self._verbal)
        except:  # noqa # pylint: disable=bare-except
            pass
        return ret

    def normal_play_time(self):
        """Returns media duration in NPT format"""
        return 'npt=-' + str(self.duration) + '\r\n'

    def range_as_absolute_time(self):
        """Returns media duration in Clock format"""
        fraction = int((self.duration - int(self.duration)) * 1000)
        return 'clock=' + \
               datetime.fromtimestamp(self._range[0]).strftime('%Y%m%dT%H%M%SZ-') + \
               datetime.fromtimestamp(self._range[1]).strftime('%Y%m%dT%H%M%S.') + \
               str(fraction) + 'Z\r\n'

    def position_absolute_time(self):
        """Returns current position in Clock format"""
        position = self._range[0]

        for key in (k for k in self._streamers if isinstance(self._streamers[k], AvcStreamer)):
            position += self._streamers[key].position
            break
        return 'clock=' + \
               datetime.fromtimestamp(position).strftime('%Y%m%dT%H%M%SZ-\r\n')

    @property
    def content_base(self):
        """Returns content base URL"""
        return self._content_base

    @property
    def identification(self):
        """Returns session identification"""
        if not self._session_id:
            source = string.ascii_letters + string.digits
            self._session_id = ''.join(map(lambda x: random.choice(source), range(16)))
        return str.encode('Session: ' + self._session_id + '\r\n')

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
            avc_box = stsd_boxes[0].inner_boxes.get('avcC')
            if avc_box is not None:
                ret += self._make_avc_sdp(track_id, avc_box)
            else:
                hevc_box = stsd_boxes[0].inner_boxes.get('hvcC')
                if hevc_box is not None:
                    ret += self._make_hevc_sdp(track_id, hevc_box)
        return ret

    def _make_avc_sdp(self, track_id, avc_box):
        self._streamers[track_id] = AvcStreamer(96, (avc_box.sps, avc_box.pps))
        ret = 'a=rtpmap:96 H264/90000\r\n' + \
              'a=fmtp:96 packetization-mode=1' + \
              '; sprop-parameter-sets=' + avc_box.sprop_parameter_sets + \
              '; profile-level-id=' + \
              avc_box.profile_level_id + '\r\n' + \
              'a=range:' + self.range_as_absolute_time()
        return ret + 'a=control:' + str(track_id) + '\r\n'

    def _make_hevc_sdp(self, track_id, hevc_box):
        self._streamers[track_id] = HevcStreamer(96)
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
