import random
import math
from typing import List, Tuple, Optional, Dict, Any
from .pallet import Pallet
from .box import Box
import numpy as np
from .mqtt_publisher import MQTTPublisher
from .mqtt_messages import send_start_pallet_message, send_place_package_message, send_complete_pallet_message
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

def first_fit_palletization(boxes: List[Box], 
                          max_width: float, 
                          max_length: float, 
                          max_height: float, 
                          max_weight: float,
                          mqtt_publisher: Optional[MQTTPublisher] = None,
                          pallet_index: int = 0) -> List[Pallet]:
    """Algoritmo First-Fit para palletización."""
    print(f"first_fit_palletization: Iniciando con {len(boxes)} cajas")
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    current_pallet.algorithm = "first_fit"  # Identificador del algoritmo
    pallets.append(current_pallet)
    
    # Enviar mensaje MQTT de inicio de pallet
    send_start_pallet_message(current_pallet, pallet_index)
    
    # Crear pallet de desechos infinito
    waste_pallet = Pallet(float('inf'), float('inf'), float('inf'), float('inf'), is_waste_pallet=True)
    waste_pallet.algorithm = "waste_pallet"
    pallets.append(waste_pallet)
    
    # Ajustar el paso de búsqueda basado en el tamaño del pallet
    step_x = max(5, int(max_width / 20))  # Paso de 5 unidades o 1/20 del ancho
    step_y = max(5, int(max_length / 20))  # Paso de 5 unidades o 1/20 del largo
    step_z = max(5, int(max_height / 20))
    
    for i, box in enumerate(boxes):
        print(f"Procesando caja {i+1}/{len(boxes)}: {box.id if box else 'None'}")
        if box is None:
            print(f"Advertencia: Caja {i+1} es None, saltando...")
            continue
            
        placed = False
        for pallet in pallets:
            if pallet.can_place_box(box):
                # Intentar colocar la caja en el pallet actual con pasos optimizados
                result = pallet.find_best_position(box, step_x, step_y, step_z)
                if result:
                    # El resultado ahora es (oriented_box, position)
                    oriented_box, position = result
                    x, y, z = position
                    oriented_box.position = (x, y, z)
                    pallet.boxes.append(oriented_box)
                    pallet.current_weight += oriented_box.weight
                    placed = True
                    
                    # Enviar mensaje MQTT de colocación de caja
                    quality_score = 0.5  # Puntuación por defecto, se puede mejorar
                    send_place_package_message(oriented_box, pallet, pallet_index, "First-Fit", quality_score)
                    
                    print(f"Caja {oriented_box.id} colocada en pallet existente (orientación: {oriented_box.orientation.name})")
                    break
        
        if not placed:
            print(f"Caja {box.id} no pudo ser colocada en pallets regulares, enviando al pallet de desechos")
            # Colocar la caja en el pallet de desechos
            waste_pallet.place_box(box)
            print(f"Caja {box.id} enviada al pallet de desechos")
    
    print(f"first_fit_palletization: Completado. {len(pallets)} pallets creados")
    
    # Enviar mensaje MQTT de completado de pallet
    if current_pallet.boxes:
        used_volume = sum(box.volume() for box in current_pallet.boxes) / current_pallet.volume()
        send_complete_pallet_message(current_pallet, pallet_index, 0.5, used_volume)
    
    return pallets

def best_fit_decreasing_palletization(boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float) -> List[Pallet]:
    """Algoritmo Best-Fit Decreasing para palletización."""
    # Ordenar cajas por volumen de mayor a menor
    sorted_boxes = sorted(boxes, key=lambda x: x.volume(), reverse=True)
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    pallets.append(current_pallet)
    
    # Ajustar el paso de búsqueda basado en el tamaño del pallet
    step_x = max(5, int(max_width / 20))
    step_y = max(5, int(max_length / 20))
    step_z = max(5, int(max_height / 20))
    
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
            best_pallet.place_box(box, step_x, step_y, step_z)
        else:
            new_pallet = Pallet(max_width, max_length, max_height, max_weight)
            new_pallet.place_box(box, step_x, step_y, step_z)
            pallets.append(new_pallet)
    
    return pallets

