import os
import re
import pickle
import shutil
import geopandas as gpd
import pandas as pd
from pathlib import Path
from glob import glob

from cwi.client import PACKAGEDIR


def copy_data(pattern: str, dest: str) -> dict[int, str]:
    """Copies cnwi trianing data from cnwipipeline to working dir for further processing

    Args:
        pattern (str): glob pattern for recursive file retriaval
        dest (str): destination directory
    """
    src_files = glob(pattern, recursive=True)

    if len(src_files) == 0:
        raise ValueError(f"The pattern {pattern} returned an empty list")

    if not os.path.exists(dest):
        os.makedirs(dest)

    for src in src_files:
        region_id = re.findall(r"\b\d{2,3}\b", src)[0]
        filename = os.path.basename(src)
        dest_path = os.path.join(dest, region_id, filename)
        if os.path.exists(dest_path):
            continue
        shutil.copy(src, dest_path)


def load_files(pattern) -> dict[int, gpd.GeoDataFrame]:
    """loads all files into seperate dataframes"""
    files = glob(pattern, recursive=True)
    if len(files) == 0:
        raise ValueError("The pattern {pattern} returned an empty list")

    gdfs = {}
    for file in files:
        region_id = re.findall(r"\b\d{2,3}\b", file)[0]
        gdf = gpd.read_file(file, driver="ESRI Shapefile")
        gdfs[int(region_id)] = gdf

    return gdfs


class DataSetBuilder:
    def __init__(self) -> None:
        self.data = None
        self.layer = None

    def load_files(self, pattern: str) -> dict[int, gpd.GeoDataFrame]:
        """loads all files into seperate dataframes"""
        files = glob(pattern, recursive=True)
        if len(files) == 0:
            raise ValueError(f"The pattern {pattern} returned an empty list")

        gdfs = {}
        for file in files:
            region_id = re.findall(r"\b\d{2,3}\b", file)[0]
            gdf = gpd.read_file(file, driver="ESRI Shapefile")
            gdfs[int(region_id)] = gdf

        self.data = gdfs
        return self

    def load_layer(self):
        with open(os.path.join(PACKAGEDIR, "data", "layer"), "rb") as data:
            self.layer = pickle.loads(data)
        return self

    def add_region_ids(self) -> gpd.GeoDataFrame:
        """inserts the key into a column called ECOREGIONS
        the Key is assumed to be the region id"""
        gdfs = []
        for k, v in gdfs.items():
            v["ECOREGION"] = k
            gdfs.append(v)
        self.data = pd.concat(gdfs)
        return self

    def add_zones_id(self):
        """joins the eco_ids layer on ECOREGION Column"""
        if self.layer is None:
            raise ValueError("Layer is None cannot join zones, load layer first")
        pass

    def add_zones_name(self):
        pass

    def build(self):
        return self
