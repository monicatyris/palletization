from dataclasses import dataclass
from typing import Tuple

@dataclass
class Box:
    """Representa una caja con sus dimensiones y peso."""
    id: int
    width: float
    length: float
    height: float
    weight: float
    position: Tuple[float, float, float] = (0, 0, 0)  # (x, y, z)

    def volume(self) -> float:
        """Calcula el volumen de la caja."""
        return self.width * self.length * self.height 