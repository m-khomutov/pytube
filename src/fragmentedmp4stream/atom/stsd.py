"""Sample descriptions (codec types, initialization etc.)"""
from . import atom, esds, avcc, hvcc, pasp, fiel
from enum import IntEnum


class VideoCodecType(IntEnum):
    """Supported codec enumeration"""
    UNKNOWN = 0
    AVC = 1
    HEVC = 2


class SampleEntry(atom.Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readsome(file, 6)
            self.data_reference_index = int.from_bytes(self._readsome(file, 2), "big")

    def __repr__(self):
        return super().__repr__() + " dataRefIdx:" + str(self.data_reference_index)

    def to_bytes(self):
        return super().to_bytes() + bytearray(6) + self.data_reference_index.to_bytes(2, byteorder='big')


class VisualSampleEntry(SampleEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self._readsome(file, 16)
            self.width = int.from_bytes(self._readsome(file, 2), "big")
            self.height = int.from_bytes(self._readsome(file, 2), "big")
            self.horizontal_resolution = int.from_bytes(self._readsome(file, 4), "big")
            self.vertical_resolution = int.from_bytes(self._readsome(file, 4), "big")
            self._readsome(file, 4)
            self.frame_count = int.from_bytes(self._readsome(file, 2), "big")
            self.compressor_name = self._readsome(file, 32).decode("utf-8")
            self.color_depth = int.from_bytes(self._readsome(file, 2), "big")
            self._readsome(file, 2)
            left = self.size - (file.tell()-self.position)
            self.advanced_vcc_box = None
            self.high_vcc_box = None
            self.pixel_aspect_ratio_box = None
            self.field_display_order = None
            while left > 0:
                box = atom.Box(file=file, depth=self._depth + 1)
                if box.type == 'avcC':
                    file.seek(box.position)
                    self.advanced_vcc_box = avcc.Box(file=file, depth=self._depth + 1)
                    left -= self.advanced_vcc_box.size
                elif box.type == 'hvcC':
                    file.seek(box.position)
                    self.high_vcc_box = hvcc.Box(file=file, depth=self._depth + 1)
                    left -= self.high_vcc_box.size
                elif box.type == 'pasp':
                    file.seek(box.position)
                    self.pixel_aspect_ratio_box = pasp.Box(file=file, depth=self._depth + 1)
                    left -= self.pixel_aspect_ratio_box.size
                elif box.type == 'fiel':
                    file.seek(box.position)
                    self.field_display_order = fiel.Box(file=file, depth=self._depth + 1)
                    left -= self.field_display_order.size
                else:
                    file.seek(box.position+box.size)
                    left -= box.size
                    self.size -= box.size

    def __repr__(self):
        ret = super().__repr__() + " width:" + str(self.width) + \
                                   " height:" + str(self.height) + \
                                   " h_resolution:" + hex(self.horizontal_resolution) + \
                                   " v_resolution:" + hex(self.vertical_resolution) + \
                                   " frame_count:" + str(self.frame_count) + \
                                   " compressor_name:'" + self.compressor_name + "'"\
                                   " depth:" + str(self.color_depth)
        if self.advanced_vcc_box is not None:
            ret += "\n" + self.advanced_vcc_box.__repr__()
        if self.high_vcc_box is not None:
            ret += "\n" + self.high_vcc_box.__repr__()
        if self.pixel_aspect_ratio_box is not None:
            ret += "\n" + self.pixel_aspect_ratio_box.__repr__()
        if self.field_display_order is not None:
            ret += "\n" + self.field_display_order.__repr__()
        return ret

    def to_bytes(self):
        ret = super().to_bytes()
        ret += bytearray(16)
        ret += self.width.to_bytes(2, byteorder='big')
        ret += self.height.to_bytes(2, byteorder='big')
        ret += self.horizontal_resolution.to_bytes(4, byteorder='big')
        ret += self.vertical_resolution.to_bytes(4, byteorder='big')
        ret += (0).to_bytes(4, byteorder='big')
        ret += self.frame_count.to_bytes(2, byteorder="big")
        ret += str.encode(self.compressor_name)
        ret += self.color_depth.to_bytes(2, byteorder='big')
        ret += (0xffff).to_bytes(2, byteorder='big')
        if self.advanced_vcc_box is not None:
            ret += self.advanced_vcc_box.to_bytes()
        if self.high_vcc_box is not None:
            ret += self.high_vcc_box.encode()
        if self.pixel_aspect_ratio_box is not None:
            ret += self.pixel_aspect_ratio_box.to_bytes()
        if self.field_display_order is not None:
            ret += self.field_display_order.to_bytes()
        return ret


class AudioSampleEntry(SampleEntry):
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
              " channels:{} sample_size:{} sample_rate:{}".format(self.channel_count,
                                                                  self.sample_size,
                                                                  self.sample_rate >> 16)
        if self.stream_descriptors is not None:
            ret += "\n" + self.stream_descriptors.__repr__()
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
    def __init__(self, file):
        self.start_char = int.from_bytes(file.read(2), 'big')
        self.end_char = int.from_bytes(file.read(2), 'big')
        self.font_id = int.from_bytes(file.read(2), 'big')
        self.face_style_flags = int.from_bytes(file.read(1), 'big')
        self.font_size = int.from_bytes(file.read(1), 'big')
        self.text_color = list(map(lambda x: int.from_bytes(file.read(1), 'big'), range(4)))

    def __repr__(self):
        ret = 'start=' + str(self.start_char) + ' end=' + str(self.end_char) + ' font-id=' + str(self.font_id) + ' '
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
        ret += ' font size=' + str(self.font_size) + ' color=[ '
        for cl in self.text_color:
            ret += str(cl) + ' '
        return ret + ']'

    def to_bytes(self):
        ret = self.start_char.to_bytes(2, byteorder='big') + \
              self.end_char.to_bytes(2, byteorder='big') + \
              self.font_id.to_bytes(2, byteorder='big') + \
              self.face_style_flags.to_bytes(1, byteorder='big') + \
              self.font_size.to_bytes(1, byteorder='big')
        for cl in self.text_color:
            ret += cl.to_bytes(1, byteorder='big')
        return ret


class FontRecord:
    def __init__(self, file):
        self.id = int.from_bytes(file.read(2), 'big')
        name_length = int.from_bytes(file.read(1), 'big')
        self.name = file.read(name_length).decode("utf-8")

    def __repr__(self):
        return 'id=' + str(self.id) + " '" + self.name + "'"

    def to_bytes(self):
        return self.id.to_bytes(2, byteorder='big') + len(self.name).to_bytes(1, byteorder='big') + self.name.encode()


class FontTableBox(atom.Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entries = []
        file = kwargs.get("file", None)
        if file is not None:
            count = int.from_bytes(file.read(2), 'big')
            for i in range(count):
                self.entries.append(FontRecord(file))
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
    def __init__(self, file):
        self.top = int.from_bytes(file.read(2), 'big')
        self.left = int.from_bytes(file.read(2), 'big')
        self.bottom = int.from_bytes(file.read(2), 'big')
        self.right = int.from_bytes(file.read(2), 'big')

    def __repr__(self):
        return 't=' + str(self.top) + ' l=' + str(self.left) + ' b=' + str(self.bottom) + ' r=' + str(self.right)

    def to_bytes(self):
        return self.top.to_bytes(2, byteorder='big') + \
               self.left.to_bytes(2, byteorder='big') + \
               self.bottom.to_bytes(2, byteorder='big') + \
               self.right.to_bytes(2, byteorder='big')


class TextSampleEntry(SampleEntry):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self.display_flags = int.from_bytes(file.read(4), 'big')
            self.horizontal_justification = int.from_bytes(file.read(1), 'big', signed=True)
            self.vertical_justification = int.from_bytes(file.read(1), 'big', signed=True)
            self.background_color_rgba = []
            for i in range(4):
                self.background_color_rgba.append(int.from_bytes(file.read(1), 'big'))
            self.default_text_box = BoxRecord(file)
            self.default_style = StyleRecord(file)
            self.font_table = FontTableBox(file=file, depth=self._depth)

    def __repr__(self):
        ret = super().__repr__() + ' flags=' + hex(self.display_flags) + ' justification=(' +\
              str(self.horizontal_justification) + ' ' + str(self.vertical_justification)
        ret += ' bg color=[ '
        for cl in self.background_color_rgba:
            ret += str(cl) + ' '
        ret += '] default textbox={' + str(self.default_text_box) + '} default style={' + str(self.default_style) + \
               '} font table=' + str(self.font_table)
        return ret

    def to_bytes(self):
        ret = super().to_bytes()
        ret += self.display_flags.to_bytes(4, byteorder='big')
        ret += self.horizontal_justification.to_bytes(1, byteorder='big', signed=True)
        ret += self.vertical_justification.to_bytes(1, byteorder='big', signed=True)
        for cl in self.background_color_rgba:
            ret += cl.to_bytes(1, byteorder='big')
        ret += self.default_text_box.to_bytes()
        ret += self.default_style.to_bytes()
        ret += self.font_table.to_bytes()
        return ret


class Box(atom.FullBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        self.entries = []
        self.video_stream_type = VideoCodecType.UNKNOWN
        if file is not None:
            self._readfile(file, kwargs.get('hdlr', None))

    def __repr__(self):
        return super().__repr__() + '\n'.join(map(lambda x: str(x), self.entries))

    def normalize(self):
        self.size = 16
        for entry in self.entries:
            self.size += entry.size

    def _readfile(self, file, handler):
        count = int.from_bytes(self._readsome(file, 4), "big")
        if handler is not None:
            for i in range(count):
                if handler == 'vide':
                    entry = VisualSampleEntry(file=file, depth=self._depth+1)
                    if entry.advanced_vcc_box is not None:
                        self.video_stream_type = VideoCodecType.AVC
                    elif entry.high_vcc_box is not None:
                        self.video_stream_type = VideoCodecType.HEVC
                    self.entries.append(entry)
                elif handler == 'soun':
                    self.entries.append(AudioSampleEntry(file=file, depth=self._depth+1))
                elif handler == 'text':
                    self.entries.append(TextSampleEntry(file=file, depth=self._depth+1))

    def to_bytes(self):
        ret = super().to_bytes()
        ret += len(self.entries).to_bytes(4, byteorder='big')
        for s in self.entries:
            ret += s.to_bytes()
        return ret