def first_fit_decreasing_palletization(boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float) -> List[Pallet]:
    """Algoritmo First-Fit Decreasing para palletización."""
    # Ordenar cajas por volumen de mayor a menor
    sorted_boxes = sorted(boxes, key=lambda x: x.volume(), reverse=True)
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    pallets.append(current_pallet)
    
    # Crear pallet de desechos infinito
    waste_pallet = Pallet(float('inf'), float('inf'), float('inf'), float('inf'), is_waste_pallet=True)
    waste_pallet.algorithm = "waste_pallet"
    pallets.append(waste_pallet)
    
    # Ajustar el paso de búsqueda basado en el tamaño del pallet
    step_x = max(5, int(max_width / 20))
    step_y = max(5, int(max_length / 20))
    step_z = max(5, int(max_height / 20))
    
    for box in sorted_boxes:
        placed = False
        for pallet in pallets:
            if not pallet.is_waste_pallet and pallet.can_place_box(box):
                if pallet.place_box(box, step_x, step_y, step_z):
                    placed = True
                    break
        
        if not placed:
            print(f"Caja {box.id} no pudo ser colocada en pallets regulares, enviando al pallet de desechos")
            waste_pallet.place_box(box)
            print(f"Caja {box.id} enviada al pallet de desechos")
    
    return pallets

def guillotine_palletization(boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float) -> List[Pallet]:
    """Algoritmo Guillotine para palletización."""
    pallets = []
    current_pallet = Pallet(max_width, max_length, max_height, max_weight)
    pallets.append(current_pallet)
    
    # Crear pallet de desechos infinito
    waste_pallet = Pallet(float('inf'), float('inf'), float('inf'), float('inf'), is_waste_pallet=True)
    waste_pallet.algorithm = "waste_pallet"
    pallets.append(waste_pallet)
    
    # Ajustar el paso de búsqueda basado en el tamaño del pallet
    step_x = max(5, int(max_width / 20))
    step_y = max(5, int(max_length / 20))
    step_z = max(5, int(max_height / 20))
    
    for box in boxes:
        placed = False
        for pallet in pallets:
            if not pallet.is_waste_pallet and pallet.can_place_box(box):
                # Encontrar el mejor lugar para colocar la caja
                best_position = None
                min_waste = float('inf')
                
                # Buscar en todas las posiciones posibles con pasos optimizados
                for z in range(0, int(pallet.max_height - box.height) + 1, step_z):
                    for y in range(0, int(pallet.max_length - box.length) + 1, step_y):
                        for x in range(0, int(pallet.max_width - box.width) + 1, step_x):
                            if pallet.is_position_valid(box, (x, y, z)):
                                waste = pallet.calculate_waste(box, (x, y, z))
                                if waste < min_waste:
                                    min_waste = waste
                                    best_position = (x, y, z)
                
                if best_position:
                    box.position = best_position
                    pallet.place_box(box, step_x, step_y, step_z)
                    placed = True
                    break
        
        if not placed:
            print(f"Caja {box.id} no pudo ser colocada en pallets regulares, enviando al pallet de desechos")
            waste_pallet.place_box(box)
            print(f"Caja {box.id} enviada al pallet de desechos")
    
    return pallets

