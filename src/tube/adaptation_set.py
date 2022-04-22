# from .atom import tkhd, mdhd


class AdaptationSet:
    def __init__(self, tkhd_box, mdhd_box):
        self._initialization = f'_init.mp4'
        self._mdhd_box = mdhd_box
        self._tkhd_box = tkhd_box
        self._mime_type = 'video/mp4'
        self._media = f'_sn$Number$.m4s'

    @property
    def mime_type(self):
        return self._mime_type

    @property
    def media(self):
        return self._media

    @media.setter
    def media(self, value):
        self._media = value

    @property
    def initialization(self):
        return self._initialization

    @initialization.setter
    def initialization(self, value):
        self._initialization = value

    @property
    def id(self):
        return self._tkhd_box.track_id

    @property
    def timescale(self):
        return self._mdhd_box.timescale

    @property
    def duration(self):
        return self._tkhd_box.duration

    @property
    def language(self):
        return self._mdhd_box.language

    @property
    def segment_url(self):
        return self._initialization.split('_init.')[0]

    @segment_url.setter
    def segment_url(self, value):
        if value:
            self._initialization = value + self._initialization
            self._media = value + self._media
