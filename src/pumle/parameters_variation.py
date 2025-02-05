import numpy as np
from src.pumle.parameters import Parameters
from copy import deepcopy


class ParametersVariation:
    def __init__(
        self,
        base_parameters: dict,
        selected_parameters: list,
        variation_delta: float = 0.2,
        class_of_parameters: str = "Fluid",
    ):
        self.base_parameters: dict = base_parameters
        self.selected_parameters: list = selected_parameters
        self.variation_delta: float = variation_delta
        self.points_in_each_parameter: int = int(1 / variation_delta)
        self.class_of_parameters: str = class_of_parameters
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
            all_values = []
            for value in range_of_values:
                all_values.append(value)
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
            variation["SimNums"]["sim_id"] = sim_id + 1

            variations.append(variation)
        return variations
