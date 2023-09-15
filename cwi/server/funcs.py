import ee
import cwi


def stack(aoi):
    # build LandSat 8 SR inputs
    l8 = (
        cwi.LandSAT8Builder()
        .filter_by_geometry(aoi)
        .filter_by_date()
        .add_doy_filter()
        .add_cloud_mask()
        .select_spectral_bands()
        .add_ndvi()
        .add_savi()
        .add_tasseled_cap()
        .build()
    )

    s1 = (
        cwi.Sentinel1DVBuilder()
        .filter_by_geometry(aoi)
        .filter_date()
        .filter_by_doy()
        .denoise()
        .add_ratio()
        .select_bands()
        .build()
    )

    # Build ALOS Yearly Mosaic, target= 2019
    a2 = (
        cwi.ALOS2Builder()
        .filter_date("2019", "2020")
        .filter_by_geometry(aoi)
        .denoise()
        .add_ratio()
        .select_bands()
        .build()
    )

    # Build Elevation Inputs
    dem = cwi.NASADEMBuilder().select().add_slope().build()

    # Create the stack
    stack = ee.Image.cat(
        l8.collection.median(),
        s1.collection.median(),
        a2.collection.first(),
        dem.collection,
    )
    return stack


def classification(stack, asset_id, class_prop: str = None, predictors: list = None):
    class_prop = "value" if class_prop is None else class_prop
    predictors = stack.bandNames() if predictors is None else predictors

    samples = ee.FeatureCollection(asset_id)
    rf_model = cwi.RandomForestClassifier().train(samples, class_prop, predictors)
    classified = rf_model.classify(stack)
    return classified
