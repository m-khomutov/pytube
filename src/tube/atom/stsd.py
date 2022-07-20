"""The sample description table gives detailed information about
   the coding type used, and any initialization information
   needed for that coding
"""
from functools import reduce
from enum import IntEnum
from .atom import FullBox, full_box_derived, Box as Atom
from . import esds, avcc, hvcc, pasp, fiel


def atom_type():
    """Returns this atom type"""
    return 'stsd'


VideoCodecType: IntEnum = IntEnum('VideoCodecType', ('UNKNOWN',
                                                     'AVC',
                                                     'HEVC',
                                                     )
                                  )


class SampleEntry(Atom):
    """The information stored in the sample description box
       is both track-type specific and can also have variants within a track type
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._read_some(file, 6)
            self.data_reference_index = int.from_bytes(self._read_some(file, 2), "big")

    def __repr__(self):
        return super().__repr__() + f" dataRefIdx:{self.data_reference_index}"

    def init_from_args(self, **kwargs):
        super().init_from_args(**kwargs)
        self.type = kwargs.get('format', 'vide')
        self.data_reference_index = kwargs.get('data_reference_index', 1)
        self.size = 16

    def to_bytes(self):
        """Returns sample entry as bytestream, ready to be sent to socket"""
        ret = super().to_bytes() + bytes(6)
        ret += self.data_reference_index.to_bytes(2, byteorder='big')
        return ret


class VisualSampleEntry(SampleEntry):
    """The sample description table for video tracks"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._read_some(file, 16)
            self.geometry = (int.from_bytes(self._read_some(file, 2), "big"),
                             int.from_bytes(self._read_some(file, 2), "big"))
            self.resolution = (int.from_bytes(self._read_some(file, 4), "big"),
                               int.from_bytes(self._read_some(file, 4), "big"))
            self._read_some(file, 4)
            self.frame_count = int.from_bytes(self._read_some(file, 2), "big")
            self.compressor_name = self._read_some(file, 32).decode("utf-8")
            self.color_depth = int.from_bytes(self._read_some(file, 2), "big")
            self._read_some(file, 2)
            left = self.size - (file.tell()-self.position)
            self._coding_boxes = {}  # [avcC hvcC pasp fiel]
            while left > 0:
                box = Atom(file=file, depth=self._depth + 1)
                file.seek(box.position)
                coding_box = {
                    'avcC': lambda: avcc.Box(file=file, depth=self._depth + 1),
                    'hvcC': lambda: hvcc.Box(file=file, depth=self._depth + 1),
                    'pasp': lambda: pasp.Box(file=file, depth=self._depth + 1),
                    'fiel': lambda: fiel.Box(file=file, depth=self._depth + 1),
                }.get(box.type, lambda: None)()
                if coding_box:
                    self._coding_boxes[box.type] = coding_box
                    left -= coding_box.size
                else:
                    file.seek(box.position + box.size)
                    left -= box.size
                    self.size -= box.size

    def __repr__(self):
        ret = super().__repr__() + \
            f" width:{self.geometry[0]} height:{self.geometry[1]}" +\
            " h_resolution:" + hex(self.resolution[0]) + \
            " v_resolution:" + hex(self.resolution[1]) + \
            f" frame_count:{self.frame_count}" + \
            f" depth:{self.color_depth}\n" + \
            '\n'.join(str(self._coding_boxes[k]) for k in self._coding_boxes)
        return ret

    def __getitem__(self, item):
        return self._coding_boxes.get(item, None)

    def init_from_args(self, **kwargs):
        super().init_from_args(**kwargs)
        self.type = kwargs.get('format', 'vide')
        self.geometry = kwargs.get('width', 0), kwargs.get('height', 0)
        self.resolution = kwargs.get('hresolution', 0x00480000), kwargs.get('vresolution', 0x00480000)
        self.frame_count = kwargs.get('frame_count', 1)
        self.compressor_name = kwargs.get('compressor', ' '*32)
        self.color_depth = kwargs.get('depth', 0x0018)
        self.size = 16

    def to_bytes(self):
        ret = super().to_bytes()
        ret += bytearray(16)
        ret += self.geometry[0].to_bytes(2, byteorder='big')
        ret += self.geometry[1].to_bytes(2, byteorder='big')
        ret += self.resolution[0].to_bytes(4, byteorder='big')
        ret += self.resolution[1].to_bytes(4, byteorder='big')
        ret += (0).to_bytes(4, byteorder='big')
        ret += self.frame_count.to_bytes(2, byteorder="big")
        ret += str.encode(self.compressor_name)
        ret += self.color_depth.to_bytes(2, byteorder='big')
        ret += (0xffff).to_bytes(2, byteorder='big')
        for box in self._coding_boxes.values():
            ret += box.to_bytes()
        return ret


