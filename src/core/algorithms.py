from typing import List
from .box import Box
from .pallet import Pallet

def first_fit_palletization(boxes: List[Box], 
                          max_width: float, 
                          max_length: float, 
                          max_height: float, 
                          max_weight: float) -> List[Pallet]:
    """
    Implementa el algoritmo First-Fit para paletización.
    
    Args:
        boxes: Lista de cajas a paletizar
        max_width: Ancho máximo del pallet
        max_length: Largo máximo del pallet
        max_height: Alto máximo del pallet
        max_weight: Peso máximo del pallet
        
    Returns:
        Lista de pallets con las cajas asignadas
    """
    pallets = []
    current_pallet_id = 1

    for box in boxes:
        placed = False
        
        # Intentar colocar en pallets existentes
        for pallet in pallets:
            if pallet.add_box(box):
                placed = True
                break
        
        # Si no se pudo colocar, crear nuevo pallet
        if not placed:
            new_pallet = Pallet(current_pallet_id, max_width, max_length, max_height, max_weight)
            if new_pallet.add_box(box):
                pallets.append(new_pallet)
                current_pallet_id += 1
            else:
                print(f"Advertencia: La caja {box.id} no pudo ser colocada en ningún pallet")

    return pallets 