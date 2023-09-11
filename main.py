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
    b = " "
    s1bldr = (
        cwi.Sentinel1DVBuilder()
        .filter_date()
        .filter_by_geometry()
        .denoise()
        .add_ratio()
        .build()
    )

    a2bldr = (
        cwi.ALOS2Builder().filter_date().denoise().add_ratio().select_bands().build()
    )

    nsbldr = cwi.NASADEMBuilder().add_slope().build()

    stack = ee.Image.cat()

    tp = (
        cwi.TrainingPoints(ee.FeatureCollection(), "B_Class")
        .add_random_col()
        .add_xy()
        .add_value()
        .sample_regions(stack)
        .build()
    )

    rfmodel = cwi.RandomForestClassifier().train(
        features=tp, class_property="value", predictors=stack.bandNames()
    )


if __name__ == "__main__":
    ee.Initialize()
    main()
