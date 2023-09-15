import ee

from typing import Callable


def mask_l8_sr(image: ee.Image) -> ee.Image:
    qaMask = image.select('QA_PIXEL').bitwiseAnd(int('11111', 2)).eq(0);
    saturationMask = image.select('QA_RADSAT').eq(0);

    # Apply the scaling factors to the appropriate bands.
    opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2);
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0);

    
    return (image.addBands(opticalBands, None, True) 
            .addBands(thermalBands, None, True)
            .updateMask(qaMask)
            .updateMask(saturationMask)
        )
