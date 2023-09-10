import ee


def ratio(num: str, dem: str, name: str = None) -> callable:
    name = f"{num}/{dem}" if name is None else name

    def calc(image: ee.Image):
        return image.addBands(image.select(num).divide(image.select(dem)).rename(name))

    return calc


def ndvi(nir: str, red: str, name: str = None):
    name = "NDVI" if name is None else name

    def calc(image: ee.Image) -> ee.Image:
        return image.addBands(image.normalizedDifference([nir, red]).rename(name))

    return calc


def savi(nir: str, red: str, L: float = 0.5, name: str = None):
    name = "SAVI" if name is None else name

    def calc(image: ee.Image) -> ee.Image:
        savi = image.expression(
            "(1 + L) * (NIR - RED) / (NIR + RED + L)",
            {
                "NIR": image.select(nir),
                "RED": image.select(red),
                "L": L,
            },
        ).rename(name)
        return image.addBands(savi)

    return calc


def tasseled_cap(blue: str, green: str, red, nir, swir1, swir2):
    def calc(image: ee.Image):
        input = image.select(blue, green, red, nir, swir1, swir2)
        co_array = [
            [0.3037, 0.2793, 0.4743, 0.5585, 0.5082, 0.1863],
            [-0.2848, -0.2435, -0.5436, 0.7243, 0.0840, -0.1800],
            [0.1509, 0.1973, 0.3279, 0.3406, -0.7112, -0.4572],
        ]

        co = ee.Array(co_array)

        arrayImage1D = input.toArray()
        arrayImage2D = arrayImage1D.toArray(1)

        components_image = (
            ee.Image(co)
            .matrixMultiply(arrayImage2D)
            .arrayProject([0])
            .arrayFlatten([["Brightness", "Greenness", "Wetness"]])
        )
        return image.addBands(components_image)

    return calc
