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

    def get_files(self, pattern: str):
        """gets files that match a pattern"""
        files = glob(pattern, recursive=True)
        if len(files) == 0:
            raise ValueError("The pattern {pattern} returned an empty list")

        self.data = files
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

    def write(self):
        dst = os.path.join(PACKAGEDIR, "data", "raw")
        with open(dst, "wb") as file:
            pickle.dump({"all": self.data}, file)
        return self


class SamplePopulation:
    def __init__(self, df: gpd.GeoDataFrame, n=650) -> None:
        self.data = df
        self.n = n
        self.samples = None

    def sample_population(self):
        samples = []
        df = self.data.groupby("ECOZONE_ID")
        for _, group_df in df:
            samples.append(group_df.groupby("class_name").sample(n=self.n))
        self.samples = gpd.GeoDataFrame(pd.concat(samples).reset_index(drop=True))
        return self

    def write(self):
        dst = os.path.join(PACKAGEDIR, "data", "processed")
        with open(dst, "wb") as file:
            pickle.dump(self.samples, file)
        return self


class TableDataSets:
    def __init__(self) -> None:
        self.ds: dict = {}

    def load(self):
        with open(os.path.join(PACKAGEDIR, "data", "raw"), "rb") as file:
            raw = pickle.load(file)
        self.ds["raw"] = raw
        with open(os.path.join(PACKAGEDIR, "data", "processed"), "rb") as file:
            processed = pickle.load(file)
        self.ds["processed"] = processed
        return self

    def list_datasets(self):
        return list(self.ds.keys())

    def get_dataset(self, name) -> gpd.GeoDataFrame | None:
        return self.ds.get(name, None)
