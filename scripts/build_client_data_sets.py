import geopandas as gpd
import pandas as pd

from cwi.client.datautils import DataSetBuilder, SamplePopulation

OVERWRITE = False

if __name__ == "__main__":
    ds_bldr = (
        DataSetBuilder()
        .get_files(root_dir="Y:\Wetlands\CNWI\working\cnwi-pipeline\priority-areas")
        .load_files()
        .load_layer()
        .add_region_ids()
        .add_ecozones()
        .add_values()
        .write()
    )

    samp_bldr = SamplePopulation(ds_bldr.data).sample_population().write()
