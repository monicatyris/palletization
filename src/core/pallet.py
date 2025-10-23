import math
from typing import List, Tuple
from .box import Box
from .stacking_validator import StackingValidator, StackingConfig

class Pallet:
    """Representa un pallet con su capacidad y las cajas asignadas."""
    def __init__(self, max_width: float, max_length: float, max_height: float, max_weight: float, is_waste_pallet: bool = False):
        self.max_width = max_width
        self.max_length = max_length
        self.max_height = max_height
        self.max_weight = max_weight
        self.is_waste_pallet = is_waste_pallet
        self.boxes: List[Box] = []
        self.current_weight = 0.0
        self.occupied_space = []  # Lista de espacios ocupados (x, y, z, width, length, height)
        self.layers = []  # Lista para mantener registro de las capas
        
        # Inicializar validador de apilado
        self.stacking_config = StackingConfig()
        self.stacking_validator = StackingValidator(self.stacking_config)
        self.stacking_violations = []  # Lista de violaciones detectadas

    def volume(self) -> float:
        """Calcula el volumen total del pallet."""
        return self.max_width * self.max_length * self.max_height
    
    def remaining_volume(self) -> float:
        """Calcula el volumen restante en el pallet."""
        used_volume = sum(box.volume() for box in self.boxes)
        return self.volume() - used_volume
    
    def can_place_box(self, box: Box) -> bool:
        """Verifica si una caja puede ser colocada en el pallet."""
        # El pallet de desechos siempre puede recibir cajas
        if self.is_waste_pallet:
            return True
        
        # Verificar límites de peso
        if self.current_weight + box.weight > self.max_weight:
            return False
        
        # Usar dimensiones efectivas según la orientación
        effective_width = box.get_effective_width()
        effective_length = box.get_effective_length()
        effective_height = box.get_effective_height()
        
        # Verificar límites de dimensiones
        if (effective_width > self.max_width or 
            effective_length > self.max_length or 
            effective_height > self.max_height):
            return False
        
        # Verificar límites de altura
        if self.boxes:
            # Filtrar cajas con posición válida
            valid_boxes = [box for box in self.boxes 
                          if hasattr(box, 'position') and 
                          box.position is not None and 
                          len(box.position) >= 3 and 
                          isinstance(box.position[2], (int, float))]
            
            if valid_boxes:
                max_height = max((box.position[2] + box.get_effective_height() for box in valid_boxes), default=0)
                if max_height + effective_height > self.max_height:
                    return False
        
        return True
    
    def is_position_valid(self, box: Box, position: Tuple[float, float, float]) -> bool:
        """Verifica si una posición es válida para colocar una caja."""
        x, y, z = position
        
        # Usar dimensiones efectivas según la orientación
        effective_width = box.get_effective_width()
        effective_length = box.get_effective_length()
        effective_height = box.get_effective_height()
        
        # Verificar límites del pallet
        if (x + effective_width > self.max_width or
            y + effective_length > self.max_length or
            z + effective_height > self.max_height):
            return False
        
        # Verificar colisiones con otras cajas
        for other_box in self.boxes:
            # Verificar que la caja tiene posición válida
            if (not hasattr(other_box, 'position') or 
                not other_box.position or 
                len(other_box.position) < 3 or
                not all(isinstance(coord, (int, float)) for coord in other_box.position)):
                continue
                
            other_width = other_box.get_effective_width()
            other_length = other_box.get_effective_length()
            other_height = other_box.get_effective_height()
            
            if (x < other_box.position[0] + other_width and
                x + effective_width > other_box.position[0] and
                y < other_box.position[1] + other_length and
                y + effective_length > other_box.position[1] and
                z < other_box.position[2] + other_height and
                z + effective_height > other_box.position[2]):
                return False
        
        # Usar el validador de apilado para verificar condiciones de estabilidad
        can_place, violations = self.stacking_validator.validate_stacking(box, self, position)
        
        # Guardar violaciones para mostrar warnings
        if violations:
            self.stacking_violations.extend(violations)
            # Mostrar warnings si está configurado
            if self.stacking_config.show_warnings:
                self._show_stacking_warnings(violations)
        
        return can_place
    
    def _show_stacking_warnings(self, violations):
        """Muestra warnings sobre violaciones de condiciones de apilado."""
        for violation in violations:
            if violation.severity == "warning":
                print(f"⚠️ WARNING - Caja {violation.box_id}: {violation.message}")
                print(f"   💡 Recomendación: {violation.recommendation}")
            elif violation.severity == "error":
                print(f"❌ ERROR - Caja {violation.box_id}: {violation.message}")
                print(f"   💡 Recomendación: {violation.recommendation}")
            elif violation.severity == "critical":
                print(f"🚨 CRÍTICO - Caja {violation.box_id}: {violation.message}")
                print(f"   💡 Recomendación: {violation.recommendation}")
    
    def get_stacking_violations_summary(self):
        """Obtiene un resumen de las violaciones de apilado detectadas."""
        return self.stacking_validator.get_violation_summary()
    
    def configure_stacking_limits(self, 
                                 min_support_area_ratio: float = None,
                                 min_support_weight_ratio: float = None,
                                 max_height_multiplier: float = None,
                                 max_weight_multiplier: float = None,
                                 show_warnings: bool = None,
                                 allow_violations: bool = None):
        """Configura los límites de apilado."""
        if min_support_area_ratio is not None:
            self.stacking_config.min_support_area_ratio = min_support_area_ratio
        if min_support_weight_ratio is not None:
            self.stacking_config.min_support_weight_ratio = min_support_weight_ratio
        if max_height_multiplier is not None:
            self.stacking_config.max_height_multiplier = max_height_multiplier
        if max_weight_multiplier is not None:
            self.stacking_config.max_weight_multiplier = max_weight_multiplier
        if show_warnings is not None:
            self.stacking_config.show_warnings = show_warnings
        if allow_violations is not None:
            self.stacking_config.allow_violations = allow_violations
        
        # Recrear el validador con la nueva configuración
        self.stacking_validator = StackingValidator(self.stacking_config)
    
    def calculate_waste(self, box: Box, position: Tuple[float, float, float]) -> float:
        """Calcula el desperdicio de espacio al colocar una caja en una posición."""
        x, y, z = position
        
        # Calcular el espacio ocupado
        occupied_volume = sum(b.volume() for b in self.boxes) + box.volume()
        
        # Calcular el espacio total disponible
        total_volume = self.volume()
        
        # El desperdicio es la diferencia entre el espacio total y el ocupado
        return total_volume - occupied_volume
    
    def place_box(self, box: Box, step_x: int = 1, step_y: int = 1, step_z: int = 1) -> bool:
        """Coloca una caja en el pallet evaluando ambas orientaciones."""
        if self.can_place_box(box):
            # Para el pallet de desechos, simplemente agregar la caja sin posición específica
            if self.is_waste_pallet:
                box.position = (0, 0, 0)  # Posición dummy para el pallet de desechos
                self.boxes.append(box)
                self.current_weight += box.weight
                return True
            
            # Usar el nuevo método find_best_position que evalúa ambas orientaciones
            result = self.find_best_position(box, step_x, step_y, step_z)
            
            if result:
                oriented_box, position = result
                x, y, z = position
                oriented_box.position = (x, y, z)
                self.boxes.append(oriented_box)
                self.current_weight += oriented_box.weight
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
        """Verifica si la caja puede caber en el pallet en alguna orientación."""
        # Verificar que las dimensiones sean válidas (no infinitas ni NaN)
        if (not isinstance(box.width, (int, float)) or 
            not isinstance(box.length, (int, float)) or 
            not isinstance(box.height, (int, float)) or
            not isinstance(box.weight, (int, float)) or
            math.isnan(box.width) or math.isnan(box.length) or 
            math.isnan(box.height) or math.isnan(box.weight) or
            math.isinf(box.width) or math.isinf(box.length) or 
            math.isinf(box.height) or math.isinf(box.weight) or
            box.width <= 0 or box.length <= 0 or box.height <= 0 or box.weight <= 0):
            return False
            
        # Verificar límites de peso
        if self.current_weight + box.weight > self.max_weight:
            return False

        # Verificar si la caja puede caber en alguna orientación
        orientations = box.get_all_orientations()
        for oriented_box in orientations:
            effective_width = oriented_box.get_effective_width()
            effective_length = oriented_box.get_effective_length()
            effective_height = oriented_box.get_effective_height()
            
            if (effective_width <= self.max_width and 
                effective_length <= self.max_length and 
                effective_height <= self.max_height):
                return True

        return False

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

    def find_best_position(self, box: Box, step_x: float = 1.0, step_y: float = 1.0, step_z: float = 1.0):
        """
        Busca la mejor posición posible para colocar una caja en el pallet sin modificar el estado.
        Evalúa ambas orientaciones (0°/180° y 90°/270°) y devuelve la mejor opción.
        Devuelve una tupla (box_with_orientation, position) si encuentra una posición válida, o None si no hay espacio.
        """
        # Verificar que las dimensiones sean válidas (no infinitas ni NaN)
        if (not isinstance(box.width, (int, float)) or 
            not isinstance(box.length, (int, float)) or 
            not isinstance(box.height, (int, float)) or
            math.isnan(box.width) or math.isnan(box.length) or 
            math.isnan(box.height) or
            math.isinf(box.width) or math.isinf(box.length) or 
            math.isinf(box.height) or
            box.width <= 0 or box.length <= 0 or box.height <= 0):
            return None
        
        # Obtener ambas orientaciones de la caja
        orientations = box.get_all_orientations()
        best_result = None
        best_score = float('inf')
        
        for oriented_box in orientations:
            # Verificar que las dimensiones efectivas no excedan el pallet
            effective_width = oriented_box.get_effective_width()
            effective_length = oriented_box.get_effective_length()
            effective_height = oriented_box.get_effective_height()
            
            if (effective_width > self.max_width or 
                effective_length > self.max_length or 
                effective_height > self.max_height):
                continue
            
            # Convertir pasos float a enteros para range()
            step_x_int = max(1, int(step_x))
            step_y_int = max(1, int(step_y))
            step_z_int = max(1, int(step_z))
            
            best_position = None
            min_z = float('inf')
            
            try:
                for z in range(0, int(self.max_height - effective_height) + 1, step_z_int):
                    for y in range(0, int(self.max_length - effective_length) + 1, step_y_int):
                        for x in range(0, int(self.max_width - effective_width) + 1, step_x_int):
                            if self.is_position_valid(oriented_box, (x, y, z)):
                                # Verificar estabilidad
                                if z == 0:
                                    if z < min_z:
                                        min_z = z
                                        best_position = (x, y, z)
                                else:
                                    # Verificar soporte
                                    support_area = 0
                                    box_area = effective_width * effective_length
                                    total_support_weight = 0
                                    for other_box in self.boxes:
                                        other_width = other_box.get_effective_width()
                                        other_length = other_box.get_effective_length()
                                        other_height = other_box.get_effective_height()
                                        
                                        if (other_box.position[2] + other_height == z and
                                            other_box.position[0] <= x + effective_width and
                                            other_box.position[0] + other_width >= x and
                                            other_box.position[1] <= y + effective_length and
                                            other_box.position[1] + other_length >= y):
                                            overlap_x = min(x + effective_width, other_box.position[0] + other_width) - max(x, other_box.position[0])
                                            overlap_y = min(y + effective_length, other_box.position[1] + other_length) - max(y, other_box.position[1])
                                            support_area += overlap_x * overlap_y
                                            total_support_weight += other_box.weight
                                    # Criterios de estabilidad relajados (50% del área y 50% del peso)
                                    if support_area >= box_area * 0.5 and total_support_weight >= box.weight * 0.5:
                                        if z < min_z:
                                            min_z = z
                                            best_position = (x, y, z)
            except (ValueError, OverflowError):
                # Si hay algún error en los cálculos, continuar con la siguiente orientación
                continue
            
            # Si encontramos una posición válida, evaluar su calidad
            if best_position is not None:
                # Score basado en la altura (menor altura = mejor score)
                score = min_z
                if score < best_score:
                    best_score = score
                    best_result = (oriented_box, best_position)
        
        return best_result 