def calculate_pallet_quality(pallet: Pallet, 
                           volume_weight: float = 0.34,
                           weight_distribution_weight: float = 0.33,
                           stability_weight: float = 0.33) -> Tuple[float, dict]:
    """
    Calcula la calidad de un pallet basada en varios factores.
    Retorna una puntuación entre 0 y 1, donde 1 es la mejor calidad.
    
    Args:
        pallet: El pallet a evaluar
        volume_weight: Peso para la utilización del volumen (por defecto 0.34)
        weight_distribution_weight: Peso para la distribución del peso (por defecto 0.33)
        stability_weight: Peso para la estabilidad (por defecto 0.33)
    """
    # No calcular calidad para el pallet de desechos
    if pallet.is_waste_pallet:
        return 0.0, {
            'volume_utilization': 0.0,
            'weight_distribution': 0.0,
            'stability_score': 0.0,
            'weights': {
                'volume': volume_weight,
                'weight': weight_distribution_weight,
                'stability': stability_weight
            }
        }
    
    if not pallet.boxes:
        return 0.0, {
            'volume_utilization': 0.0,
            'weight_distribution': 0.0,
            'stability_score': 0.0,
            'weights': {
                'volume': volume_weight,
                'weight': weight_distribution_weight,
                'stability': stability_weight
            }
        }

    # 1. Utilización del volumen (33% del score)
    total_volume = pallet.max_width * pallet.max_length * pallet.max_height
    used_volume = sum(box.volume() for box in pallet.boxes)
    volume_utilization = used_volume / total_volume

    # 2. Distribución del peso (33% del score)
    total_weight = sum(box.weight for box in pallet.boxes)
    if total_weight == 0:
        weight_distribution = 0.0
    else:
        # Calcula el centro de masa
        center_of_mass_x = sum(box.weight * (box.position[0] + box.width/2) for box in pallet.boxes) / total_weight
        center_of_mass_y = sum(box.weight * (box.position[1] + box.length/2) for box in pallet.boxes) / total_weight
        
        # Centro ideal del pallet
        ideal_center_x = pallet.max_width / 2
        ideal_center_y = pallet.max_length / 2
        
        # Calcula la desviación normalizada usando distancia euclidiana
        max_deviation = ((pallet.max_width/2)**2 + (pallet.max_length/2)**2)**0.5
        actual_deviation = ((center_of_mass_x - ideal_center_x)**2 + 
                          (center_of_mass_y - ideal_center_y)**2)**0.5
        
        # Penalización cuadrática
        weight_distribution = 1 - (actual_deviation / max_deviation)**2

    # 3. Estabilidad de la carga (33% del score)
    stability_scores = []
    for current_box in pallet.boxes:
        if current_box.position[2] == 0:  # Si está en el suelo
            stability_scores.append(1.0)
            continue
            
        # Calcula el área de soporte
        support_area = 0
        box_area = current_box.width * current_box.length
        box_bottom = current_box.position[2]
        
        # Encuentra todas las cajas que podrían estar soportando
        supporting_boxes = [b for b in pallet.boxes 
                          if b != current_box and 
                          b.position[2] + b.height == box_bottom]
        
        # Calcula el área de soporte para cada caja de soporte
        for support_box in supporting_boxes:
            # Calcula la intersección en el plano XY
            overlap_x = min(current_box.position[0] + current_box.width, 
                          support_box.position[0] + support_box.width) - \
                       max(current_box.position[0], support_box.position[0])
            overlap_y = min(current_box.position[1] + current_box.length, 
                          support_box.position[1] + support_box.length) - \
                       max(current_box.position[1], support_box.position[1])
            
            if overlap_x > 0 and overlap_y > 0:
                support_area += overlap_x * overlap_y
        
        # Calcula el score de estabilidad para esta caja
        support_ratio = support_area / box_area
        if support_ratio >= 0.75:  # Soporte completo
            stability_scores.append(1.0)
        elif support_ratio >= 0.5:  # Soporte parcial
            stability_scores.append(0.7)
        elif support_ratio >= 0.25:  # Soporte mínimo
            stability_scores.append(0.3)
        else:  # Soporte insuficiente
            stability_scores.append(0.0)
    
    # Promedio ponderado de estabilidad
    stability_score = sum(stability_scores) / len(stability_scores)

    # Cálculo del score final (ponderación equitativa)
    quality_score = (
        volume_weight * volume_utilization +           # Peso personalizable para volumen
        weight_distribution_weight * weight_distribution +  # Peso personalizable para distribución del peso
        stability_weight * stability_score             # Peso personalizable para estabilidad
    )

    return quality_score, {
        'volume_utilization': volume_utilization,
        'weight_distribution': weight_distribution,
        'stability_score': stability_score,
        'weights': {
            'volume': volume_weight,
            'weight': weight_distribution_weight,
            'stability': stability_weight
        }
    }

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
    
    # Crear pallet de desechos infinito
    waste_pallet = Pallet(float('inf'), float('inf'), float('inf'), float('inf'), is_waste_pallet=True)
    waste_pallet.algorithm = "waste_pallet"
    pallets.append(waste_pallet)
    
    # Convertir la lista de cajas en una cola para poder mirar adelante
    boxes_queue = boxes.copy()
    
    # Ajustar el paso de búsqueda basado en el tamaño del pallet
    step_x = max(5, int(max_width / 20))
    step_y = max(5, int(max_length / 20))
    step_z = max(5, int(max_height / 20))
    
    while boxes_queue:
        current_box = boxes_queue.pop(0)
        best_pallet = None
        best_score = float('-inf')
        
        # Obtener las próximas N cajas para el lookahead
        next_boxes = boxes_queue[:lookahead]
        
        for pallet in pallets:
            if not pallet.is_waste_pallet and pallet.can_place_box(current_box):
                # Calcular el score para este pallet considerando las cajas futuras
                score = calculate_pallet_score(pallet, current_box, next_boxes, max_width, max_length, max_height, max_weight)
                
                if score > best_score:
                    best_score = score
                    best_pallet = pallet
        
        if best_pallet:
            if not best_pallet.place_box(current_box, step_x, step_y, step_z):
                print(f"Caja {current_box.id} no pudo ser colocada en pallets regulares, enviando al pallet de desechos")
                waste_pallet.place_box(current_box)
                print(f"Caja {current_box.id} enviada al pallet de desechos")
        else:
            print(f"Caja {current_box.id} no pudo ser colocada en pallets regulares, enviando al pallet de desechos")
            waste_pallet.place_box(current_box)
            print(f"Caja {current_box.id} enviada al pallet de desechos")
    
    return pallets

