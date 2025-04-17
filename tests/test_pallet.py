import pytest
from src.core.box import Box
from src.core.pallet import Pallet

def test_pallet_creation():
    """Test para verificar la creación correcta de un pallet."""
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    assert pallet.id == 1
    assert pallet.max_width == 100
    assert pallet.max_length == 100
    assert pallet.max_height == 150
    assert pallet.max_weight == 1000
    assert len(pallet.boxes) == 0
    assert pallet.current_weight == 0

def test_pallet_add_box():
    """Test para verificar la adición de cajas a un pallet."""
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    box = Box(id=1, width=50, length=50, height=50, weight=100)
    
    assert pallet.add_box(box) is True
    assert len(pallet.boxes) == 1
    assert pallet.current_weight == 100
    assert box in pallet.boxes

def test_pallet_add_box_exceeds_dimensions():
    """Test para verificar que no se pueden añadir cajas que exceden las dimensiones del pallet."""
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    box = Box(id=1, width=150, length=50, height=50, weight=100)
    
    assert pallet.add_box(box) is False
    assert len(pallet.boxes) == 0
    assert pallet.current_weight == 0

def test_pallet_add_box_exceeds_weight():
    """Test para verificar que no se pueden añadir cajas que exceden el peso máximo del pallet."""
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    box1 = Box(id=1, width=50, length=50, height=50, weight=600)
    box2 = Box(id=2, width=50, length=50, height=50, weight=500)
    
    assert pallet.add_box(box1) is True
    assert pallet.add_box(box2) is False
    assert len(pallet.boxes) == 1
    assert pallet.current_weight == 600

def test_pallet_add_box_collision():
    """Test para verificar que no se pueden añadir cajas que colisionan con otras."""
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    box1 = Box(id=1, width=50, length=50, height=50, weight=100)
    box2 = Box(id=2, width=50, length=50, height=50, weight=100)
    
    assert pallet.add_box(box1) is True
    box1.position = (0, 0, 0)  # Forzar posición para el test
    assert pallet.add_box(box2) is False  # Debería colisionar
    assert len(pallet.boxes) == 1
    assert pallet.current_weight == 100

def test_pallet_add_box_multiple_layers():
    """Test para verificar la adición de cajas en múltiples capas."""
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    box1 = Box(id=1, width=50, length=50, height=50, weight=100)
    box2 = Box(id=2, width=50, length=50, height=50, weight=100)
    
    assert pallet.add_box(box1) is True
    box1.position = (0, 0, 0)  # Forzar posición para el test
    assert pallet.add_box(box2) is True  # Debería ir en la siguiente capa
    assert len(pallet.boxes) == 2
    assert pallet.current_weight == 200 