from .atom import Box


class Box(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self.video_field_order = int.from_bytes(self._readsome(f, 2), 'big')
    def __repr__(self):
        return super().__repr__() + " videoFieldOrder:" + str(self.video_field_order)
    def encode(self):
        return super().encode() + (self.video_field_order).to_bytes(2, byteorder="big")