def calculate_pallet_score(pallet: Pallet, current_box: Box, next_boxes: List[Box], max_width: float, max_length: float, max_height: float, max_weight: float) -> float:
    """
    Calcula un score para un pallet considerando la caja actual y las próximas cajas.
    Versión optimizada que reduce cálculos innecesarios.
    """
    # Verificar rápidamente si la caja actual puede ser colocada
    if not pallet.can_place_box(current_box):
        return float('-inf')
    
    # Crear una copia temporal del pallet solo si es necesario
    temp_pallet = None
    if next_boxes:
        temp_pallet = Pallet(pallet.max_width, pallet.max_length, pallet.max_height, pallet.max_weight)
        # Copiar las cajas existentes de forma segura
        for existing_box in pallet.boxes:
            if existing_box is not None:
                try:
                    temp_pallet.place_box(existing_box)
                except Exception as e:
                    print(f"Error al copiar caja {existing_box.id if existing_box else 'None'} al pallet temporal: {e}")
                    continue
    
    # 1. Calcular utilización del espacio (simplificado)
    try:
        space_utilization = 1 - (pallet.remaining_volume() / pallet.volume())
    except ZeroDivisionError:
        space_utilization = 0.0
    
    # 2. Calcular potencial para las próximas cajas (simplificado)
    next_boxes_score = 0.0
    if next_boxes and temp_pallet:
        # Solo verificar si las cajas caben, sin intentar colocarlas
        try:
            placed_count = sum(1 for next_box in next_boxes if next_box is not None and temp_pallet.can_fit(next_box))
            next_boxes_score = placed_count / len(next_boxes) if next_boxes else 0.0
        except Exception as e:
            print(f"Error al calcular next_boxes_score: {e}")
            next_boxes_score = 0.0
    
    # 3. Calcular estabilidad (simplificado)
    try:
        stability_score = pallet.get_stability_score()
    except Exception as e:
        print(f"Error al calcular stability_score: {e}")
        stability_score = 0.0
    
    # 4. Calcular distribución del peso (simplificado)
    try:
        center_of_mass = pallet.get_center_of_mass()
        ideal_center = (max_width/2, max_length/2, 0)
        weight_distribution = 1 - (
            abs(center_of_mass[0] - ideal_center[0]) / (max_width/2) +
            abs(center_of_mass[1] - ideal_center[1]) / (max_length/2)
        ) / 2
    except Exception as e:
        print(f"Error al calcular weight_distribution: {e}")
        weight_distribution = 0.0
    
    # Combinar los scores con pesos
    final_score = (
        0.4 * space_utilization +      # 40% importancia al uso del espacio
        0.3 * next_boxes_score +       # 30% importancia al potencial futuro
        0.2 * stability_score +        # 20% importancia a la estabilidad
        0.1 * weight_distribution      # 10% importancia a la distribución del peso
    )
    
    return final_score 

