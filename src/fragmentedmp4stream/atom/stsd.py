"""The sample description table gives detailed information about
   the coding type used, and any initialization information
   needed for that coding
"""
from enum import IntEnum
from . import atom, esds, avcc, hvcc, pasp, fiel


class VideoCodecType(IntEnum):
    """Supported codec enumeration"""
    UNKNOWN = 0
    AVC = 1
    HEVC = 2


class SampleEntry(atom.Box):
    """The information stored in the sample description box
       is both track-type specific and can also have variants within a track type
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readsome(file, 6)
            self.data_reference_index = int.from_bytes(self._readsome(file, 2), "big")

    def __repr__(self):
        return super().__repr__() + f" dataRefIdx:{self.data_reference_index}"

    def to_bytes(self):
        """Returns sample entry as bytestream, ready to be sent to socket"""
        ret = super().to_bytes() + bytearray(6)
        ret += self.data_reference_index.to_bytes(2, byteorder='big')
        return ret


class VisualSampleEntry(SampleEntry):
    """The sample description table for video tracks"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readsome(file, 16)
            self.geometry = (int.from_bytes(self._readsome(file, 2), "big"),
                             int.from_bytes(self._readsome(file, 2), "big"))
            self.resolution = (int.from_bytes(self._readsome(file, 4), "big"),
                               int.from_bytes(self._readsome(file, 4), "big"))
            self._readsome(file, 4)
            self.frame_count = int.from_bytes(self._readsome(file, 2), "big")
            self.compressor_name = self._readsome(file, 32).decode("utf-8")
            self.color_depth = int.from_bytes(self._readsome(file, 2), "big")
            self._readsome(file, 2)
            left = self.size - (file.tell()-self.position)
            self.inner_boxes = {}  # [avcC hvcC pasp fiel]
            while left > 0:
                box = atom.Box(file=file, depth=self._depth + 1)
                if box.type == 'avcC':
                    file.seek(box.position)
                    inner_box = avcc.Box(file=file, depth=self._depth + 1)
                    self.inner_boxes[box.type] = inner_box
                    left -= inner_box.size
                elif box.type == 'hvcC':
                    file.seek(box.position)
                    inner_box = hvcc.Box(file=file, depth=self._depth + 1)
                    self.inner_boxes[box.type] = inner_box
                    left -= inner_box.size
                elif box.type == 'pasp':
                    file.seek(box.position)
                    inner_box = pasp.Box(file=file, depth=self._depth + 1)
                    self.inner_boxes[box.type] = inner_box
                    left -= inner_box.size
                elif box.type == 'fiel':
                    file.seek(box.position)
                    inner_box = fiel.Box(file=file, depth=self._depth + 1)
                    self.inner_boxes[box.type] = inner_box
                    left -= inner_box.size
                else:
                    file.seek(box.position+box.size)
                    left -= box.size
                    self.size -= box.size

    def __repr__(self):
        ret = super().__repr__() + \
              f" width:{self.geometry[0]} height:{self.geometry[1]}" +\
              " h_resolution:" + hex(self.resolution[0]) + \
              " v_resolution:" + hex(self.resolution[1]) + \
              f" frame_count:{self.frame_count}" \
              f" compressor_name:'{self.compressor_name}'" \
              f" depth:{self.color_depth}\n"
        ret += '\n'.join(str(self.inner_boxes[k]) for k in self.inner_boxes)
        return ret

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
        for key in self.inner_boxes:
            ret += self.inner_boxes[key].to_bytes()
        return ret


