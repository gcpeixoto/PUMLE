import numpy as np
from src.pumle.parameters import Parameters
from copy import deepcopy
import os
import json


class ParametersVariation:
    def __init__(
        self,
        base_parameters: dict,
        selected_parameters: list,
        variation_delta: float = 0.2,
        class_of_parameters: str = "Fluid",
        cache_file: str = None,
    ):
        self.base_parameters: dict = base_parameters
        self.selected_parameters: list = selected_parameters
        self.variation_delta: float = variation_delta
        self.points_in_each_parameter: int = int(1 / variation_delta)
        self.class_of_parameters: str = class_of_parameters
        self.cache_file = cache_file
        if self.cache_file:
            if not os.path.exists(self.cache_file):
                with open(self.cache_file, "w") as f:
                    json.dump([], f)
            self.cache = self.load_variations_from_cache()

        self.get_parameters_combinations()

    def get_parameters(self):
        parameters = []
        for parameter in self.selected_parameters:
            base_value = self.base_parameters[self.class_of_parameters][parameter]
            parameters.append(
                Parameters(
                    name=parameter,
                    base_value=base_value,
                    description=f"Variation of {parameter}",
                    variation_delta=self.variation_delta,
                )
            )
        return parameters

    def _format_combinations(self, combinations) -> list:
        return np.array(np.meshgrid(*combinations)).T.reshape(
            -1, len(self.selected_parameters)
        )

    def get_parameters_combinations(self):
        parameters = self.get_parameters()
        parameters_combinations = []
        for parameter in parameters:
            range_of_values = np.linspace(
                parameter.min_value, parameter.max_value, self.points_in_each_parameter
            )
            all_values = list(range_of_values)
            parameters_combinations.append(all_values)
        self.parameters_combinations = self._format_combinations(
            parameters_combinations
        )

    def generate_parameter_variations(self):
        variations = []
        for sim_id, combination in enumerate(self.parameters_combinations):
            variation = deepcopy(self.base_parameters)
            for i, parameter in enumerate(self.selected_parameters):
                variation[self.class_of_parameters][parameter] = combination[i]
                if self.cache_file:
                    if f"{parameter}_{combination[i]}" in self.cache:
                        continue
                    else:
                        self.cache.append(f"{parameter}_{combination[i]}\n")

            variation["SimNums"]["sim_id"] = sim_id + 1
            variations.append(variation)

        self.save_variations_to_cache()
        return variations

    def save_variations_to_cache(self):
        with open(self.cache_file, "w") as f:
            f.write(str(self.cache))

    def load_variations_from_cache(self):
        with open(self.cache_file, "r") as f:
            combos = f.readlines()
        return combos
