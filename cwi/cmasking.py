import ee

from typing import Callable


def add_cloud_bands(cld_prb_thresh: int = 50) -> Callable:
    def _add_cloud_bands(img):
        #     # Get s2cloudless image, subset the probability band.
        cld_prb = ee.Image(img.get("s2cloudless")).select("probability")

        # Condition s2cloudless by the probability threshold value.
        is_cloud = cld_prb.gt(cld_prb_thresh).rename("clouds")

        # Add the cloud probability layer and cloud mask as image bands.
        return img.addBands(ee.Image([cld_prb, is_cloud]))

    return _add_cloud_bands


def add_shadow_bands(
    sr_band_scale: int = 1e4, nir_drk_thresh: float = 0.15, cld_prj_dist: int = 1
) -> Callable:
    def _add_shadow_bands(img: ee.Image):
        # Identify water pixels from the SCL band.
        not_water = img.select("SCL").neq(6)

        # Identify dark NIR pixels that are not water (potential cloud shadow pixels).

        dark_pixels = (
            img.select("B8")
            .lt(nir_drk_thresh * sr_band_scale)
            .multiply(not_water)
            .rename("dark_pixels")
        )

        # Determine the direction to project cloud shadow from clouds (assumes UTM projection).
        shadow_azimuth = ee.Number(90).subtract(
            ee.Number(img.get("MEAN_SOLAR_AZIMUTH_ANGLE"))
        )

        # Project shadows from clouds for the distance specified by the CLD_PRJ_DIST input.
        cld_proj = (
            img.select("clouds")
            .directionalDistanceTransform(shadow_azimuth, cld_prj_dist * 10)
            .reproject(**{"crs": img.select(0).projection(), "scale": 100})
            .select("distance")
            .mask()
            .rename("cloud_transform")
        )

        # Identify the intersection of dark pixels with cloud shadow projection.
        shadows = cld_proj.multiply(dark_pixels).rename("shadows")

        # Add dark pixels, cloud projection, and identified shadows as image bands.
        return img.addBands(ee.Image([dark_pixels, cld_proj, shadows]))

    return _add_shadow_bands


def add_cld_shdw_mask(buffer: int = 50) -> Callable:
    def _add_cld_shdw_mask(img):
        # Combine cloud and shadow mask, set cloud and shadow as value 1, else 0.
        is_cld_shdw = img.select("clouds").add(img.select("shadows")).gt(0)

        # Remove small cloud-shadow patches and dilate remaining pixels by BUFFER input.
        # 20 m scale is for speed, and assumes clouds don't require 10 m precision.
        is_cld_shdw = (
            is_cld_shdw.focalMin(2)
            .focalMax(buffer * 2 / 20)
            .reproject(**{"crs": img.select([0]).projection(), "scale": 20})
            .rename("cloudmask")
        )

        # Add the final cloud-shadow mask to the image.
        return img.addBands(is_cld_shdw)

    return _add_cld_shdw_mask


def apply_cld_shdw_mask(img):
    # Subset the cloudmask band and invert it so clouds/shadow are 0, else 1.
    not_cld_shdw = img.select("cloudmask").Not()

    # Subset reflectance bands and update their masks, return the result.
    return img.select("B.*").updateMask(not_cld_shdw)


class S2CloudlessBuilder:
    CLOUD_FILTER = 60
    CLD_PRB_THRESH = 40
    NIR_DRK_THRESH = 0.15
    CLD_PRJ_DIST = 2
    BUFFER = 100

    def __init__(self, collection: ee.ImageCollection):
        self.collection = collection

    def add_cloud_bands(self):
        self.collection = self.collection.map(add_cloud_bands(self.CLD_PRB_THRESH))
        return self

    def add_shadow_bands(self):
        self.collection = self.collection.map(
            add_shadow_bands(
                nir_drk_thresh=self.NIR_DRK_THRESH, cld_prj_dist=self.CLD_PRJ_DIST
            )
        )
        return self

    def add_cld_shdw_mask(self):
        self.collection = self.collection.map(add_cld_shdw_mask(self.BUFFER))
        return self

    def apply_cld_shdw_mask(self):
        self.collection = self.collection.map(apply_cld_shdw_mask)
        return self

    def build(self):
        return self
