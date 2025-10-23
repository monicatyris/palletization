from dataclasses import dataclass
from typing import Tuple, Union, List
from enum import Enum

class BoxOrientation(Enum):
    """Orientaciones posibles de una caja."""
    NORMAL = 0      # 0°/180° - (width, length, height)
    ROTATED_90 = 1  # 90°/270° - (length, width, height)

@dataclass
class Box:
    """Representa una caja con sus dimensiones y peso."""
    id: Union[int, str]
    width: float
    length: float
    height: float
    weight: float
    position: Tuple[float, float, float] = (0, 0, 0)  # (x, y, z)
    orientation: BoxOrientation = BoxOrientation.NORMAL  # Orientación actual

    def volume(self) -> float:
        """Calcula el volumen de la caja."""
        return self.width * self.length * self.height
    
    def get_dimensions(self) -> Tuple[float, float, float]:
        """Obtiene las dimensiones actuales según la orientación."""
        if self.orientation == BoxOrientation.NORMAL:
            return (self.width, self.length, self.height)
        else:  # ROTATED_90
            return (self.length, self.width, self.height)
    
    def get_effective_width(self) -> float:
        """Obtiene el ancho efectivo según la orientación."""
        return self.get_dimensions()[0]
    
    def get_effective_length(self) -> float:
        """Obtiene el largo efectivo según la orientación."""
        return self.get_dimensions()[1]
    
    def get_effective_height(self) -> float:
        """Obtiene el alto efectivo según la orientación."""
        return self.get_dimensions()[2]
    
    def rotate_90(self) -> 'Box':
        """Crea una nueva caja rotada 90 grados."""
        rotated_box = Box(
            id=self.id,
            width=self.width,
            length=self.length,
            height=self.height,
            weight=self.weight,
            position=self.position,
            orientation=BoxOrientation.ROTATED_90 if self.orientation == BoxOrientation.NORMAL else BoxOrientation.NORMAL
        )
        return rotated_box
    
    def get_all_orientations(self) -> List['Box']:
        """Obtiene todas las orientaciones posibles de la caja."""
        orientations = [self]
        rotated = self.rotate_90()
        orientations.append(rotated)
        return orientations 