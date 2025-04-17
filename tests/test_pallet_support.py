import pytest
from src.core.pallet import Pallet
from src.core.box import Box

def test_box_support():
    # Crear un pallet
    pallet = Pallet(1, 100, 100, 200, 1000)
    
    # Agregar una caja base
    base_box = Box(1, 30, 30, 20, 10)
    assert pallet.add_box(base_box)
    
    # Intentar agregar una caja que no está soportada
    unsupported_box = Box(2, 20, 20, 20, 5)
    assert not pallet.add_box(unsupported_box)  # No debería poder agregarse
    
    # Agregar una caja que sí está soportada
    supported_box = Box(3, 20, 20, 20, 5)
    supported_box.position = (5, 5, 20)  # Justo encima de la caja base
    assert pallet._is_position_supported(5, 5, supported_box, 20)
    
    # Verificar soporte parcial
    partially_supported_box = Box(4, 40, 40, 20, 8)
    assert not pallet._is_position_supported(0, 0, partially_supported_box, 20)

def test_multiple_supporting_boxes():
    pallet = Pallet(1, 100, 100, 200, 1000)
    
    # Agregar dos cajas base
    box1 = Box(1, 30, 30, 20, 10)
    box2 = Box(2, 30, 30, 20, 10)
    assert pallet.add_box(box1)
    assert pallet.add_box(box2)
    
    # Agregar una caja que descansa sobre ambas
    supported_box = Box(3, 40, 40, 20, 5)
    assert pallet._is_position_supported(10, 10, supported_box, 20)

def test_edge_support():
    pallet = Pallet(1, 100, 100, 200, 1000)
    
    # Agregar cajas en los bordes
    box1 = Box(1, 30, 30, 20, 10)
    box2 = Box(2, 30, 30, 20, 10)
    assert pallet.add_box(box1)
    box2.position = (70, 70, 0)
    assert pallet.add_box(box2)
    
    # Verificar soporte en el borde
    edge_box = Box(3, 20, 20, 20, 5)
    assert not pallet._is_position_supported(60, 60, edge_box, 20) 