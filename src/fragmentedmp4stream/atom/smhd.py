"""The sound media header contains general presentation information,
   independent of the coding, for audio media
"""
from .atom import FullBox, full_box_derived


def atom_type():
    """Returns this atom type"""
    return 'smhd'


@full_box_derived
class Box(FullBox):
    """Sound media header, overall information (sound track only"""
    balance = 0

    def __repr__(self):
        return super().__repr__() + f" balance:{self.balance}"

    def init_from_file(self, file):
        self.balance = int.from_bytes(self._read_some(file, 2), "big")
        self._read_some(file, 2)

    def to_bytes(self):
        ret = super().to_bytes() + \
              self.balance.to_bytes(2, byteorder='big') + \
              (0).to_bytes(2, byteorder='big')
        return ret