def weight_based_palletization(boxes: List[Box], 
                              pallet1_config: dict, 
                              pallet2_config: dict,
                              weight_threshold: float = 5.0) -> List[Pallet]:
    """
    Algoritmo de paletización basado en peso que clasifica las cajas en 2 pallets específicos.
    
    Args:
        boxes: Lista de cajas a paletizar
        pallet1_config: Configuración del pallet 1 (para cajas < threshold)
        pallet2_config: Configuración del pallet 2 (para cajas >= threshold)
        weight_threshold: Umbral de peso para clasificar las cajas (por defecto 5.0 kg)
    
    Returns:
        Lista con exactamente 2 pallets (puede estar vacía si no se pudo colocar)
    """
    # Crear los dos pallets con sus configuraciones específicas
    pallet1 = Pallet(
        max_width=pallet1_config.max_width,
        max_length=pallet1_config.max_length,
        max_height=pallet1_config.max_height,
        max_weight=pallet1_config.max_weight
    )
    pallet1.algorithm = "weight_based"
    
    # Enviar mensaje MQTT de inicio de pallet 1
    send_start_pallet_message(pallet1, 0)
    
    pallet2 = Pallet(
        max_width=pallet2_config.max_width,
        max_length=pallet2_config.max_length,
        max_height=pallet2_config.max_height,
        max_weight=pallet2_config.max_weight
    )
    pallet2.algorithm = "weight_based"
    
    # Enviar mensaje MQTT de inicio de pallet 2
    send_start_pallet_message(pallet2, 1)
    
    # Crear pallet de desechos infinito
    waste_pallet = Pallet(float('inf'), float('inf'), float('inf'), float('inf'), is_waste_pallet=True)
    waste_pallet.algorithm = "waste_pallet"
    
    pallets = [pallet1, pallet2, waste_pallet]
    
    # Ajustar el paso de búsqueda basado en el tamaño del pallet
    step_x1 = max(5, int(pallet1.max_width / 20))
    step_y1 = max(5, int(pallet1.max_length / 20))
    step_z1 = max(5, int(pallet1.max_height / 20))
    
    step_x2 = max(5, int(pallet2.max_width / 20))
    step_y2 = max(5, int(pallet2.max_length / 20))
    step_z2 = max(5, int(pallet2.max_height / 20))
    
    for i, box in enumerate(boxes):
        print(f"Procesando caja {i+1}/{len(boxes)}: {box.id} - Peso: {box.weight} kg")
        
        if box is None:
            print(f"Advertencia: Caja {i+1} es None, saltando...")
            continue
        
        # Determinar en qué pallet debe ir según el peso
        if box.weight < weight_threshold:
            target_pallet = pallet1
            target_pallet_name = "Pallet 1 (cajas ligeras)"
            step_x, step_y, step_z = step_x1, step_y1, step_z1
        else:
            target_pallet = pallet2
            target_pallet_name = "Pallet 2 (cajas pesadas)"
            step_x, step_y, step_z = step_x2, step_y2, step_z2
        
        print(f"Caja {box.id} ({box.weight} kg) asignada a {target_pallet_name}")
        
        # Verificar si la caja puede ser colocada en el pallet asignado
        if target_pallet.can_place_box(box):
            # Intentar colocar la caja en el pallet asignado
            result = target_pallet.find_best_position(box, step_x, step_y, step_z)
            if result:
                # El resultado ahora es (oriented_box, position)
                oriented_box, position = result
                x, y, z = position
                oriented_box.position = (x, y, z)
                target_pallet.boxes.append(oriented_box)
                target_pallet.current_weight += oriented_box.weight
                
                # Enviar mensaje MQTT de colocación de caja
                pallet_index = 0 if target_pallet == pallet1 else 1
                quality_score = 0.5  # Puntuación por defecto, se puede mejorar
                send_place_package_message(oriented_box, target_pallet, pallet_index, "Weight-Based", quality_score)
                
                print(f"✅ Caja {oriented_box.id} colocada exitosamente en {target_pallet_name} (orientación: {oriented_box.orientation.name})")
            else:
                # No se pudo encontrar una posición válida, enviar al pallet de desechos
                print(f"⚠️ Caja {box.id} no pudo ser colocada en {target_pallet_name} - Enviando al pallet de desechos")
                waste_pallet.place_box(box)
                print(f"✅ Caja {box.id} enviada al pallet de desechos")
        else:
            # La caja no puede ser colocada (restricciones de peso o dimensiones), enviar al pallet de desechos
            print(f"⚠️ Caja {box.id} no puede ser colocada en {target_pallet_name} - Restricciones violadas, enviando al pallet de desechos")
            waste_pallet.place_box(box)
            print(f"✅ Caja {box.id} enviada al pallet de desechos")
    
    print(f"weight_based_palletization: Completado. {len(pallets)} pallets creados")
    
    # Enviar mensajes MQTT de completado para cada pallet
    if pallet1.boxes:
        used_volume = sum(box.volume() for box in pallet1.boxes) / pallet1.volume()
        quality_score = 0.5  # Puntuación por defecto, se puede mejorar
        send_complete_pallet_message(pallet1, 0, quality_score, used_volume)
    
    if pallet2.boxes:
        used_volume = sum(box.volume() for box in pallet2.boxes) / pallet2.volume()
        quality_score = 0.5  # Puntuación por defecto, se puede mejorar
        send_complete_pallet_message(pallet2, 1, quality_score, used_volume)
    
    # Enviar mensaje MQTT de completado para el pallet de desechos si tiene cajas
    if waste_pallet.boxes:
        used_volume = sum(box.volume() for box in waste_pallet.boxes) / waste_pallet.volume()
        send_complete_pallet_message(waste_pallet, 2, 0.0, used_volume)
    
    return pallets

