"""Network RTSP service session"""
import random
import string
import logging
from ..reader import Reader
from ..rtp.streamer import Streamer as RtpStreamer


class Session:
    """RTSP Session parameters"""
    _session_id = ''
    _streamers = {}
    _sdp = ''
    _reader = None

    def __init__(self, content_base, filename, verbal):
        self._content_base = content_base
        self._reader = Reader(filename)
        self._verbal = verbal
        if self._verbal:
            logging.info(self._reader)
        for box in self._reader.find_box('trak'):
            track_id = box.find_inner_boxes('tkhd')[0].track_id
            box = box.find_inner_boxes('stsd')[0]
            if box.handler == 'vide':
                self._sdp = self._make_video_sdp(track_id, box.entries)
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
        return self._streamers[1].next_frame(self._reader, self._verbal)

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

    def _make_video_sdp(self, track_id, stsd_boxes):
        ret = ''
        if stsd_boxes:
            ret += 'm=video 0 RTP/AVP 96\r\n'
            avc_box = stsd_boxes[0].inner_boxes.get('avcC')
            if avc_box is not None:
                ret += 'a=rtpmap:96 H264/90000\r\n' + \
                       'a=fmtp:96 packetization-mode=1' + \
                       '; sprop-parameter-sets=' + avc_box.sprop_parameter_sets + \
                       '; profile-level-id=' + \
                       avc_box.profile_level_id + '\r\n'
            ret += 'a=control:' + str(track_id) + '\r\n'
            self._streamers[track_id] = RtpStreamer(track_id, 96)
        return ret

    def _make_audio_sdp(self, track_id, stsd_boxes):
        ret = ''
        if stsd_boxes:
            print(str(stsd_boxes[0]))
            ret += 'm=audio 0 RTP/AVP 97\r\n' + \
                   'a=rtpmap:97 ' + stsd_boxes[0].rtpmap + '\r\n' + \
                   'a=fmtp:97 config=' + stsd_boxes[0].config + '\r\n' + \
                   'a=control:' + str(track_id) + '\r\n'
            self._streamers[track_id] = RtpStreamer(track_id, 97)
        return ret
