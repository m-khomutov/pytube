"""stores media data in MP4 format"""
import os.path
import shutil
import tempfile
from .rtmp.messages.data import VideoData, AudioData
from .atom import ftyp, stsz


class Mp4Sink:
    def __init__(self, root: str) -> None:
        self._root: str = root
        self._name: tuple = ()
        self._folder: str = None
        self._stsz: stsz.Box = stsz.Box(version=0, flags=0)

    def __del__(self) -> None:
        try:
            with open(self._name[0], 'ab') as f:
                f.write(self._stsz.to_bytes())
            os.rename(self._name[0], self._name[1])
            shutil.rmtree(self._folder)
        except OSError as err:
            print(err)

    def on_publish(self, publish_name: str) -> None:
        self._folder = tempfile.mkdtemp()
        self._name = os.path.join(self._folder, publish_name + '.mp4'), os.path.join(self._root, publish_name + '.mp4')

    def on_metadata(self, data: dict) -> None:
        print(f'Meta: {data}')
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
        self._stsz.append(len(payload))
        for i in payload[:10]:
            print(f'{i:x}', end=' ')
        print(f' of {len(payload)}')

    def on_audio_config(self, payload: bytes) -> None:
        #print(AudioData.configuration)
        pass

    def on_audiodata(self, payload: bytes) -> None:
        for i in payload[:5]:
            print(f'{i:x}', end=' ')
        print(f' of {len(payload)}')
