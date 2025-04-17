import pytest
import matplotlib.pyplot as plt
from src.core.box import Box
from src.core.pallet import Pallet
from src.visualization.plotter import visualize_pallets, print_palletization_summary

def test_visualize_pallets():
    """Test para verificar que la función de visualización no genera errores."""
    # Crear un pallet con algunas cajas
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    box1 = Box(id=1, width=50, length=50, height=50, weight=100)
    box2 = Box(id=2, width=30, length=30, height=30, weight=50)
    
    # Añadir cajas al pallet
    pallet.add_box(box1)
    pallet.add_box(box2)
    
    # Intentar visualizar (no debería generar errores)
    try:
        visualize_pallets([pallet])
        plt.close('all')  # Cerrar todas las figuras
        assert True
    except Exception as e:
        pytest.fail(f"La visualización generó un error: {str(e)}")

def test_print_palletization_summary(capsys):
    """Test para verificar que la función de resumen imprime correctamente."""
    # Crear un pallet con algunas cajas
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    box1 = Box(id=1, width=50, length=50, height=50, weight=100)
    box2 = Box(id=2, width=30, length=30, height=30, weight=50)
    
    # Añadir cajas al pallet
    pallet.add_box(box1)
    pallet.add_box(box2)
    
    # Capturar la salida impresa
    print_palletization_summary([pallet])
    captured = capsys.readouterr()
    
    # Verificar que la salida contiene la información esperada
    assert "Resumen de Paletización" in captured.out
    assert "Pallet 1" in captured.out
    assert "Cajas asignadas: 2" in captured.out
    assert "Peso total: 150.00 / 1000" in captured.out
    assert "Caja 1" in captured.out
    assert "Caja 2" in captured.out

def test_visualize_empty_pallet():
    """Test para verificar la visualización de un pallet vacío."""
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    
    try:
        visualize_pallets([pallet])
        plt.close('all')
        assert True
    except Exception as e:
        pytest.fail(f"La visualización de pallet vacío generó un error: {str(e)}")

def test_visualize_multiple_pallets():
    """Test para verificar la visualización de múltiples pallets."""
    # Crear dos pallets con cajas
    pallet1 = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    pallet2 = Pallet(id=2, max_width=100, max_length=100, max_height=150, max_weight=1000)
    
    box1 = Box(id=1, width=50, length=50, height=50, weight=100)
    box2 = Box(id=2, width=30, length=30, height=30, weight=50)
    
    pallet1.add_box(box1)
    pallet2.add_box(box2)
    
    try:
        visualize_pallets([pallet1, pallet2])
        plt.close('all')
        assert True
    except Exception as e:
        pytest.fail(f"La visualización de múltiples pallets generó un error: {str(e)}")

def test_print_empty_palletization(capsys):
    """Test para verificar el resumen de una paletización vacía."""
    print_palletization_summary([])
    captured = capsys.readouterr()
    
    assert "Resumen de Paletización" in captured.out
    assert "No hay pallets para mostrar" in captured.out 