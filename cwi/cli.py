import ee
import click
import geopandas as gpd
import pandas as pd
from . import commands as c


@click.group()
def cli():
    pass


@cli.command()
@click.argument("src")
def init(src):
    """sets the inital state of the project"""
    c.init(src_dir=src)


@cli.command()
def add_dataset():
    """adds dataset to the project src"""
    click.echo("adding dataset to project")


@cli.command()
def get_datasets():
    try:
        c.get_dataset()
    except ValueError as ve:
        click.echo(ve)
    except FileExistsError as fee:
        click.echo(fee)


@cli.command()
@click.option("n", "-n", type=int, default=650, required=False, help="Sample Size")
def process_dataset(n):
    """samples client dataset the dataset"""

    df = gpd.read_file("data/raw/raw.geojson")
    procd = c.sample(df, n, "class_name")
    procd.to_file("data/processed/process.geojson")


@cli.command()
@click.option("d", "-d", default="projects/ee-nwrc-geomatics/assets/cwiops")
def sample(d):
    """generates samples in ee exports to asset store"""
    ee.Initialize()

    assets = {"assetid": [], "ecozone_name": [], "ecozone_id": []}
    gdf = gpd.read_file("data/processed/process.geojson", driver="GeoJSON")

    ee_samp = c.sever_sampels(gdf)

    name = gdf["ECOZONE_NAME"].unique().tolist()[0].split()
    z_id = gdf["ECOZONE_ID"].unique().tolist()[0]
    if len(name) > 1:
        name = "-".join(name).lower()
    else:
        name = name[0]
    assetid = f"{d}/{name}"
    assets["assetid"].append(assetid)
    assets["ecozone_name"].append(name)
    assets["ecozone_id"].append(z_id)

    df = pd.DataFrame(data=assets)
    df.to_csv("asset.csv")

    task = ee.batch.Export.table.toAsset(
        collection=ee_samp, description="", assetId=assetid
    )

    task.start()


@cli.command()
def classify():
    pass
