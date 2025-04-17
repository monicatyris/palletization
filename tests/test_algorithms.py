import pytest
from src.core.box import Box
from src.core.pallet import Pallet
from src.core.algorithms import first_fit_palletization

def test_first_fit_palletization_single_box():
    """Test para verificar la paletización de una sola caja."""
    boxes = [Box(id=1, width=50, length=50, height=50, weight=100)]
    pallets = first_fit_palletization(
        boxes=boxes,
        max_width=100,
        max_length=100,
        max_height=150,
        max_weight=1000
    )
    
    assert len(pallets) == 1
    assert len(pallets[0].boxes) == 1
    assert pallets[0].boxes[0].id == 1

def test_first_fit_palletization_multiple_boxes():
    """Test para verificar la paletización de múltiples cajas."""
    boxes = [
        Box(id=1, width=50, length=50, height=50, weight=100),
        Box(id=2, width=50, length=50, height=50, weight=100),
        Box(id=3, width=50, length=50, height=50, weight=100)
    ]
    pallets = first_fit_palletization(
        boxes=boxes,
        max_width=100,
        max_length=100,
        max_height=150,
        max_weight=1000
    )
    
    assert len(pallets) == 1
    assert len(pallets[0].boxes) == 3
    assert all(box.id in [1, 2, 3] for box in pallets[0].boxes)

def test_first_fit_palletization_multiple_pallets():
    """Test para verificar la creación de múltiples pallets cuando es necesario."""
    boxes = [
        Box(id=1, width=80, length=80, height=80, weight=800),
        Box(id=2, width=80, length=80, height=80, weight=800)
    ]
    pallets = first_fit_palletization(
        boxes=boxes,
        max_width=100,
        max_length=100,
        max_height=150,
        max_weight=1000
    )
    
    assert len(pallets) == 2
    assert len(pallets[0].boxes) == 1
    assert len(pallets[1].boxes) == 1
    assert pallets[0].boxes[0].id == 1
    assert pallets[1].boxes[0].id == 2

def test_first_fit_palletization_exceeds_dimensions():
    """Test para verificar el manejo de cajas que exceden las dimensiones del pallet."""
    boxes = [Box(id=1, width=150, length=150, height=150, weight=100)]
    pallets = first_fit_palletization(
        boxes=boxes,
        max_width=100,
        max_length=100,
        max_height=150,
        max_weight=1000
    )
    
    assert len(pallets) == 0  # No se debería crear ningún pallet

def test_first_fit_palletization_exceeds_weight():
    """Test para verificar el manejo de cajas que exceden el peso máximo del pallet."""
    boxes = [Box(id=1, width=50, length=50, height=50, weight=1500)]
    pallets = first_fit_palletization(
        boxes=boxes,
        max_width=100,
        max_length=100,
        max_height=150,
        max_weight=1000
    )
    
    assert len(pallets) == 0  # No se debería crear ningún pallet

def test_first_fit_palletization_optimal_placement():
    """Test para verificar la colocación óptima de cajas en el pallet."""
    boxes = [
        Box(id=1, width=50, length=50, height=50, weight=100),
        Box(id=2, width=30, length=30, height=30, weight=50),
        Box(id=3, width=20, length=20, height=20, weight=30)
    ]
    pallets = first_fit_palletization(
        boxes=boxes,
        max_width=100,
        max_length=100,
        max_height=150,
        max_weight=1000
    )
    
    assert len(pallets) == 1
    assert len(pallets[0].boxes) == 3
    
    # Verificar que las cajas están colocadas de manera óptima
    box_positions = [box.position for box in pallets[0].boxes]
    assert len(set(box_positions)) == 3  # Todas las posiciones deben ser únicas 