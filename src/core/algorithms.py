from typing import List, Tuple
from .box import Box
from .pallet import Pallet
import numpy as np

def first_fit_palletization(boxes: List[Box], 
                          max_width: float, 
                          max_length: float, 
                          max_height: float, 
                          max_weight: float) -> List[Pallet]:
    """Algoritmo First-Fit para palletización."""
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    pallets.append(current_pallet)
    
    for box in boxes:
        placed = False
        for pallet in pallets:
            if pallet.can_place_box(box):
                # Intentar colocar la caja en el pallet actual
                if pallet.place_box(box):
                    placed = True
                    break
        
        if not placed:
            # Si no se pudo colocar en ningún pallet existente, crear uno nuevo
            new_pallet = Pallet(max_width, max_length, max_height, max_weight)
            if new_pallet.place_box(box):
                pallets.append(new_pallet)
            else:
                print(f"Advertencia: La caja {box.id} no pudo ser colocada en ningún pallet")
    
    return pallets

def best_fit_decreasing_palletization(boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float) -> List[Pallet]:
    """Algoritmo Best-Fit Decreasing para palletización."""
    # Ordenar cajas por volumen de mayor a menor
    sorted_boxes = sorted(boxes, key=lambda x: x.volume(), reverse=True)
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    pallets.append(current_pallet)
    
    for box in sorted_boxes:
        best_pallet = None
        best_remaining_volume = float('inf')
        
        for pallet in pallets:
            if pallet.can_place_box(box):
                remaining_volume = pallet.remaining_volume()
                if remaining_volume < best_remaining_volume:
                    best_remaining_volume = remaining_volume
                    best_pallet = pallet
        
        if best_pallet:
            best_pallet.place_box(box)
        else:
            new_pallet = Pallet(max_width, max_length, max_height, max_weight)
            new_pallet.place_box(box)
            pallets.append(new_pallet)
    
    return pallets

def first_fit_decreasing_palletization(boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float) -> List[Pallet]:
    """Algoritmo First-Fit Decreasing para palletización."""
    # Ordenar cajas por volumen de mayor a menor
    sorted_boxes = sorted(boxes, key=lambda x: x.volume(), reverse=True)
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    pallets.append(current_pallet)
    
    for box in sorted_boxes:
        placed = False
        for pallet in pallets:
            if pallet.can_place_box(box):
                pallet.place_box(box)
                placed = True
                break
        
        if not placed:
            new_pallet = Pallet(max_width, max_length, max_height, max_weight)
            new_pallet.place_box(box)
            pallets.append(new_pallet)
    
    return pallets

def guillotine_palletization(boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float) -> List[Pallet]:
    """Algoritmo Guillotine para palletización."""
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    pallets.append(current_pallet)
    
    for box in boxes:
        placed = False
        for pallet in pallets:
            # Intentar colocar la caja en el pallet actual
            if pallet.can_place_box(box):
                # Encontrar el mejor lugar para colocar la caja
                best_position = None
                min_waste = float('inf')
                
                # Buscar en todas las posiciones posibles
                for x in range(0, int(pallet.max_width - box.width) + 1):
                    for y in range(0, int(pallet.max_length - box.length) + 1):
                        for z in range(0, int(pallet.max_height - box.height) + 1):
                            # Verificar si la posición es válida
                            if pallet.is_position_valid(box, (x, y, z)):
                                # Calcular el desperdicio de espacio
                                waste = pallet.calculate_waste(box, (x, y, z))
                                if waste < min_waste:
                                    min_waste = waste
                                    best_position = (x, y, z)
                
                if best_position:
                    box.position = best_position
                    pallet.place_box(box)
                    placed = True
                    break
        
        if not placed:
            new_pallet = Pallet(max_width, max_length, max_height, max_weight)
            new_pallet.place_box(box)
            pallets.append(new_pallet)
    
    return pallets