class AudioSampleEntry(SampleEntry):
    """The sample description table for audio tracks"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._read_some(file, 8)
            self.channel_count = int.from_bytes(self._read_some(file, 2), "big")
            self.sample_size = int.from_bytes(self._read_some(file, 2), "big")
            self._read_some(file, 4)
            self.sample_rate = int.from_bytes(self._read_some(file, 4), "big")
            left = self.size - (file.tell()-self.position)
            while left > 0:
                box = Atom(file=file, depth=self._depth + 1)
                if box.type == 'esds':
                    file.seek(box.position)
                    self.stream_descriptors = esds.Box(file=file, depth=self._depth + 1)
                    left -= self.stream_descriptors.size

    def __repr__(self):
        ret = super().__repr__() +\
              f" channels:{self.channel_count}" \
              f" sample_size:{self.sample_size}" \
              f" sample_rate:{self.sample_rate >> 16}"
        if self.stream_descriptors is not None:
            ret += f"\n{self.stream_descriptors}"
        return ret

    @property
    def rtpmap(self):
        """Returns RTPMAP structure"""
        if self.type == 'mp4a':
            return 'MPEG4-GENERIC/' + \
                   str(self.sample_rate >> 16) + '/' + str(self.channel_count)
        return ''

    @property
    def config(self):
        """Returns audio specific config"""
        if self.stream_descriptors is not None:
            try:
                return self.stream_descriptors.config
            except:  # noqa # pylint: disable=bare-except
                pass
        return ''

    def to_bytes(self):
        ret = super().to_bytes()
        ret += bytearray(8)
        ret += self.channel_count.to_bytes(2, byteorder='big')
        ret += self.sample_size.to_bytes(2, byteorder='big')
        ret += bytearray(4)
        ret += self.sample_rate.to_bytes(4, byteorder='big')
        if self.stream_descriptors is not None:
            ret += self.stream_descriptors.to_bytes()
        return ret


class HintSampleEntry(SampleEntry):
    """The sample description table for hint tracks"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._hint_data = self._read_some(file, self.size - 16)

    def __repr__(self):
        ret = super().__repr__() + \
              ' '.join('{:02x}'.format(k) for k in self._hint_data)
        return ret

    def to_bytes(self):
        return super().to_bytes() + self._hint_data


