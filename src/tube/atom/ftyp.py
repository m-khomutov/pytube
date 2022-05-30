"""File type and compatibility"""
from .atom import Box as Atom


def atom_type():
    """Returns this atom type"""
    return 'ftyp'


class Box(Atom):
    """File type and compatibility box"""
    def __init__(self, *args, **kwargs):
        self.major_brand = ''
        self.minor_version = 0
        self._compatible_brands = set()
        super().__init__(*args, **kwargs)

    def __repr__(self):
        ret = super().__repr__() + \
              f" majorBrand:{self.major_brand} minorVersion:{self.minor_version} compatibleBrands:["
        ret += ' '.join(k for k in self._compatible_brands) + ']'
        return ret

    def set_compatible_brands(self, brands):
        old_length = len(self._compatible_brands)
        self._compatible_brands |= brands
        self.size += (len(self._compatible_brands) - old_length) * len(self.major_brand)

    def init_from_file(self, file):
        self.major_brand = self._read_some(file, 4).decode("utf-8")
        self.minor_version = int.from_bytes(self._read_some(file, 4), "big")
        left = int((self.position + self.size - file.tell()) / 4)
        self._compatible_brands = \
            set(map(lambda x: self._read_some(file, 4).decode("utf-8"), range(left)))

    def init_from_args(self, **kwargs):
        self.type = atom_type()
        self.major_brand = kwargs.get('major_brand')
        self.minor_version = kwargs.get('minor_version')
        self._compatible_brands = kwargs.get('compatible_brands')
        self.size += 8 + 4 * len(self._compatible_brands)

    def to_bytes(self):
        ret = super().to_bytes()
        ret += str.encode(self.major_brand) + self.minor_version.to_bytes(4, byteorder='big')
        for brand in self._compatible_brands:
            ret += str.encode(brand)
        return ret
