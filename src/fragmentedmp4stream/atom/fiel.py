"""Two 8-bit integers that define field handling.
  This information is used by applications to modify decompressed image data
  or by decompressor components to determine field display order.
  This extension is mandatory for all uncompressed Y´CbCr data formats.
  The first byte specifies the field count, and may be set to 1 or 2.
  A value of 1 is used for progressive-scan images; a value of 2 indicates interlaced images.
  When the field count is 2, the second byte specifies the field ordering:
  which field contains the topmost scan-line, which field should be displayed earliest,
  and which is stored first in each sample. Each sample consists of two distinct compressed images,
  each coding one field: the field with the topmost scan-line, T, and the other field, B.
  The following defines the permitted variants:
  0 – There is only one field. 1 – T is displayed earliest,
  T is stored first in the file. 6 – B is displayed earliest, B is stored first in the file.
  9 – B is displayed earliest, T is stored first in the file.
  14 – T is displayed earliest, B is stored first in the file
  """
from .atom import Box as Atom


class Box(Atom):
    """Determines field display order. The first byte specifies the field count,
      the second byte specifies the field ordering"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        file = kwargs.get("file", None)
        if file is not None:
            self.video_field_order = int.from_bytes(self._read_some(file, 2), 'big')

    def __repr__(self):
        return super().__repr__() + " videoFieldOrder:" + str(self.video_field_order)

    def to_bytes(self):
        """Returns sample optional fields as bytestream, ready to be sent to socket"""
        return super().to_bytes() + self.video_field_order.to_bytes(2, byteorder="big")
