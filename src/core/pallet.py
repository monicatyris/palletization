from typing import List, Tuple
from .box import Box

class Pallet:
    """Representa un pallet con su capacidad y las cajas asignadas."""
    def __init__(self, max_width: float, max_length: float, max_height: float, max_weight: float):
        self.max_width = max_width
        self.max_length = max_length
        self.max_height = max_height
        self.max_weight = max_weight
        self.boxes: List[Box] = []
        self.current_weight = 0.0
        self.occupied_space = []  # Lista de espacios ocupados (x, y, z, width, length, height)
        self.layers = []  # Lista para mantener registro de las capas

    def volume(self) -> float:
        """Calcula el volumen total del pallet."""
        return self.max_width * self.max_length * self.max_height
    
    def remaining_volume(self) -> float:
        """Calcula el volumen restante en el pallet."""
        used_volume = sum(box.volume() for box in self.boxes)
        return self.volume() - used_volume
    
    def can_place_box(self, box: Box) -> bool:
        """Verifica si una caja puede ser colocada en el pallet."""
        # Verificar límites de peso
        if self.current_weight + box.weight > self.max_weight:
            return False
        
        # Verificar límites de altura
        max_height = max((box.position[2] + box.height for box in self.boxes), default=0)
        if max_height + box.height > self.max_height:
            return False
        
        return True
    
    def is_position_valid(self, box: Box, position: Tuple[float, float, float]) -> bool:
        """Verifica si una posición es válida para colocar una caja."""
        x, y, z = position
        
        # Verificar límites del pallet
        if (x + box.width > self.max_width or
            y + box.length > self.max_length or
            z + box.height > self.max_height):
            return False
        
        # Verificar colisiones con otras cajas
        for other_box in self.boxes:
            if (x < other_box.position[0] + other_box.width and
                x + box.width > other_box.position[0] and
                y < other_box.position[1] + other_box.length and
                y + box.length > other_box.position[1] and
                z < other_box.position[2] + other_box.height and
                z + box.height > other_box.position[2]):
                return False
        
        return True
    
    def calculate_waste(self, box: Box, position: Tuple[float, float, float]) -> float:
        """Calcula el desperdicio de espacio al colocar una caja en una posición."""
        x, y, z = position
        
        # Calcular el espacio ocupado
        occupied_volume = sum(b.volume() for b in self.boxes) + box.volume()
        
        # Calcular el espacio total disponible
        total_volume = self.volume()
        
        # El desperdicio es la diferencia entre el espacio total y el ocupado
        return total_volume - occupied_volume
    
    def place_box(self, box: Box) -> bool:
        """Coloca una caja en el pallet."""
        if self.can_place_box(box):
            # Encontrar la mejor posición para la caja
            best_position = None
            min_z = float('inf')
            
            # Buscar en todas las posiciones posibles
            for z in range(0, int(self.max_height - box.height) + 1):
                for y in range(0, int(self.max_length - box.length) + 1):
                    for x in range(0, int(self.max_width - box.width) + 1):
                        # Verificar si la posición es válida
                        if self.is_position_valid(box, (x, y, z)):
                            # Preferir posiciones más bajas
                            if z < min_z:
                                min_z = z
                                best_position = (x, y, z)
            
            if best_position:
                x, y, z = best_position
                box.position = (x, y, z)
                self.boxes.append(box)
                self.current_weight += box.weight
                return True
        return False
    
    def get_center_of_mass(self) -> Tuple[float, float, float]:
        """Calcula el centro de masa del pallet."""
        if not self.boxes:
            return (self.max_width/2, self.max_length/2, 0)
        
        total_weight = sum(box.weight for box in self.boxes)
        if total_weight == 0:
            return (self.max_width/2, self.max_length/2, 0)
        
        center_x = sum(box.weight * (box.position[0] + box.width/2) for box in self.boxes) / total_weight
        center_y = sum(box.weight * (box.position[1] + box.length/2) for box in self.boxes) / total_weight
        center_z = sum(box.weight * (box.position[2] + box.height/2) for box in self.boxes) / total_weight
        
        return (center_x, center_y, center_z)
    
    def get_stability_score(self) -> float:
        """Calcula un score de estabilidad para el pallet."""
        score = 1.0
        
        for box in self.boxes:
            # Verificar si la caja tiene soporte
            has_support = False
            if box.position[2] == 0:  # Si está en el suelo
                has_support = True
            else:
                for other_box in self.boxes:
                    if other_box != box:
                        # Verificar si hay soporte debajo
                        if (other_box.position[2] + other_box.height == box.position[2] and
                            other_box.position[0] <= box.position[0] + box.width and
                            other_box.position[0] + other_box.width >= box.position[0] and
                            other_box.position[1] <= box.position[1] + box.length and
                            other_box.position[1] + other_box.length >= box.position[1]):
                            has_support = True
                            break
            
            if not has_support:
                score -= 0.1  # Penalización por cada caja sin soporte
        
        return max(0, min(1, score))  # Asegurar que el score esté entre 0 y 1

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