from typing import List, Tuple
from .box import Box

class Pallet:
    """Representa un pallet con su capacidad y las cajas asignadas."""
    def __init__(self, id: int, max_width: float, max_length: float, max_height: float, max_weight: float):
        self.id = id
        self.max_width = max_width
        self.max_length = max_length
        self.max_height = max_height
        self.max_weight = max_weight
        self.boxes: List[Box] = []
        self.current_weight = 0
        self.occupied_space = []  # Lista de espacios ocupados (x, y, z, width, length, height)
        self.layers = []  # Lista para mantener registro de las capas

    def can_fit(self, box: Box) -> bool:
        """Verifica si la caja puede caber en el pallet."""
        # Verificar límites de peso
        if self.current_weight + box.weight > self.max_weight:
            return False

        # Verificar límites de dimensiones
        if (box.width > self.max_width or 
            box.length > self.max_length or 
            box.height > self.max_height):
            return False

        return True

    def _is_position_available(self, x: float, y: float, z: float, box: Box) -> bool:
        """Verifica si una posición específica está disponible."""
        # Verificar límites del pallet
        if (x + box.width > self.max_width or 
            y + box.length > self.max_length or 
            z + box.height > self.max_height):
            return False

        # Verificar colisiones con otras cajas
        for occupied in self.occupied_space:
            ox, oy, oz, ow, ol, oh = occupied
            if not (x + box.width <= ox or ox + ow <= x or
                    y + box.length <= oy or oy + ol <= y or
                    z + box.height <= oz or oz + oh <= z):
                return False

        return True

    def _get_supported_area(self, z: float) -> List[Tuple[float, float, float, float]]:
        """Obtiene las áreas soportadas en una altura específica."""
        supported_areas = []
        current_z = z

        # Encontrar todas las cajas que soportan esta altura
        supporting_boxes = [box for box in self.boxes 
                          if box.position[2] + box.height == current_z]

        if not supporting_boxes:
            # Si no hay cajas soportando, el área soportada es el piso del pallet
            return [(0, 0, self.max_width, self.max_length)]

        # Calcular las áreas soportadas por las cajas
        for box in supporting_boxes:
            x, y, _ = box.position
            supported_area = (x, y, x + box.width, y + box.length)
            supported_areas.append(supported_area)

        return supported_areas

    def _is_position_supported(self, x: float, y: float, box: Box, z: float) -> bool:
        """Verifica si una posición está soportada por cajas debajo."""
        if z == 0:  # Si está en el piso, siempre está soportada
            return True

        supported_areas = self._get_supported_area(z)
        box_area = (x, y, x + box.width, y + box.length)

        # Verificar si el área de la caja está completamente soportada
        for area in supported_areas:
            ax1, ay1, ax2, ay2 = area
            bx1, by1, bx2, by2 = box_area

            # Verificar si hay superposición
            if not (bx2 <= ax1 or bx1 >= ax2 or by2 <= ay1 or by1 >= ay2):
                return True

        return False

    def add_box(self, box: Box) -> bool:
        """Intenta agregar una caja al pallet."""
        if not self.can_fit(box):
            return False

        # Buscar la mejor posición en todas las capas posibles
        best_position = None
        min_z = float('inf')

        # Probar diferentes alturas
        for z in range(0, int(self.max_height - box.height) + 1):
            # Probar diferentes posiciones en x e y
            for y in range(0, int(self.max_length - box.length) + 1):
                for x in range(0, int(self.max_width - box.width) + 1):
                    if (self._is_position_available(x, y, z, box) and 
                        self._is_position_supported(x, y, box, z)):
                        if z < min_z:
                            min_z = z
                            best_position = (x, y, z)

        if best_position is not None:
            x, y, z = best_position
            box.position = (x, y, z)
            self.boxes.append(box)
            self.occupied_space.append((x, y, z, box.width, box.length, box.height))
            self.current_weight += box.weight
            return True

        return False 