"""Network RTSP service session"""
import random
import string
from ..reader import Reader
from ..rtp.streamer import Streamer as RtpStreamer


class Session:
    """RTSP Session parameters"""
    _session_id = ''
    _transport = {}
    _sdp = ''
    _streamer = None

    def __init__(self, content_base, filename, verbal):
        self._streamer = RtpStreamer(Reader(filename), verbal)
        self._content_base = content_base
        for box in self._streamer.reader.find_box('stsd'):
            if box.handler == 'vide':
                self._sdp = self._make_video_sdp(box.entries)
            elif box.handler == 'soun':
                self._sdp += self._make_audio_sdp(box.entries)

    def __del__(self):
        # self._streamer.join()
        pass

    def add_stream(self, headers):
        """Adds a controlled stream"""
        stream = int(headers[0].split()[1].split('/')[-1])
        transport = ''
        if self._transport.get(stream) is not None:
            transport = [k for k in headers if 'Transport: ' in k][0]
            self._transport[stream] = transport
        return transport

    def valid_request(self, headers):
        """Verifies content and session identity"""
        content = headers[0].split()[1]
        session_id = [k for k in headers if 'Session: ' in k][0][9:]
        return content == self._content_base and session_id == self._session_id

    def get_next_frame(self):
        """If time has come writes next media frame"""
        return self._streamer.next_frame()

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

    def _make_video_sdp(self, stsd_boxes):
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
            ret += 'a=control:0\r\n'
            self._transport[0] = ''
        return ret

    def _make_audio_sdp(self, stsd_boxes):
        ret = ''
        if stsd_boxes:
            print(str(stsd_boxes[0]))
            ret += 'm=audio 0 RTP/AVP 97\r\n' + \
                   'a=rtpmap:97 ' + stsd_boxes[0].rtpmap + '\r\n' + \
                   'a=fmtp:97 config=' + stsd_boxes[0].config + '\r\n' + \
                   'a=control:1\r\n'
            self._transport[1] = ''
        return ret
