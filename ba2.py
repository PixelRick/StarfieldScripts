from struct import unpack, unpack_from, calcsize
from collections import namedtuple
import binascii
import lz4.frame as lz4f
import zlib
import io
import os

FileEntry = namedtuple('FileEntry', (
    'name',
    'namehash',
    'ext',
    'dirhash',
    #
    'flags',
    'offset',
    'packsize',
    'fullsize',
    'align'
))

TexEntry = namedtuple('TexEntry', (
    'name',
    'namehash',
    'ext',
    'dirhash',
    #
    'unk1',
    'nchunks',
    'hdrlen',
    'height',
    'width',
    'nmips',
    'fmt',
    'iscube',
    'tiling',
    'chunks'
))

TexChunkEntry = namedtuple('TexChunkEntry', (
    'offset',
    'packsize',
    'fullsize',
    'mip0',
    'mipN',
    'align'
))

class Ba2Reader(object):
    def __init__(self):
        self.filename = None
        self.datasize = 0
        self._data = b''
        self._pos = 0
        self.kind = b''
        self.file_entries = ()
        self.file_names = ()
        self.nametbl_size = 0

    def seek(self, ofs, whence=0):
        if whence == 0:
            self._pos = ofs
        elif whence == 1:
            self._pos += ofs
        elif whence == 2:
            self._pos = self.datasize - ofs
        else:
            raise ValueError('invalid whence value')
        if not 0 <= self._pos <= self.datasize:
            raise ValueError('out of bounds seek')

    def tell(self):
        return self._pos

    def read(self, n):
        start_pos = self._pos
        self._pos += n
        return self._data[start_pos:self._pos]
    
    @staticmethod
    def load(filename):
        instance = Ba2Reader()
        instance.load_(filename)
        return instance
    
    def load_(self, filename):
        assert filename.endswith('.ba2')
        with open(filename, 'rb') as f:
            f.seek(0, 2)
            fsize = f.tell()
            f.seek(0)
            self._data = f.read(fsize)
        self.datasize = len(self._data)
        magic, version, kind, num_files, nametbl_offset, unk1, unk2 = unpack('=4sI4sIQII', self.read(32))
        self.nametbl_size = fsize - nametbl_offset
        assert magic == b'BTDX'
        #assert version == 2
        self.kind = kind
        print(f"Loading '{kind.decode('latin-1')}' archive of {num_files} files.")
        pos = self.tell()
        if nametbl_offset:
            self.seek(nametbl_offset)
            self.file_names = tuple(self.read_Name() for _ in range(num_files))
        self.seek(pos)
        if kind == b'GNRL':
            assert version == 2
            self.file_entries = tuple(self.read_FileEntry(i) for i in range(num_files))
        if kind == b'DX10':
            print(f"version: {version}")
            assert version == 3
            unk3, = unpack('=I', self.read(4))
            self.file_entries = tuple(self.read_TexEntry(i) for i in range(num_files))

    def read_FileEntry(self, i):
        x = unpack('=I4sIIQIII', self.read(36))
        return FileEntry(self.file_names[i], x[0], x[1].rstrip(b'\x00').decode('latin-1'), *x[2:])
    
    def read_TexEntry(self, i):
        x = unpack('=I4sIBBHHHBBBB', self.read(24))
        chunks = tuple(self.read_TexChunkEntry() for _ in range(x[4]))
        return TexEntry(self.file_names[i], x[0], x[1].rstrip(b'\x00').decode('latin-1'), *x[2:], chunks)
  
    def read_TexChunkEntry(self):
        x = unpack('=QIIHHI', self.read(24))
        return TexChunkEntry(*x)

    def read_Name(self):
        cnt = unpack('=H', self.read(2))[0]
        return self.read(cnt).decode('latin-1')

    def extract(self, i):
        fe = self.file_entries[i]
        if self.kind == b'GNRL':
            self.seek(fe.offset)
            packsize = fe.packsize if fe.packsize else fe.fullsize
            data = self.read(packsize)
            print(fe.name, fe.packsize, fe.fullsize, binascii.hexlify(bytearray(data[:10])).decode('ascii'))
            ofpath, ofname = os.path.split(fe.name)
            decompressed = data
            if fe.fullsize != packsize:
                decompressed = zlib.decompress(data)
            if not os.path.exists(ofpath):
                os.makedirs(ofpath)
            with open(os.path.join(ofpath, ofname), 'wb') as f:
                f.write(decompressed)
            assert len(decompressed) == fe.fullsize
        if self.kind == b'DX10':
            pass

if 0:
    import pathlib
    datadir = pathlib.Path(r"G:/Xbox/Starfield/Content/Data/")
    for item in datadir.glob("*.ba2"):
       reader = Ba2Reader.load(str(item))
       print(f"{item} -> nametbl is {reader.nametbl_size} bytes")

if 0:
    reader = Ba2Reader.load(r"G:/Xbox/Starfield/Content/Data/Starfield - Textures01.ba2")
    for i, e in enumerate(reader.file_entries):
        name = str(e.name)
        if ".swf" in name:
            continue
        if ".txt" in name:
            continue
        if ".gfx" in name:
            continue
        print(name)
        if "andraphon" in e.name:
            print(e)
            #reader.extract(i)