class StyleRecord:
    """Style information for the text to override the default style in the
       sample description or to define more than one style for a sample
    """
    def __init__(self, file):
        self._fields = [
            int.from_bytes(file.read(2), 'big'),  # start char
            int.from_bytes(file.read(2), 'big'),  # end char
            int.from_bytes(file.read(2), 'big'),  # font id
            int.from_bytes(file.read(1), 'big'),  # face style flags
            int.from_bytes(file.read(1), 'big'),  # font size
        ]
        self.text_color = list(map(lambda x: int.from_bytes(file.read(1), 'big'), range(4)))

    def __repr__(self):
        ret = f'start={self._fields[0]} end={self._fields[1]} font-id={self._fields[2]} '
        if self._fields[3] == 0:
            ret += 'plain'
        else:
            style = ''
            if self._fields[3] & 1 != 0:
                style += 'bold'
            if self._fields[3] & 2 != 0:
                if style:
                    style += '|'
                style += 'italic'
            if self._fields[3] & 4 != 0:
                if style:
                    style += '|'
                style += 'underline'
            ret += style
        ret += ' font size=' + str(self._fields[4]) + \
               ' color=[' + ' '.join(str(k) for k in self.text_color) + ']'
        return ret

    @property
    def start_char(self):
        """Offset of the first character that is to use the style specified in this record"""
        return self._fields[0]

    @start_char.setter
    def start_char(self, value):
        """Sets offset of the first character that is to use the style specified in this record"""
        self._fields[0] = value

    @property
    def end_char(self):
        """Returns offset of the character that follows the last character to use this style"""
        return self._fields[1]

    @end_char.setter
    def end_char(self, value):
        """Sets offset of the character that follows the last character to use this style"""
        self._fields[1] = value

    @property
    def font_id(self):
        """Returns font identifier"""
        return self._fields[2]

    @font_id.setter
    def font_id(self, value):
        """Sets font identifier"""
        self._fields[2] = value

    @property
    def face_style_flags(self):
        """Returns indications of the font’s style"""
        return self._fields[3]

    @face_style_flags.setter
    def face_style_flags(self, value):
        """Sets indications of the font’s style"""
        self._fields[3] = value

    @property
    def font_size(self):
        """Returns font's size specification"""
        return self._fields[4]

    @font_size.setter
    def font_size(self, value):
        """Sets font's size specification"""
        self._fields[4] = value

    def to_bytes(self):
        """Returns record as bytestream, ready to be sent to socket"""
        ret = b''
        for i, field in enumerate(self._fields):
            ret += field.to_bytes(2 if i < 3 else 1, byteorder='big')
        for color in self.text_color:
            ret += color.to_bytes(1, byteorder='big')
        return ret


class FontRecord:
    """Font record used in a font table"""
    def __init__(self, file):
        self._identifier = int.from_bytes(file.read(2), 'big')
        name_length = int.from_bytes(file.read(1), 'big')
        self._name = file.read(name_length).decode("utf-8")

    def __repr__(self):
        return 'id=' + str(self._identifier) + " '" + self._name + "'"

    @property
    def identifier(self):
        """Returns font identifier"""
        return self._identifier

    @property
    def name(self):
        """Returns font name"""
        return self._name

    def to_bytes(self):
        """Returns record as bytestream, ready to be sent to socket"""
        ret = self._identifier.to_bytes(2, byteorder='big')
        ret += len(self._name).to_bytes(1, byteorder='big') + self._name.encode()
        return ret


