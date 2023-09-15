import os
import ee
import cwi

import pandas as pd
import pickle

from cwi.client.datautils import TableDataSets
from cwi.server.funcs import stack
from cwi.server import PACKAGEDIR


if __name__ == "__main__":
    ee.Initialize()

    # load client files
    client_table = TableDataSets().load()
    sampled = client_table.get_dataset("processed")

    grouped = sampled.groupby("ECOZONE_NAME")
    assets = {"name": [], "id": []}
    for group_name, grouped_df in grouped:
        if not ee.data._credentials:
            ee.Initialize()
        fc = ee.FeatureCollection(grouped_df.__geo_interface__)
        img = stack(fc)
        # build Training Points
        tp = (
            cwi.TrainingPointsBuilder(fc, "class_name", "value")
            .add_xy()
            .sample_regions(img, scale=30)
            .set_xy_geometry()
            .build()
        )
        name = group_name.split()
        if len(name) > 1:
            name = "-".join(name)
        else:
            name = name[0]
        asset_id = f"projects/ee-nwrc-geomatics/assets/cwiops/{name}"
        task = ee.batch.Export.table.toAsset(
            collection=tp,
            description="",
            assetId=asset_id,
        )

        assets["name"].append(name)
        assets["id"].append(asset_id)
        task.start()

        ee.Reset()
        tp = None

    df = pd.DataFrame(data=assets)

    with open(os.path.join(PACKAGEDIR, "data", "assets"), "wb") as file:
        pickle.dump(df, file)
