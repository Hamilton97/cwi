import ee
from cwi.bmath import *


class S2CloudProb:
    def __init__(self, aoi, start, end, cld_px: int = 60):
        self.aoi = aoi
        self.start = start
        self.end = end
        self.cld_px = cld_px

    def get_collection(self) -> ee.ImageCollection:
        sr = (
            ee.ImageCollection("COPERNICUS/S2_SR")
            .filterDate(self.start, self.end)
            .filterBounds(self.aoi)
            .filter(ee.Filter.eq("CLOUDY_PIXEL_PERCENTAGE", self.cld_px))
        )

        cld_prob = (
            ee.ImageCollection("COPERNICUS/S2_SR")
            .filterDate(self.start, self.end)
            .filterBounds(self.aoi)
        )

        return ee.ImageCollection(
            ee.Join.saveFirst("s2cloudless").apply(
                **{
                    "primary": sr,
                    "secondary": cld_prob,
                    "condition": ee.Filter.equals(
                        **{"leftField": "system:index", "rightField": "system:index"}
                    ),
                }
            )
        )


class Sentinel2Builder:
    DOY = {"spring": (), "summer": (), "fall": ()}

    def __init__(self, col: ee.ImageCollection):
        self.collection = col

    def add_ndvi(self):
        calc = ndvi("B8", "B4")
        self.collection = self.collection.map(calc)
        return self

    def add_savi(self):
        self.collection = self.collection.map(savi("B8", "B4"))
        return self

    def add_tasseled_cap(self):
        self.collection = self.collection.map(
            tasseled_cap("B2", "B3", "B4", "B8", "B11", "B12")
        )
        return self

    def build(self):
        spri_filter = ee.Filter.dayOfYear(*self.DOY["spring"])
        summ_filter = ee.Filter.dayOfYear(*self.DOY["summer"])
        fall_filter = ee.Filter.dayOfYear(*self.DOY["fall"])
        return ee.Image.cat(
            self.collection.filter(spri_filter).median(),
            self.collection.filter(summ_filter).median(),
            self.collection.filter(fall_filter).median(),
        )


class Sentinel1DVBuilder:
    def __init__(self):
        self.collection = ee.ImageCollection("COPERNICUS/S1_GRD")

    @property
    def collection(self):
        return self._collection

    @collection.setter
    def collection(self, col):
        self._collection = self._filter_dv(col)

    @staticmethod
    def _filter_dv(col) -> ee.ImageCollection:
        return (
            col.filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
            .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
            .filter(ee.Filter.eq("instrumentMode", "IW"))
        )

    def filter_date(self, start, end):
        self._collection = self._collection.filterDate(start, end)
        return self

    def filter_by_geometry(self, geometry):
        self._collection = self._collection.filterBounds(geometry)
        return self

    def denoise(self):
        self._collection = self._collection.map(
            lambda x: x.convovle(ee.Kernel.square(1))
        )
        return self

    def add_ratio(self):
        self._collection = self._collection.map(ratio("VV", "VH"))
        return self

    def select_bands(self):
        self._collection = self._collection.select("V.*")
        return self

    def build(self) -> ee.Image:
        spri_filter = None
        summ_filter = None
        return ee.Image.cat(
            self._collection.filter(spri_filter).median(),
            self._collection.filter(summ_filter).median(),
        )


class ALOS2Builder:
    def __init__(self):
        self._collection = ee.ImageCollection("JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH")

    def filter_date(self, start, end):
        self._collection = self._collection.filterDate(start, end)
        return self

    def denoise(self):
        self._collection = self._collection.map(
            lambda x: x.convovle(ee.Kernel.square(1))
        )
        return self

    def add_ratio(self):
        self._collection = self._collection.map(ratio("HH", "HV"))
        return self

    def select_bands(self):
        self._collection = self._collection.select("H.*")
        return self

    def build(self) -> ee.ImageCollection:
        return self._collection


class NASADEMBuilder:
    def __init__(self):
        self.image = ee.Image("NASA/NASADEM_HGT/001")

    def add_slope(self):
        self.image = self.image.addBands(
            ee.Terrain.slope(self.image.select("elevation"))
        )
        return self

    def build(self) -> ee.Image:
        return self.image


class TrainingPoints:
    def __init__(self, feat_col, label_col):
        self.collection = feat_col
        self.label_col = label_col
        self.props = []

    def __append_prop(self, value):
        if isinstance(value, str) and value not in self.props:
            self.props.append(value)
        if isinstance(value, list) and value not in self.props:
            self.props.extend(value)

    def add_xy(self):
        def _add_xy(feature: ee.Feature):
            feat = ee.Feature(feature).geometry()
            x = feat.coordinates().get(0)
            y = feat.coordinates().get(1)
            return feature.set("x", x, "y", y)

        self.collection = self.collection.map(_add_xy)
        self.__append_prop(["x", "y"])
        return self

    def add_y(self):
        self.collection = self.collection.map()
        self.__append_prop("y")
        return self

    def add_random_col(self):
        labels = self.collection.aggregate_array(self.label_col).distinct()
        tables = labels.map(
            lambda x: self.collection.filter(
                ee.Filter.eq(self.label_col, x)
            ).randomColumn()
        )
        self.collection = ee.FeatureCollection(tables).flatten()
        self.__append_prop("random")
        return self

    def add_value(self, order: list[int] | ee.List = None):
        labels = self.collection.aggregate_array(self.label_col).distinct()
        order = ee.List.sequence(1, labels.size()) if order is None else order

        lookup = ee.Dictionary.fromList(labels, order)
        self.collection = self.collection.map(
            lambda x: x.set("value", lookup.get(x.get(self.label_col)))
        )
        return self

    def sample_regions(self, image):
        samples = image.sampleRegions(
            collection=self.collection, properties=self.props, tileScale=16, scale=10
        )
        props = self.props
        self.collection = TrainingPoints(samples, self.label_col)
        self.collection.props = props
        return self

    def build(self) -> ee.FeatureCollection:
        return self.collection
