# Canadian Wetland Inventory (CWI)
Provide standard tool set to complete the rest of the country. Everything south of 60, excluding the 14 priority areas

## Installation
```shell
pip install -e .
```

## Example Usage
```python
import ee

import cwi


def main():
    table = ee.FeatureCollection(
        "projects/earthengine-legacy/assets/users/ryangilberthamilton/randForestTrain_bq"
    )
    aoi = table.geometry().bounds()

    cloud_prob = cwi.S2CloudProb(
        aoi, start="2019-04-01", end="2019-10-31"
    ).get_collection()

    # trim collection by day of year

    s2_cloudless = (
        cwi.S2CloudlessBuilder(cloud_prob)
        .add_cloud_bands()
        .add_shadow_bands()
        .add_cld_shdw_mask()
        .apply_cld_shdw_mask()
        .build()
    )

    s2bldr = (
        cwi.Sentinel2Builder(s2_cloudless.collection)
        .add_savi()
        .add_ndvi()
        .add_tasseled_cap()
        .build()
    )

    s1bldr = (
        cwi.Sentinel1DVBuilder()
        .filter_date(start="2019-04-01", end="2019-10-31")
        .filter_by_geometry(aoi)
        .denoise()
        .add_ratio()
        .select_bands()
        .build()
    )

    a2bldr = (
        cwi.ALOS2Builder()
        .filter_date("2019", "2020")
        .denoise()
        .add_ratio()
        .select_bands()
        .build()
    )

    nsbldr = cwi.NASADEMBuilder().select().add_slope().build()

    stack = ee.Image.cat(s1bldr, s2bldr, a2bldr, nsbldr)

    tp = (
        cwi.TrainingPoints(table, "B_Class")
        .add_random_col()
        .add_xy()
        .add_value()
        .sample_regions(stack)
        .build()
    )
    
    train = tp.filter(ee.Filter.lte('random', 0.7))
    test = tp.filter(ee.Filter.gt('random', 0.7))
    rfmodel = cwi.RandomForestClassifier().train(
        features=train, class_property="value", predictors=stack.bandNames()
    )

    classification = rfmodel.classify(stack)


if __name__ == "__main__":
    ee.Initialize()
    main()

```