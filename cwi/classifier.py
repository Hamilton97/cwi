import ee


class RandomForestClassifier:
    def __init__(
        self,
        n_trees: int = 1000,
        var_per_split: int = None,
        min_leaf_pop: int = 1,
        bag_frac: float = 0.5,
        max_nodes: int = None,
        seed: int = 0,
    ) -> None:
        self.numberOfTrees = n_trees
        self.variablesPerSplit = var_per_split
        self.minLeafPopulation = min_leaf_pop
        self.bagFraction = bag_frac
        self.maxNodes = max_nodes
        self.seed = seed
        self.output_mode = "CLASSIFICATION"
        self._classifier = None

    def train(self, features, class_property, predictors):
        self._classifier = (
            ee.Classifier.smileRandomForest(
                self.numberOfTrees,
                self.variablesPerSplit,
                self.minLeafPopulation,
                self.bagFraction,
                self.maxNodes,
                self.seed,
            )
            .setOutputMode(self.output_mode)
            .train(features, class_property, predictors)
        )
        return self

    def classify(self, eeobj: ee.Image | ee.FeatureCollection):
        if self._classifier is None:
            raise ValueError("Classifier must be trained before you classify")
        return eeobj.classify(self._classifier)
