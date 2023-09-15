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

    def get_files(self, root_dir: str):
        """gets files that match a pattern"""
        shp_files = []
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if "training" in file and file.endswith(".shp"):
                    shp_files.append(os.path.join(root, file))
        if len(files) == 0:
            raise ValueError(f"No Shapefiles in this directory: {root_dir}")

        self.data = shp_files
        return self

    def load_files(self) -> dict[int, gpd.GeoDataFrame]:
        """loads all files into seperate dataframes"""

        gdfs = {}
        for file in self.data:
            region_id = re.findall(r"\b\d{2,3}\b", file)[0]
            gdf = gpd.read_file(file, driver="ESRI Shapefile")
            gdfs[int(region_id)] = gdf

        self.data = gdfs
        return self

    def load_layer(self):
        """loads the ecozones layer, contains info on region id, zone id and zone name"""
        with open(os.path.join(PACKAGEDIR, "data", "zones"), "rb") as data:
            self.layer = pickle.load(data).get("regions")[
                [
                    "ECOREIGON_ID",
                    "ECOZONE_ID",
                    "ECOZONE_NAME",
                ]
            ]
        return self

    def add_region_ids(self) -> gpd.GeoDataFrame:
        """inserts the key into a column called ECOREGIONS
        the Key is assumed to be the region id"""
        gdfs = []
        for k, v in self.data.items():
            v["ECOREIGON_ID"] = k
            gdfs.append(v)
        self.data = gpd.GeoDataFrame(pd.concat(gdfs)).to_crs(epsg=4326)
        return self

    def add_ecozones(self):
        """joins the eco_ids layer on ECOREGION Column"""
        if self.layer is None:
            raise ValueError("Layer is None cannot join zones, load layer first")
        if not isinstance(self.data, gpd.GeoDataFrame):
            raise TypeError("self.data must be a DataFrame before proceeding")
        self.data = pd.merge(self.data, self.layer, on="ECOREIGON_ID", how="inner")
        return self

    def add_values(self, on: str = "class_name"):
        """adds an interger representation of the label for the entire population"""
        labels = self.data[on].unique().tolist()
        values = list(range(1, len(labels) + 1))
        lookup = pd.DataFrame(data={on: labels, "value": values})
        self.data = pd.merge(self.data, lookup, on=on, how="inner")
        return self

    def select_south_of_60(self):
        with open(os.path.join(PACKAGEDIR, "data", "south_of_60"), "rb") as file:
            filter = pickle.load(file)
        filter_polygon = filter.geometry.iloc[0]
        self.data = self.data[self.data.geometry.intersects(filter_polygon)]
        return self

    def write(self):
        dst = os.path.join(PACKAGEDIR, "data", "raw")
        with open(dst, "wb") as file:
            pickle.dump(self.data, file)
        return self


def sample_population():
    samples = []
    df = self.data.groupby("ECOZONE_ID")
    for _, group_df in df:
        samples.append(group_df.groupby("class_name").sample(n=self.n))
    self.samples = gpd.GeoDataFrame(pd.concat(samples).reset_index(drop=True))
    return self


class TableDataSets:
    def __init__(self) -> None:
        self.ds: dict = {}

    def load(self):
        pass

    def list_datasets(self):
        return list(self.ds.keys())

    def get_dataset(self, name) -> gpd.GeoDataFrame | None:
        return self.ds.get(name, None)
