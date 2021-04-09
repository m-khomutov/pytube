from .atom import Box


class Box(Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = kwargs.get("file", None)
        if f != None:
            self.majorBrand = self._readsome(f, 4).decode("utf-8")
            self.minorVersion = int.from_bytes(self._readsome(f, 4), "big")
            left=int((self.position + self.size - f.tell()) / 4)
            self.compatible_brands=[]
            for i in range(left):
                self.compatible_brands.append(self._readsome(f, 4).decode("utf-8"))
        pass

    def __repr__(self):
        ret = super().__repr__() + " majorBrand:" + self.majorBrand +\
                                   " minorVersion:" + str(self.minorVersion) +\
                                   " compatibleBrands:[ "
        for brand in self.compatible_brands:
            ret += brand + " "
        ret += "]"

        return ret

    def encode(self):
        ret = super().encode()
        ret += str.encode(self.majorBrand)
        ret += self.minorVersion.to_bytes(4, byteorder='big')
        for brand in self.compatible_brands:
            ret += str.encode(brand)
        return ret