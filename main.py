import ee

import cwi


def main():
    s2_cld_prb = cwi.S2CloudProb(aoi, start=2018, end=2020).get_collection()
    # trim collection by day of year

    s2_cloudless = (
        cwi.S2Cloudless(s2_cld_prb)
        .add_cloud_bands()
        .add_shadow_bands()
        .apply_cld_shdw_mask()
        .build()
    )

    s2bldr = (
        cwi.Sentinel2Builder(s2_cloudless)
        .add_savi()
        .add_ndvi()
        .add_tasseled_cap()
        .build()
    )

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
    main()
