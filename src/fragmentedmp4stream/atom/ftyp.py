"""File type and compatibility"""
from .atom import Box as Atom


def atom_type():
    """Returns this atom type"""
    return 'ftyp'


class Box(Atom):
    """File type and compatibility box"""

    def __repr__(self):
        ret = super().__repr__() + \
              f" majorBrand:{self.major_brand} minorVersion:{self.minor_version} compatibleBrands:["
        ret += ' '.join(k for k in self.compatible_brands) + ']'
        return ret

    def _init_from_file(self, file):
        self.major_brand = self._read_some(file, 4).decode("utf-8")
        self.minor_version = int.from_bytes(self._read_some(file, 4), "big")
        left = int((self.position + self.size - file.tell()) / 4)
        self.compatible_brands = \
            list(map(lambda x: self._read_some(file, 4).decode("utf-8"), range(left)))

    def to_bytes(self):
        ret = super().to_bytes()
        ret += str.encode(self.major_brand) + self.minor_version.to_bytes(4, byteorder='big')
        for brand in self.compatible_brands:
            ret += str.encode(brand)
        return ret