def multi_pallet_palletization(boxes: List[Box], pallet_configs: List[dict], algorithm: str = "First-Fit") -> List[Pallet]:
    """
    Algoritmo para palletización en múltiples pallets con diferentes configuraciones.
    
    Args:
        boxes: Lista de cajas a paletizar
        pallet_configs: Lista de configuraciones de pallets (cada una con max_width, max_length, max_height, max_weight)
        algorithm: Algoritmo a usar para cada pallet ("First-Fit", "Best-Fit Decreasing", etc.)
    
    Returns:
        Lista de pallets con las cajas asignadas
    """
    all_pallets = []
    remaining_boxes = boxes.copy()
    
    for i, config in enumerate(pallet_configs):
        if not remaining_boxes:
            break
            
        print(f"Procesando Pallet {i+1} con configuración: {config}")
        
        # Crear pallet con la configuración específica
        current_pallet = Pallet(
            max_width=config.max_width,
            max_length=config.max_length,
            max_height=config.max_height,
            max_weight=config.max_weight
        )
        
        # Enviar mensaje MQTT de inicio de pallet
        send_start_pallet_message(current_pallet, i)
        
        # Aplicar el algoritmo seleccionado al pallet actual
        if algorithm == "First-Fit":
            pallets_for_current = first_fit_palletization(
                remaining_boxes,
                max_width=config.max_width,
                max_length=config.max_length,
                max_height=config.max_height,
                max_weight=config.max_weight,
                pallet_index=i
            )
        elif algorithm == "Best-Fit Decreasing":
            pallets_for_current = best_fit_decreasing_palletization(
                remaining_boxes,
                max_width=config.max_width,
                max_length=config.max_length,
                max_height=config.max_height,
                max_weight=config.max_weight
            )
        elif algorithm == "First-Fit Decreasing":
            pallets_for_current = first_fit_decreasing_palletization(
                remaining_boxes,
                max_width=config.max_width,
                max_length=config.max_length,
                max_height=config.max_height,
                max_weight=config.max_weight
            )
        elif algorithm == "Guillotine":
            pallets_for_current = guillotine_palletization(
                remaining_boxes,
                max_width=config.max_width,
                max_length=config.max_length,
                max_height=config.max_height,
                max_weight=config.max_weight
            )
        elif algorithm == "Best-Fit Lookahead":
            pallets_for_current = best_fit_lookahead_palletization(
                remaining_boxes,
                max_width=config.max_width,
                max_length=config.max_length,
                max_height=config.max_height,
                max_weight=config.max_weight,
                lookahead=3
            )
        elif algorithm == "Weight-Based":
            pallets_for_current = weight_based_palletization(
                remaining_boxes,
                pallet1_config=config,
                pallet2_config=pallet_configs[i+1] if i+1 < len(pallet_configs) else config, # Assuming next config is pallet2
                weight_threshold=3.0 # Default threshold
            )
        else:
            # Default to First-Fit
            pallets_for_current = first_fit_palletization(
                remaining_boxes,
                max_width=config.max_width,
                max_length=config.max_length,
                max_height=config.max_height,
                max_weight=config.max_weight
            )
        
        # Agregar los pallets creados para esta configuración
        all_pallets.extend(pallets_for_current)
        
        # Enviar mensajes MQTT de completado para cada pallet
        for j, pallet in enumerate(pallets_for_current):
            if pallet.boxes and not pallet.is_waste_pallet:
                used_volume = sum(box.volume() for box in pallet.boxes) / pallet.volume()
                quality_score = 0.5  # Puntuación por defecto, se puede mejorar
                send_complete_pallet_message(pallet, i + j, quality_score, used_volume)
        
        # Actualizar las cajas restantes (las que no se pudieron colocar)
        placed_boxes = []
        for pallet in pallets_for_current:
            placed_boxes.extend(pallet.boxes)
        
        # Filtrar las cajas que ya fueron colocadas
        remaining_boxes = [box for box in remaining_boxes if box not in placed_boxes]
        
        print(f"Pallet {i+1} completado. Cajas colocadas: {len(placed_boxes)}, Cajas restantes: {len(remaining_boxes)}")
    
    # Crear pallet de desechos para las cajas restantes
    if remaining_boxes:
        waste_pallet = Pallet(float('inf'), float('inf'), float('inf'), float('inf'), is_waste_pallet=True)
        waste_pallet.algorithm = "waste_pallet"
        for box in remaining_boxes:
            waste_pallet.place_box(box)
        all_pallets.append(waste_pallet)
        
        # Enviar mensaje MQTT de completado para el pallet de desechos
        if waste_pallet.boxes:
            used_volume = sum(box.volume() for box in waste_pallet.boxes) / waste_pallet.volume()
            send_complete_pallet_message(waste_pallet, len(all_pallets), 0.0, used_volume)
    
    return all_pallets 

