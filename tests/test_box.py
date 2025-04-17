import pytest
from src.core.box import Box

def test_box_creation():
    """Test para verificar la creación correcta de una caja."""
    box = Box(id=1, width=10, length=20, height=30, weight=40)
    assert box.id == 1
    assert box.width == 10
    assert box.length == 20
    assert box.height == 30
    assert box.weight == 40
    assert box.position == (0, 0, 0)

def test_box_volume():
    """Test para verificar el cálculo del volumen de una caja."""
    box = Box(id=1, width=2, length=3, height=4, weight=5)
    assert box.volume() == 24  # 2 * 3 * 4 = 24

def test_box_position():
    """Test para verificar la asignación de posición de una caja."""
    box = Box(id=1, width=10, length=20, height=30, weight=40)
    box.position = (1, 2, 3)
    assert box.position == (1, 2, 3)

def test_box_invalid_dimensions():
    """Test para verificar que no se pueden crear cajas con dimensiones inválidas."""
    with pytest.raises(ValueError):
        Box(id=1, width=0, length=20, height=30, weight=40)
    with pytest.raises(ValueError):
        Box(id=1, width=10, length=-5, height=30, weight=40)
    with pytest.raises(ValueError):
        Box(id=1, width=10, length=20, height=0, weight=40)
    with pytest.raises(ValueError):
        Box(id=1, width=10, length=20, height=30, weight=-10) 