class AudioSampleEntry(SampleEntry):
    """The sample description table for audio tracks"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readsome(file, 8)
            self.channel_count = int.from_bytes(self._readsome(file, 2), "big")
            self.sample_size = int.from_bytes(self._readsome(file, 2), "big")
            self._readsome(file, 4)
            self.sample_rate = int.from_bytes(self._readsome(file, 4), "big")
            left = self.size - (file.tell()-self.position)
            while left > 0:
                box = atom.Box(file=file, depth=self._depth + 1)
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


class StyleRecord:
    """Style information for the text to override the default style in the
       sample description or to define more than one style for a sample
    """
    def __init__(self, file):
        self.start_char = int.from_bytes(file.read(2), 'big')
        self.end_char = int.from_bytes(file.read(2), 'big')
        self.font_id = int.from_bytes(file.read(2), 'big')
        self.face_style_flags = int.from_bytes(file.read(1), 'big')
        self.font_size = int.from_bytes(file.read(1), 'big')
        self.text_color = list(map(lambda x: int.from_bytes(file.read(1), 'big'), range(4)))

    def __repr__(self):
        ret = f'start={self.start_char} end={self.end_char} font-id={self.font_id} '
        if self.face_style_flags == 0:
            ret += 'plain'
        else:
            style = ''
            if self.face_style_flags & 1 != 0:
                style += 'bold'
            if self.face_style_flags & 2 != 0:
                if len(style) > 0:
                    style += '|'
                style += 'italic'
            if self.face_style_flags & 4 != 0:
                if len(style) > 0:
                    style += '|'
                style += 'underline'
            ret += style
        ret += ' font size=' + str(self.font_size) + \
               ' color=[' + ' '.join(str(k) for k in self.text_color) + ']'
        return ret

    def to_bytes(self):
        """Returns record as bytestream, ready to be sent to socket"""
        ret = self.start_char.to_bytes(2, byteorder='big')
        ret += self.end_char.to_bytes(2, byteorder='big')
        ret += self.font_id.to_bytes(2, byteorder='big')
        ret += self.face_style_flags.to_bytes(1, byteorder='big')
        ret += self.font_size.to_bytes(1, byteorder='big')
        for color in self.text_color:
            ret += color.to_bytes(1, byteorder='big')
        return ret


class FontRecord:
    """Font record used in a font table"""
    def __init__(self, file):
        self.identifier = int.from_bytes(file.read(2), 'big')
        name_length = int.from_bytes(file.read(1), 'big')
        self.name = file.read(name_length).decode("utf-8")

    def __repr__(self):
        return 'id=' + str(self.identifier) + " '" + self.name + "'"

    def to_bytes(self):
        """Returns record as bytestream, ready to be sent to socket"""
        ret = self.identifier.to_bytes(2, byteorder='big')
        ret += len(self.name).to_bytes(1, byteorder='big') + self.name.encode()
        return ret


class FontTableBox(atom.Box):
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
        self.top = int.from_bytes(file.read(2), 'big')
        self.left = int.from_bytes(file.read(2), 'big')
        self.bottom = int.from_bytes(file.read(2), 'big')
        self.right = int.from_bytes(file.read(2), 'big')

    def __repr__(self):
        return f't={self.top} l={self.left} b={self.bottom} r={self.right}'

    def to_bytes(self):
        """Returns record as bytestream, ready to be sent to socket"""
        ret = self.top.to_bytes(2, byteorder='big')
        ret += self.left.to_bytes(2, byteorder='big')
        ret += self.bottom.to_bytes(2, byteorder='big')
        ret += self.right.to_bytes(2, byteorder='big')
        return ret


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


class Box(atom.FullBox):
    """Sample descriptions (codec types, initialization etc.)"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.entries = []
        self.video_stream_type = VideoCodecType.UNKNOWN
        if file is not None:
            self._readfile(file, kwargs.get('hdlr', None))

    def __repr__(self):
        return super().__repr__() + '\n' + '\n'.join(str(k) for k in self.entries)

    def normalize(self):
        """Returns box with all entries size"""
        self.size = 16 + sum([k.size for k in self.entries])

    def _readfile(self, file, handler):
        count = int.from_bytes(self._readsome(file, 4), "big")
        if handler is not None:
            self.entries = list(map(lambda x: self._read_entry(file, handler), range(count)))

    def _read_entry(self, file, handler):
        """Reads entry of specific type"""
        if handler == 'vide':
            entry = VisualSampleEntry(file=file, depth=self._depth+1)
            if entry.inner_boxes.get('avcC') is not None:
                self.video_stream_type = VideoCodecType.AVC
            elif entry.inner_boxes.get('hvcC') is not None:
                self.video_stream_type = VideoCodecType.HEVC
            return entry
        if handler == 'soun':
            return AudioSampleEntry(file=file, depth=self._depth+1)
        if handler == 'text':
            return TextSampleEntry(file=file, depth=self._depth+1)
        return SampleEntry()

    def to_bytes(self):
        ret = super().to_bytes()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        for entry in self.entries:
            ret += entry.to_bytes()
        return ret
