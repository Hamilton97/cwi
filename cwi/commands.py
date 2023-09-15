import ee
import os
import re
import pandas as pd
import geopandas as gpd

import cwi
from cwi.server import funcs
from cwi import PACKAGEDIR


def init(src_dir: str) -> None:
    data = {"src": [], "ECOREIGON_ID": []}

    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if "training" in file and file.endswith(".shp"):
                src_file = os.path.join(root, file)
                data["src"].append(src_file)
                data["ECOREIGON_ID"].append(
                    int(re.findall(r"\b\d{2,3}\b", src_file)[0])
                )

    df1 = pd.DataFrame(data=data)
    zones = pd.read_csv(os.path.join(PACKAGEDIR, "data", "zones.csv"))

    df = pd.merge(df1, zones, on="ECOREIGON_ID", how="inner")
    df.to_csv("src.csv")

    grouped = df.groupby("ECOZONE_NAME")

    for name, group in grouped:
        if not os.path.exists(name):
            os.mkdir(name)
            os.makedirs(os.path.join(name, "data", "processed"))
            os.makedirs(os.path.join(name, "data", "raw"))

            group.to_csv(os.path.join(name, "datasource.csv"))


def get_dataset():
    if not os.path.exists("datasource.csv"):
        raise ValueError("datasource.csv is not present in the current dir")
    if os.path.exists("data/raw/raw.geojson"):
        raise FileExistsError("raw.geojson already exits")

    raw = []
    srcs = pd.read_csv("datasource.csv")
    for idx, row in srcs.iterrows():
        gdf = gpd.read_file(row["src"])
        gdf["ECOREIGON_ID"] = row["ECOREIGON_ID"]
        gdf["ECOZONE_ID"] = row["ECOZONE_ID"]
        gdf["ECOZONE_NAME"] = row["ECOZONE_NAME"]
        raw.append(gdf)

    raw = gpd.GeoDataFrame(pd.concat(raw))
    labels = raw["class_name"].unique().tolist()
    values = list(range(1, len(labels) + 1))
    lookup = pd.DataFrame(data={"class_name": labels, "values": values})
    raw = pd.merge(raw, lookup, on="class_name", how="inner")
    raw.to_file("data/raw/raw.geojson", driver="GeoJSON")


def sample(df, n, groupby):
    return df.groupby(groupby).sample(n=n)


def sever_sampels(gdf) -> ee.FeatureCollection:
    if gdf.crs.to_epsg() != 4326:
        gdf.to_crs(epsg=4326, inplace=True)

    fc = ee.FeatureCollection(gdf.__geo_interface__)
    img = funcs.stack(fc)
    tp = (
        cwi.TrainingPointsBuilder(fc, "class_name", value_col="values")
        .add_xy()
        .sample_regions(img, scale=30)
        .set_xy_geometry()
        .build()
    )
    return tp