def normalize_box_features(boxes: List[Box], pallet_configs: List) -> np.ndarray:
    """
    Normaliza las características de las cajas para clustering.
    
    Características:
    1. Peso normalizado (0-1)
    2. Ancho normalizado (0-1) 
    3. Largo normalizado (0-1)
    4. Alto normalizado (0-1)
    5. Densidad (peso/volumen)
    6. Proporción ancho/largo
    7. Proporción alto/ancho
    """
    if not boxes:
        return np.array([])
    
    # Obtener dimensiones máximas de los pallets para normalización
    max_width = max(config.max_width for config in pallet_configs)
    max_length = max(config.max_length for config in pallet_configs)
    max_height = max(config.max_height for config in pallet_configs)
    max_weight = max(config.max_weight for config in pallet_configs)
    
    features = []
    for box in boxes:
        # Características básicas normalizadas
        weight_norm = box.weight / max_weight
        width_norm = box.width / max_width
        length_norm = box.length / max_length
        height_norm = box.height / max_height
        
        # Densidad (peso/volumen)
        volume = box.width * box.length * box.height
        density = box.weight / volume if volume > 0 else 0
        
        # Proporciones de dimensiones
        width_length_ratio = box.width / box.length if box.length > 0 else 1
        height_width_ratio = box.height / box.width if box.width > 0 else 1
        
        # Normalizar proporciones (log para evitar valores extremos)
        width_length_ratio_norm = np.log1p(width_length_ratio) / np.log(10)
        height_width_ratio_norm = np.log1p(height_width_ratio) / np.log(10)
        
        features.append([
            weight_norm,
            width_norm,
            length_norm,
            height_norm,
            density,
            width_length_ratio_norm,
            height_width_ratio_norm
        ])
    
    return np.array(features)

def preprocess_knn_clustering(csv_file_path: str, pallet_configs: List) -> Dict[int, int]:
    """
    Pre-procesa el clustering KNN con todas las cajas del CSV.
    
    Args:
        csv_file_path: Ruta al archivo CSV con todas las cajas
        pallet_configs: Lista de configuraciones de pallets
    
    Returns:
        Diccionario {caja_id: pallet_id} con las asignaciones predefinidas
    """
    import pandas as pd
    
    print(f"🔍 KNN Pre-procesamiento: Cargando y analizando todas las cajas del CSV...")
    
    try:
        # Cargar todas las cajas del CSV
        df = pd.read_csv(csv_file_path)
        all_boxes = []
        
        for _, row in df.iterrows():
            try:
                box = Box(
                    id=str(row['id']),
                    width=float(row['width']),
                    length=float(row['length']),
                    height=float(row['height']),
                    weight=float(row['weight'])
                )
                all_boxes.append(box)
            except Exception as e:
                print(f"⚠️ Error creando caja {row.get('id', 'N/A')}: {e}")
                continue
        
        if not all_boxes:
            print("❌ No se pudieron cargar cajas del CSV")
            return {}
        
        num_pallets = len(pallet_configs)
        print(f"📦 Total de cajas cargadas: {len(all_boxes)}")
        print(f"🎯 Clustering en {num_pallets} grupos...")
        
        # Caso especial: si hay menos cajas que pallets
        if len(all_boxes) < num_pallets:
            print(f"⚠️ Caso especial: {len(all_boxes)} cajas < {num_pallets} pallets. Asignando secuencialmente.")
            assignments = {}
            for i, box in enumerate(all_boxes):
                assignments[int(box.id)] = i % num_pallets
            return assignments
        
        # Normalizar características de todas las cajas
        features = normalize_box_features(all_boxes, pallet_configs)
        
        if len(features) == 0:
            print("❌ Error en normalización de características")
            return {}
        
        # Aplicar K-means clustering
        kmeans = KMeans(n_clusters=num_pallets, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features)
        
        # Crear diccionario de asignaciones
        assignments = {}
        for i, box in enumerate(all_boxes):
            cluster_id = cluster_labels[i]
            assignments[int(box.id)] = cluster_id
        
        print(f"✅ KNN Pre-procesamiento completado. {len(assignments)} cajas asignadas a {num_pallets} pallets")
        
        # Mostrar estadísticas del clustering
        for i in range(num_pallets):
            cajas_en_pallet = sum(1 for pallet_id in assignments.values() if pallet_id == i)
            print(f"   Pallet {i+1}: {cajas_en_pallet} cajas")
        
        return assignments
        
    except Exception as e:
        print(f"❌ Error en pre-procesamiento KNN: {e}")
        return {}

