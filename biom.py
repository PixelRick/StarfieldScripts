from pathlib import Path
from construct import Struct, Const, Rebuild, this, len_
from construct import Int32ul as UInt32, Int16ul as UInt16, Int8ul as UInt8
import csv
import numpy as np
import plotly.graph_objects as plgo
#from PIL import Image

GRID_SIZE = [0x100, 0x100]
GRID_FLATSIZE = GRID_SIZE[0] * GRID_SIZE[1]

CsSF_Biom = Struct(
    "magic" / Const(0x105, UInt16),
    "_numBiomes" / Rebuild(UInt32, len_(this.biomeIds)),
    "biomeIds" / UInt32[this._numBiomes],
    Const(2, UInt32),
    Const(GRID_SIZE, UInt32[2]),
    Const(GRID_FLATSIZE, UInt32),
    "biomeGridN" / UInt32[GRID_FLATSIZE],
    Const(GRID_FLATSIZE, UInt32),
    "resrcGridN" / UInt8[GRID_FLATSIZE],
    Const(GRID_SIZE, UInt32[2]),
    Const(GRID_FLATSIZE, UInt32),
    "biomeGridS" / UInt32[GRID_FLATSIZE],
    Const(GRID_FLATSIZE, UInt32),
    "resrcGridS" / UInt8[GRID_FLATSIZE],
)

KNOWN_RESOURCE_IDS = (8, 88, 0, 80, 1, 81, 2, 82, 3, 83, 4, 84)

