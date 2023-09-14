# import ee
from typing import Callable
from cwi.bmath import *



class LandSAT8Builder:
    DOY = {"spring": (135, 181), "summer": (182, 243), "fall": (244, 288)}
    def __init__(self) -> None:
        self.collection: ee.ImageCollection = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
    
    @property
    def collection(self) -> None:
        return self._collection

    @collection.setter
    def collection(self, collection: ee.ImageCollection):
        if not isinstance(collection, ee.ImageCollection):
            raise TypeError("Collection must be an ImageCollection")
        else:
            self._collection = collection

    def filter_by_geometry(self, geometry: ee.Geometry):
        self.collection = self.collection.filterBounds(geometry)
        return self
    
    def filter_by_date(self, *args):
        self.collection = self.collection.filterDate(*args)
        return self
    
    def add_cloud_mask(self, func: Callable):
        self.collection = self.collection.map(func)
        return self
    
    def add_ndvi(self):
        self.collection = self.collection.map(ndvi(nir='SR_B6', red='SR_B4'))
        return self
    
    def add_savi(self):
        self.collection = self.collection.map(savi(nir='SR_B6', red='SR_B4'))
        return self
        
    def add_tasseled_cap(self):
        self.collection = self.collection.map(tasseled_cap(
            blue='SR_B2',
            green='SR_B3',
            red='SR_B4',
            swir1='SR_B6',
            swir2='SR_B7'
        ))
        return self
    
    def select_spectral_bands(self):
        self.collection = self.collection.select("SR_.*")
        return self

    def build(self):
        return self


class Sentinel1DVBuilder:
    DOY = {"spring": (135, 181), "summer": (182, 243), "fall": (244, 288)}

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
            lambda x: x.convolve(ee.Kernel.square(1))
        )
        return self

    def add_ratio(self):
        self._collection = self._collection.map(ratio("VV", "VH"))
        return self

    def select_bands(self):
        self._collection = self._collection.select("V.*")
        return self

    def build(self) -> ee.Image:
        return ee.Image.cat(
            self._collection.filter(ee.Filter.dayOfYear(*self.DOY["spring"])).median(),
            self._collection.filter(ee.Filter.dayOfYear(*self.DOY["summer"])).median(),
        )


class ALOS2Builder:
    def __init__(self):
        self._collection = ee.ImageCollection("JAXA/ALOS/PALSAR/YEARLY/SAR_EPOCH")

    def filter_date(self, start, end):
        self._collection = self._collection.filterDate(start, end)
        return self

    def denoise(self):
        self._collection = self._collection.map(
            lambda x: x.convolve(ee.Kernel.square(1))
        )
        return self

    def add_ratio(self):
        self._collection = self._collection.map(ratio("HH", "HV"))
        return self

    def select_bands(self):
        self._collection = self._collection.select("H.*")
        return self

    def build(self) -> ee.ImageCollection:
        return self._collection.first()


class NASADEMBuilder:
    def __init__(self):
        self.image = ee.Image("NASA/NASADEM_HGT/001")

    def add_slope(self):
        self.image = self.image.addBands(
            ee.Terrain.slope(self.image.select("elevation"))
        )
        return self

    def select(self):
        self.image = self.image.select("elevation")
        return self

    def build(self) -> ee.Image:
        return self.image


class TrainingPointsBuilder:
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

        lookup = ee.Dictionary.fromLists(labels, order)
        self.collection = self.collection.map(
            lambda x: x.set("value", lookup.get(x.get(self.label_col)))
        )
        self.__append_prop("value")
        return self

    def sample_regions(self, image, scale: int = 10, tile_scale: int = 16):
        samples = image.sampleRegions(
            collection=self.collection,
            properties=self.props,
            tileScale=tile_scale,
            scale=scale,
        )
        self.collection = samples
        return self
    
    def set_xy_geometry(self):
        pass

    def build(self) -> ee.FeatureCollection:
        return self.collection