def calculate_pallet_quality(pallet: Pallet) -> Tuple[float, dict]:
    """
    Calcula una métrica de calidad para el pallet basada en varios factores:
    1. Utilización del volumen (0-1)
    2. Distribución del peso (0-1)
    3. Estabilidad de la carga (0-1)
    4. Altura utilizada (0-1)
    
    Returns:
        Tuple[float, dict]: 
            - Puntuación de calidad entre 0 y 1 (1 es mejor)
            - Diccionario con los componentes individuales y sus pesos
    """
    if not pallet.boxes:
        return 0.0, {
            'volume_utilization': 0.0,
            'weight_distribution': 0.0,
            'stability_score': 0.0,
            'height_utilization': 0.0,
            'weights': {
                'volume': 0.4,
                'weight': 0.3,
                'stability': 0.2,
                'height': 0.1
            }
        }
    
    # 1. Utilización del volumen
    total_volume = pallet.max_width * pallet.max_length * pallet.max_height
    used_volume = sum(box.volume() for box in pallet.boxes)
    volume_utilization = used_volume / total_volume
    
    # 2. Distribución del peso
    # Calcular el centro de masa
    total_weight = sum(box.weight for box in pallet.boxes)
    if total_weight == 0:
        weight_distribution = 0
    else:
        center_of_mass_x = sum(box.weight * (box.position[0] + box.width/2) for box in pallet.boxes) / total_weight
        center_of_mass_y = sum(box.weight * (box.position[1] + box.length/2) for box in pallet.boxes) / total_weight
        
        # La distribución ideal es en el centro del pallet
        ideal_center_x = pallet.max_width / 2
        ideal_center_y = pallet.max_length / 2
        
        # Calcular la desviación del centro ideal (normalizada)
        max_deviation = np.sqrt((pallet.max_width/2)**2 + (pallet.max_length/2)**2)
        actual_deviation = np.sqrt((center_of_mass_x - ideal_center_x)**2 + (center_of_mass_y - ideal_center_y)**2)
        weight_distribution = 1 - (actual_deviation / max_deviation)
    
    # 3. Estabilidad de la carga
    # Verificar si las cajas están bien apoyadas
    stability_score = 1.0
    for box in pallet.boxes:
        if box.position[2] > 0:  # Si no está en el suelo
            # Verificar si hay cajas debajo que la soporten
            supported = False
            for other_box in pallet.boxes:
                if other_box != box and other_box.position[2] < box.position[2]:
                    # Verificar si hay superposición en el plano XY
                    if (other_box.position[0] < box.position[0] + box.width and
                        other_box.position[0] + other_box.width > box.position[0] and
                        other_box.position[1] < box.position[1] + box.length and
                        other_box.position[1] + other_box.length > box.position[1]):
                        supported = True
                        break
            if not supported:
                stability_score *= 0.5  # Penalizar cajas no soportadas
    
    # 4. Altura utilizada
    max_height = max(box.position[2] + box.height for box in pallet.boxes)
    height_utilization = max_height / pallet.max_height
    
    # Ponderación de los factores
    weights = {
        'volume': 0.4,      # 40% importancia al volumen
        'weight': 0.3,      # 30% importancia a la distribución del peso
        'stability': 0.2,   # 20% importancia a la estabilidad
        'height': 0.1       # 10% importancia a la altura
    }
    
    # Calcular puntuación final
    quality_score = (
        weights['volume'] * volume_utilization +
        weights['weight'] * weight_distribution +
        weights['stability'] * stability_score +
        weights['height'] * height_utilization
    )
    
    # Devolver la puntuación y los componentes
    components = {
        'volume_utilization': volume_utilization,
        'weight_distribution': weight_distribution,
        'stability_score': stability_score,
        'height_utilization': height_utilization,
        'weights': weights
    }
    
    return quality_score, components 

def best_fit_lookahead_palletization(boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float, lookahead: int = 3) -> List[Pallet]:
    """
    Algoritmo Best-Fit Lookahead para palletización.
    Considera las próximas N cajas para tomar una mejor decisión sobre dónde colocar la caja actual.
    
    Args:
        boxes: Lista de cajas a paletizar
        max_width: Ancho máximo del pallet
        max_length: Largo máximo del pallet
        max_height: Alto máximo del pallet
        max_weight: Peso máximo del pallet
        lookahead: Número de cajas futuras a considerar (por defecto 3)
    
    Returns:
        Lista de pallets con las cajas asignadas
    """
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    pallets.append(current_pallet)
    
    # Convertir la lista de cajas en una cola para poder mirar adelante
    boxes_queue = boxes.copy()
    
    while boxes_queue:
        current_box = boxes_queue.pop(0)
        best_pallet = None
        best_score = float('-inf')
        
        # Obtener las próximas N cajas para el lookahead
        next_boxes = boxes_queue[:lookahead]
        
        for pallet in pallets:
            if pallet.can_place_box(current_box):
                # Calcular el score para este pallet considerando las cajas futuras
                score = calculate_pallet_score(pallet, current_box, next_boxes, max_width, max_length, max_height, max_weight)
                
                if score > best_score:
                    best_score = score
                    best_pallet = pallet
        
        if best_pallet:
            best_pallet.place_box(current_box)
        else:
            # Si no se encontró un pallet adecuado, crear uno nuevo
            new_pallet = Pallet(max_width, max_length, max_height, max_weight)
            if new_pallet.place_box(current_box):
                pallets.append(new_pallet)
            else:
                print(f"Advertencia: La caja {current_box.id} no pudo ser colocada en ningún pallet")
    
    return pallets

def calculate_pallet_score(pallet: Pallet, current_box: Box, next_boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float) -> float:
    """
    Calcula un score para un pallet considerando la caja actual y las próximas cajas.
    El score considera:
    1. Utilización del espacio después de colocar la caja actual
    2. Potencial para colocar las próximas cajas
    3. Estabilidad del pallet
    """
    # Crear una copia temporal del pallet para simular la colocación
    temp_pallet = Pallet(pallet.max_width, pallet.max_length, pallet.max_height, pallet.max_weight)
    for box in pallet.boxes:
        temp_pallet.place_box(box)
    
    # Intentar colocar la caja actual
    if not temp_pallet.place_box(current_box):
        return float('-inf')
    
    # 1. Calcular utilización del espacio
    space_utilization = 1 - (temp_pallet.remaining_volume() / temp_pallet.volume())
    
    # 2. Calcular potencial para las próximas cajas
    next_boxes_score = 0.0
    if next_boxes:
        # Intentar colocar las próximas cajas
        placed_count = 0
        for next_box in next_boxes:
            if temp_pallet.can_place_box(next_box):
                placed_count += 1
        next_boxes_score = placed_count / len(next_boxes)
    
    # 3. Calcular estabilidad
    stability_score = temp_pallet.get_stability_score()
    
    # 4. Calcular distribución del peso
    center_of_mass = temp_pallet.get_center_of_mass()
    ideal_center = (max_width/2, max_length/2, 0)
    weight_distribution = 1 - (
        abs(center_of_mass[0] - ideal_center[0]) / (max_width/2) +
        abs(center_of_mass[1] - ideal_center[1]) / (max_length/2)
    ) / 2
    
    # Combinar los scores con pesos
    final_score = (
        0.4 * space_utilization +      # 40% importancia al uso del espacio
        0.3 * next_boxes_score +       # 30% importancia al potencial futuro
        0.2 * stability_score +        # 20% importancia a la estabilidad
        0.1 * weight_distribution      # 10% importancia a la distribución del peso
    )
    
    return final_score 