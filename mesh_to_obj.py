from struct import unpack, iter_unpack
import os

class BethMesh(object):
    def __init__(self):
        self.filename = None
        self.datasize = 0
        self._f = None
        self.indices = []
        self.vertices = []
        self.UV1s = []
        self.UV2s = []
        self.colors = []

    def tell(self):
        return self._f.tell()

    def read(self, n):
        return self._f.read(n)
    
    def load(self, filename):
        assert filename.endswith('.mesh')
        print(f"Loading '{filename}'")
        with open(filename, 'rb') as f:
            self._f = f
            f.seek(0, 2)
            fsize = f.tell()
            f.seek(0)
            self.datasize = fsize
            self.loadf()
        self._f = None
		
    def loadf(self):
        version, = unpack('=I', self.read(4))
        assert version == 1

        # Number of indices
        nIndices, = unpack('=I', self.read(4))
        print(f"nIndices: {nIndices}")

        # Indices: nIndices * (uint16, uint16, uint16)
        self.indices = [x for x in iter_unpack('=HHH', self.read(nIndices * 2))]
        
        # Scale, Number of weights per vertex, Number of vertices
        scale, nWeightsPerVertex, nVertices, = unpack('=fII', self.read(12))
        print(f"nVertices: {nVertices}")
        print(f"scale: {scale}")

        scale = scale / 32767.0

        # Packed Vertices: nVertices * (int16, int16, int16)
        packed_vertices = [x for x in iter_unpack('=hhh', self.read(nVertices * 3 * 2))]
        self.vertices = [(float(x) * scale, float(y) * scale, float(z) * scale) for x, y, z in packed_vertices]

        # Number of UV_1 coordinates
        nUV1s, = unpack('=I', self.read(4))
        assert nUV1s == nVertices

        # UV_1 coordinates: nUV1s * (float16, float16)
        self.UV1s = [x for x in iter_unpack('=ee', self.read(nUV1s * 2 * 2))]

        # Number of UV_2 coordinates
        nUV2s, = unpack('=I', self.read(4))
        assert nUV2s in (0, nVertices)

        # UV_2 coordinates: nUV2s * (float16, float16)
        self.UV2s = [x for x in iter_unpack('=ee', self.read(nUV2s * 2 * 2))]

        # Number of colors
        nColors, = unpack('=I', self.read(4))
        assert nColors in (0, nVertices)

        # Colors: nColors * (uint8, uint8, uint8, uint8)
        colors = [x for x in iter_unpack('=BBBB', self.read(nColors * 4))]
    
        # Number of normals
        nNormals, = unpack('=I', self.read(4))
        assert nNormals == nVertices

        # Normals: nNormals * (X10Y10Z10W2)
        packed_normals = [x for x in iter_unpack('=I', self.read(nNormals * 4))]

        # Number of tangents
        nTangents, = unpack('=I', self.read(4))
        assert nTangents == nVertices

        # Tangents: nTangents * (X10Y10Z10W2)
        packed_tangents = [x for x in iter_unpack('=I', self.read(nTangents * 4))]

        # Number of weights
        nWeights, = unpack('=I', self.read(4))
        assert nWeights == nWeightsPerVertex * nVertices

        # Weigths: nTangents * (X10Y10Z10W2)
        weights = [x for x in iter_unpack('=I', self.read(nWeights * 4))]

        # Number of LODs
        nLODs, = unpack('=I', self.read(4))

        # LODs: nLODs * (uint32 nLODIndices, nLODIndices * uint16)
        def readLOD(n):
            return [x for x in iter_unpack('=H', self.read(n * 2))]
        LODs = [readLOD(unpack('=I', self.read(4))[0]) for _ in range(nLODs)]

        # -------------------  The remaining data is optional, the file may end here.
        # uint32               Number of meshlets (n5).
        # n5 * 16 bytes        Meshlet data.
        # uint32               Number of bounding spheres (bndCnt).
        # {
        #     float32          Bounding sphere center X.
        #     float32          Bounding sphere center Y.
        #     float32          Bounding sphere center Z.
        #     float32          Bounding sphere radius.
        #     8 bytes          Unknown data.
        # } * bndCnt

    # only triangles with uvs, no normals
    def save_as_obj(self, fpath):
        with open(fpath, 'w') as f:
            for v in self.vertices:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            for uv in self.UV1s:
                f.write(f"vt {uv[0]} {uv[1]}\n")#
            for a, b, c in self.indices:
                f.write(f"f {a+1}/{a+1} {b+1}/{b+1} {c+1}/{c+1}\n")

            # List of geometric vertices, with (x, y, z, [w]) coordinates, w is optional and defaults to 1.0.
            #v 0.123 0.234 0.345 1.0
            #v ...
            #...
            ## List of texture coordinates, in (u, [v, w]) coordinates, these will vary between 0 and 1. v, w are optional and default to 0.
            #vt 0.500 1 [0]
            #vt ...
            #...
            ## List of vertex normals in (x,y,z) form; normals might not be unit vectors.
            #vn 0.707 0.000 0.707
            #vn ...
            #...
            ## Parameter space vertices in (u, [v, w]) form; free form geometry statement (see below)
            #vp 0.310000 3.210000 2.100000
            #vp ...
            #...
            ## Polygonal face element (see below)
            #f 1 2 3
            #f 3/1 4/2 5/3
            #f 6/4/1 3/5/3 7/6/5
            #f 7//1 8//2 9//3
            #f ...
            #...
            ## Line element (see below)
            #l 5 8 1 2 4 9

if 0:        
    mesh = BethMesh()
    mesh.load(os.path.join(r"./", 'da3af0033b74cd91e41f.mesh'))
    mesh.save_as_obj(r"./test.obj")
