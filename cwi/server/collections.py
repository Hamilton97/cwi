from typing import Callable
from cwi.server.bmath import *
from cwi.server.cmasking import mask_l8_sr



class LandSAT8Builder:
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
    
    def filter_by_date(self):
        self.collection = self.collection.filterDate('2018', '2020')
        return self
    
    def add_doy_filter(self):
        self.collection = self.colleciton.filter(ee.Filter.dayOfYear(135, 288))
        return self
    
    def add_cloud_mask(self):
        self.collection = self.collection.map(mask_l8_sr)
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
    POL = {'DV': 'V.*' }
    def __init__(self):
        self.collection = ee.ImageCollection("COPERNICUS/S1_GRD")
        self.pol = 'DV'

    def set_dv_collection(self) -> ee.ImageCollection:
        self.collection = self.collection.filter(ee.Filter([
            ee.Filter.listContains("transmitterReceiverPolarisation", "VV"),
            ee.Filter.listContains("transmitterReceiverPolarisation", "VH"),
            ee.Filter.eq("instrumentMode", "IW")
        ]))
        return self

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
        self._collection = self._collection.select(self.POL[self.pol])
        return self

    def build(self):
        return self


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
        return self


class NASADEMBuilder:
    def __init__(self):
        self.collection = ee.Image("NASA/NASADEM_HGT/001")

    def add_slope(self):
        self.collection = self.collection.addBands(
            ee.Terrain.slope(self.collection.select("elevation"))
        )
        return self

    def select(self):
        self.collection = self.collection.select("elevation")
        return self

    def build(self):
        return self


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
        if ['x', 'y'] not in self.props:
            raise ValueError("xy not in props, you need to add x,y columns to dataset")
        self.collection = self.collection.map(lambda elem: elem.setGeometry(ee.Geometry.Point([elem.get('x'), elem.get('y')])))
        return self

    def build(self) -> ee.FeatureCollection:
        return self.collection