class FontTableBox(Atom):
    """The atom specifies fonts used to display the subtitle"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entries = []
        file = kwargs.get("file", None)
        if file is not None:
            count = int.from_bytes(file.read(2), 'big')
            self.entries = list(map(lambda x: FontRecord(file), range(count)))
        else:
            self.type = 'ftab'
            self.size = 10

    def __repr__(self):
        return '[' + ''.join(map(lambda x: '{' + str(x) + '}', self.entries)) + ']'

    def to_bytes(self):
        ret = super().to_bytes()
        ret += len(self.entries).to_bytes(2, byteorder='big')
        for entry in self.entries:
            ret += entry.to_bytes()
        return ret


class BoxRecord:
    """Defines text geometry on the window"""
    def __init__(self, file):
        self._fields = (int.from_bytes(file.read(2), 'big'),
                        int.from_bytes(file.read(2), 'big'),
                        int.from_bytes(file.read(2), 'big'),
                        int.from_bytes(file.read(2), 'big'))

    def __repr__(self):
        return ' '.join(str(k) for k in self._fields)

    @property
    def top(self):
        """Returns top corner fo the window"""
        return self._fields[0]

    @property
    def left(self):
        """Returns left corner fo the window"""
        return self._fields[1]

    @property
    def bottom(self):
        """Returns bottom corner fo the window"""
        return self._fields[2]

    @property
    def right(self):
        """Returns right corner fo the window"""
        return self._fields[3]

    def to_bytes(self):
        """Returns record as bytestream, ready to be sent to socket"""
        return reduce(lambda a, b: a + b,
                      map(lambda x: x.to_bytes(2, byteorder='big'), self._fields))


class TextSampleEntry(SampleEntry):
    """The sample description table for subtitles"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self.display_flags = int.from_bytes(file.read(4), 'big')
            self.horizontal_justification = int.from_bytes(file.read(1), 'big', signed=True)
            self.vertical_justification = int.from_bytes(file.read(1), 'big', signed=True)
            self.background_color_rgba = \
                list(map(lambda x: int.from_bytes(file.read(1), 'big'), range(4)))
            self.default_text_box = BoxRecord(file)
            self.default_style = StyleRecord(file)
            self.font_table = FontTableBox(file=file, depth=self._depth)

    def __repr__(self):
        ret = super().__repr__() + ' flags=' + hex(self.display_flags) + ' justification=(' +\
              str(self.horizontal_justification) + ' ' + str(self.vertical_justification)
        ret += ' bg color=[' + ' '.join(str(k) for k in self.background_color_rgba) + \
               '] default textbox={' + str(self.default_text_box) + \
               '} default style={' + str(self.default_style) + \
               '} font table=' + str(self.font_table)
        return ret

    def to_bytes(self):
        ret = super().to_bytes()
        ret += self.display_flags.to_bytes(4, byteorder='big')
        ret += self.horizontal_justification.to_bytes(1, byteorder='big', signed=True)
        ret += self.vertical_justification.to_bytes(1, byteorder='big', signed=True)
        for color in self.background_color_rgba:
            ret += color.to_bytes(1, byteorder='big')
        ret += self.default_text_box.to_bytes()
        ret += self.default_style.to_bytes()
        ret += self.font_table.to_bytes()
        return ret


@full_box_derived
class Box(FullBox):
    """Sample descriptions (codec types, initialization etc.)"""
    def __init__(self, *args, **kwargs):
        self.entries = []
        self.video_stream_type = VideoCodecType.UNKNOWN
        self.handler = kwargs.get('hdlr', None)
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return super().__repr__() + '\n' + '\n'.join(str(k) for k in self.entries)

    def video_configuration_box(self):
        """Returns AVC or HVC ConfigurationBox"""
        if self.handler == 'vide' and self.entries:
            if self.video_stream_type == VideoCodecType.AVC:
                return self.entries[0]['avcC']
            return self.entries[0]['hvcC']
        return None

    def normalize(self):
        """Returns box with all entries size"""
        self.size = 16 + sum([k.size for k in self.entries])

    def init_from_file(self, file):
        self.entries = self._read_entries(file)

    def init_from_args(self, **kwargs):
        super().init_from_args(**kwargs)
        self.type = atom_type()
        self.size = 16

    def _read_entry(self, file):
        """Reads entry of specific type"""
        if self.handler == 'vide':
            entry = VisualSampleEntry(file=file, depth=self._depth+1)
            if entry['avcC']:
                self.video_stream_type = VideoCodecType.AVC
            elif entry['hvcC']:
                self.video_stream_type = VideoCodecType.HEVC
            return entry
        if self.handler == 'soun':
            return AudioSampleEntry(file=file, depth=self._depth+1)
        if self.handler == 'text':
            return TextSampleEntry(file=file, depth=self._depth+1)
        if self.handler == 'hint':
            return HintSampleEntry(file=file, depth=self._depth+1)
        return SampleEntry()

    def to_bytes(self):
        ret = super().to_bytes()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        for entry in self.entries:
            ret += entry.to_bytes()
        return ret
