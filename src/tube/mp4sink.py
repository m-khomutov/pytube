"""stores media data in MP4 format"""
import os.path
import shutil
import tempfile
from collections import defaultdict
from .rtmp.messages.data import VideoData, AudioData
from .atom import atom, ftyp, mvhd, tkhd, hdlr, stsd, stsz


class Mp4Sink:
    def __init__(self, root: str) -> None:
        self._root: str = root
        self._name: tuple = ()
        self._folder: str = None
        self._metadata: dict = {}
        self._stsz: defaultdict = defaultdict(lambda: stsz.Box(version=0, flags=0))

    def __del__(self) -> None:
        try:
            with open(self._name[0], 'ab') as f:
                self._compile(f)
            os.rename(self._name[0], self._name[1])
            shutil.rmtree(self._folder)
        except OSError as err:
            print(err)

    def on_publish(self, publish_name: str) -> None:
        self._folder = tempfile.mkdtemp()
        self._name = os.path.join(self._folder, publish_name + '.mp4'), os.path.join(self._root, publish_name + '.mp4')

    def on_metadata(self, data: dict) -> None:
        self._metadata = data
        print(f'Meta: {self._metadata}')
        with open(self._name[0], 'wb') as f:
            ftyp_box: ftyp.Box = ftyp.Box(major_brand='isom',
                                          minor_version=512,
                                          compatible_brands={'isom', 'iso2', 'avc1', 'mp41'}
                                          )
            f.write(ftyp_box.to_bytes())

    def on_video_config(self, payload: bytes) -> None:
        d = os.path.join(self._folder, 'vide')
        try:
            os.mkdir(d)
        except OSError as err:
            print(err)
        print(VideoData.configuration)

    def on_videodata(self, payload: bytes) -> None:
        self._stsz['vide'].append(len(payload))
        for i in payload[:10]:
            print(f'{i:x}', end=' ')
        print(f' of {len(payload)}')

    def on_audio_config(self, payload: bytes) -> None:
        #print(AudioData.configuration)
        pass

    def on_audiodata(self, payload: bytes) -> None:
        self._stsz['soun'].append(len(payload))
        for i in payload[:5]:
            print(f'{i:x}', end=' ')
        print(f' of {len(payload)}')

    def _compile(self, file):
        moov: atom.Box = atom.Box(type='moov')
        moov.add_inner_box(mvhd.Box(next_track_id=len(self._stsz) + 1))
        stsd_ = sorted(self._stsz, reverse=True)
        for i, tr in enumerate(stsd_):
            track: atom.Box = atom.Box(type='trak')
            volume: int = 0 if tr == 'vide' else 0x0100
            duration: int = int(self._metadata.get('duration', 0.))
            width: int = int(self._metadata.get('width', 0.)) if tr == 'vide' else 0
            height: int = int(self._metadata.get('height', 0.)) if tr == 'vide' else 0
            track.add_inner_box(tkhd.Box(track_id=i+1,
                                         volume=volume,
                                         duration=duration,
                                         width=width,
                                         height=height
                                         )
                                )
            track.add_inner_box(atom.Box(type='mdia'))
            track.add_inner_box(hdlr.Box(handler_type=tr,
                                         name='VideoHandler' if tr == 'vide' else 'SoundHandler'
                                         ),
                                'mdia'
                                )
            track.add_inner_box(atom.Box(type='minf'), 'mdia')
            track.add_inner_box(atom.Box(type='stbl'), 'minf')
            track.add_inner_box(stsd.Box(), 'stbl')
            track.add_inner_box(self._stsz[tr], 'stbl')
            moov.add_inner_box(track)
        file.write(moov.to_bytes())