with open(Path(__file__).parent.resolve() / "./biomes.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=("edid", "id", "name"))
    KNOWN_BIOMES = {int(x["id"], 16): (x["edid"], x["name"]) for x in reader}


def get_biome_names(id):
    entry = KNOWN_BIOMES.get(id, None)
    return entry if entry else (str(id), str(id))


class BiomFile(object):
    def __init__(self):
        self.planet_name = None
        self.biomeIds = set()
        self.resourcesPerBiomeId = dict()
        self.biomeGridN = []
        self.resrcGridN = []
        self.biomeGridS = []
        self.resrcGridS = []

    def load(self, filename):
        assert filename.endswith(".biom")
        with open(filename, "rb") as f:
            data = CsSF_Biom.parse_stream(f)
            assert not f.read()
        self.biomeIds = tuple(data.biomeIds)
        self.biomeGridN = np.array(data.biomeGridN)
        self.biomeGridS = np.array(data.biomeGridS)
        self.resrcGridN = np.array(data.resrcGridN)
        self.resrcGridS = np.array(data.resrcGridS)
        resourcesPerBiomeId = {biomeId: set() for biomeId in self.biomeIds}
        for i, biomeId in enumerate(self.biomeGridN):
            resourcesPerBiomeId[biomeId].add(self.resrcGridN[i])
        for i, biomeId in enumerate(self.biomeGridS):
            resourcesPerBiomeId[biomeId].add(self.resrcGridS[i])
        self.resourcesPerBiomeId = resourcesPerBiomeId
        self.biomesDesc = {
            "{}_{}".format(get_biome_names(id), id): sorted(value)
            for id, value in self.resourcesPerBiomeId.items()
        }
        self.planet_name = Path(filename).stem
        print(f"Loaded '{filename}'.")

    def save(self, filename):
        assert filename.endswith(".biom")
        obj = dict(
            biomeIds=sorted(set(self.biomeGridN) | set(self.biomeGridS)),
            biomeGridN=self.biomeGridN,
            biomeGridS=self.biomeGridS,
            resrcGridN=self.resrcGridN,
            resrcGridS=self.resrcGridS,
        )
        assert len(self.biomeGridN) == 0x10000
        assert len(self.biomeGridS) == 0x10000
        assert len(self.resrcGridN) == 0x10000
        assert len(self.resrcGridS) == 0x10000
        with open(filename, "wb") as f:
            CsSF_Biom.build_stream(obj, f)
        print(f"Saved '{filename}'.")

    def plot2d(self):
        b2i = {id: i for i, id in enumerate(self.biomeIds)}
        b2n = {id: get_biome_names(id) for id in self.biomeIds}
        r2i = {id: i for i, id in enumerate(KNOWN_RESOURCE_IDS)}

        biomeNameGridN = np.reshape([b2n[x][0] for x in self.biomeGridN], GRID_SIZE)
        biomeNameGridS = np.reshape([b2n[x][0] for x in self.biomeGridS], GRID_SIZE)
        biomeShortNameGridN = np.reshape(
            [b2n[x][1] for x in self.biomeGridN], GRID_SIZE
        )
        biomeShortNameGridS = np.reshape(
            [b2n[x][1] for x in self.biomeGridS], GRID_SIZE
        )
        biomeIdxGridN = np.reshape([b2i[x] for x in self.biomeGridN], GRID_SIZE)
        biomeIdxGridS = np.reshape([b2i[x] for x in self.biomeGridS], GRID_SIZE)
        resGridN = np.reshape(self.resrcGridN, GRID_SIZE)
        resGridS = np.reshape(self.resrcGridS, GRID_SIZE)
        resIdxGridN = np.reshape([r2i[x] for x in self.resrcGridN], GRID_SIZE)
        resIdxGridS = np.reshape([r2i[x] for x in self.resrcGridS], GRID_SIZE)

        biomeNameGrid = np.hstack((biomeNameGridN, biomeNameGridS))
        biomeShortNameGrid = np.hstack((biomeShortNameGridN, biomeShortNameGridS))
        biomeIdxGrid = np.hstack((biomeIdxGridN, biomeIdxGridS))
        resGrid = np.hstack((resGridN, resGridS))
        resIdxGrid = np.hstack((resIdxGridN, resIdxGridS))

        combinedGrid = (resIdxGrid + 1) * len(b2i) + biomeIdxGrid * 2

        # fig = plsp.make_subplots(rows=2, cols=1)
        fig = plgo.Figure()
        fig.add_trace(
            plgo.Heatmap(
                z=np.rot90(combinedGrid.T),
                customdata=np.dstack(
                    (
                        np.rot90(biomeNameGrid.T),
                        np.rot90(biomeShortNameGrid.T),
                        np.rot90(resGrid.T),
                    )
                ),
                hovertemplate="%{customdata[0]}<br>%{customdata[1]}<br>resource: %{customdata[2]}",
                colorscale="Cividis",
                showscale=False,
                name="",
            )
        )
        pname = self.planet_name.capitalize()
        space_index = pname.find(" ")
        if space_index > 0:
            pname = pname[:space_index] + pname[space_index:].upper()
        fig.update_layout(
            yaxis=dict(
                scaleanchor="x",
                scaleratio=1,
            ),
            title_text=f"<b>{pname}</b>",
        )
        fig.show()

    def plot3d(self):
        pass
        # todo: recode, that's a puzzle of pasta made during cleaning up

        #hpi = np.pi / 2

        #lat = im[:256, ..., 1]

        #print(lat.shape)

        # lon = np.arctan2(y, x)
        # lon_mod_hpi = np.mod(lon, hpi)
        # lon_angle_from_closest_main_axis = qpi - np.abs(lon_mod_hpi - qpi)
        #d = np.sqrt(x * x + y * y)
        ## d = d * np.cos(lon_angle_from_closest_main_axis)

        #lat = hpi * (1 - d)
        #xs1 = radius * np.cos(-lon) * np.cos(lat)
        #ys1 = radius * np.sin(-lon) * np.cos(lat)
        #zs1 = radius * np.sin(lat)

        #zs1[zs1 < 0] = 0

        #lat = -hpi * (1 - d)
        #xs2 = radius * np.cos(lon + np.pi) * np.cos(lat)
        #ys2 = radius * np.sin(lon + np.pi) * np.cos(lat)
        #zs2 = radius * np.sin(lat)

        #zs2[zs2 > 0] = 0

        #xs = np.hstack((xs1, xs2))
        #ys = np.hstack((ys1, ys2))
        #zs = np.hstack((zs1, zs2))
        #grid = np.hstack((grid1, grid2))

        #sphere = plgo.Surface(
        #    x=xs,
        #    y=ys,
        #    z=zs,
        #    surfacecolor=grid
        #    # surfacecolor=np.reshape(tbl5, (256, 256)).T
        #)
        #fig.add_trace(sphere, 2, 2)
        #fig.show()

        # print(tbl3[:5])
        # print(tbl5[:5])

        # pos = self.tell()
        # if nametbl_offset:
        #    self.seek(nametbl_offset)
        #    self.file_names = tuple(self.read_Name() for _ in range(num_files))
        # self.seek(pos)
        # self.file_entries = tuple(self.read_FileEntry(i) for i in range(num_files))

    # def save_png(self):
    # im2 = Image.fromarray(biome_b).convert('RGB')
    # im2.save(r'./biome_b.png')
    # raise
