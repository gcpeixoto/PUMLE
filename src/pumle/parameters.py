from typing import Any


class Parameters:
    def __init__(
        self, name: str, base_value: Any, variation_delta: float, description: str = ""
    ):
        self.name = name
        self.base_value = base_value
        self.description = description
        self.min_value = self.base_value * (1 - variation_delta)
        self.max_value = self.base_value * (1 + variation_delta)

    def __str__(self):
        return f"{self.name}: {self.base_value} ({self.description})"