def knn_based_palletization(boxes: List[Box], pallet_configs: List, step_x: float = 1.0, step_y: float = 1.0, step_z: float = 1.0, precomputed_assignments: Dict[int, int] = None) -> List[Pallet]:
    """
    Algoritmo de paletización basado en KNN clustering pre-procesado.
    
    Args:
        boxes: Lista de cajas a paletizar
        pallet_configs: Lista de configuraciones de pallets
        step_x, step_y, step_z: Pasos de búsqueda de posición
        precomputed_assignments: Diccionario pre-computado de asignaciones caja->pallet
    
    Returns:
        Lista de pallets con las cajas colocadas
    """
    if not boxes or not pallet_configs:
        return []
    
    num_pallets = len(pallet_configs)
    
    if precomputed_assignments is None:
        print("❌ ERROR: Se requieren asignaciones pre-computadas para KNN-Based")
        return []
    
    print(f"🎯 KNN Paletization: Procesando {len(boxes)} cajas usando asignaciones pre-computadas")
    
    # Crear pallets
    pallets = []
    for i, config in enumerate(pallet_configs):
        pallet = Pallet(
            max_width=config.max_width,
            max_length=config.max_length,
            max_height=config.max_height,
            max_weight=config.max_weight
        )
        pallets.append(pallet)
    
    # Crear pallet de desechos infinito
    waste_pallet = Pallet(float('inf'), float('inf'), float('inf'), float('inf'), is_waste_pallet=True)
    waste_pallet.algorithm = "waste_pallet"
    pallets.append(waste_pallet)
    
    # Asignar cajas a pallets según clustering pre-computado
    for box in boxes:
        box_id = int(box.id)
        
        if box_id not in precomputed_assignments:
            print(f"⚠️ Caja {box.id} no encontrada en asignaciones pre-computadas. Asignando al Pallet 1")
            target_pallet = pallets[0]
        else:
            pallet_id = precomputed_assignments[box_id]
            target_pallet = pallets[pallet_id]
        
        print(f"📦 Caja {box.id} (Peso: {box.weight} kg) → Pallet {pallet_id + 1}")
        
        # Intentar colocar la caja en el pallet asignado primero
        placed = False
        if target_pallet.can_fit(box):
            result = target_pallet.find_best_position(box, step_x, step_y, step_z)
            if result:
                # El resultado ahora es (oriented_box, position)
                oriented_box, position = result
                x, y, z = position
                oriented_box.position = (x, y, z)
                target_pallet.boxes.append(oriented_box)
                target_pallet.current_weight += oriented_box.weight
                print(f"✅ Caja {oriented_box.id} colocada exitosamente en Pallet {pallet_id + 1} (orientación: {oriented_box.orientation.name})")
                placed = True
        
        # Si no se pudo colocar en el pallet asignado, intentar en otros pallets
        if not placed:
            for i, pallet in enumerate(pallets):
                if not pallet.is_waste_pallet and pallet.can_fit(box):
                    result = pallet.find_best_position(box, step_x, step_y, step_z)
                    if result:
                        oriented_box, position = result
                        x, y, z = position
                        oriented_box.position = (x, y, z)
                        pallet.boxes.append(oriented_box)
                        pallet.current_weight += oriented_box.weight
                        print(f"✅ Caja {oriented_box.id} colocada exitosamente en Pallet {i + 1} (orientación: {oriented_box.orientation.name})")
                        placed = True
                        break
        
        # Si no se pudo colocar en ningún pallet regular, enviar al pallet de desechos
        if not placed:
            print(f"⚠️ Caja {box.id} no pudo ser colocada en ningún pallet regular - Enviando al pallet de desechos")
            waste_pallet.place_box(box)
            print(f"✅ Caja {box.id} enviada al pallet de desechos")
    
    print(f"🎯 KNN Paletization: Completado. {num_pallets} pallets creados")
    return pallets 