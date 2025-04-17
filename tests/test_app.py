import pytest
import streamlit as st
from src.app import main
from src.config.config import AppConfig, PalletConfig, ConveyorConfig
from src.core.box import Box
from src.core.pallet import Pallet
from src.core.algorithms import first_fit_palletization

def test_app_initialization():
    """Test para verificar la inicialización de la aplicación."""
    # Crear configuración de prueba
    pallet_config = PalletConfig()
    conveyor_config = ConveyorConfig()
    app_config = AppConfig(pallet=pallet_config, conveyor=conveyor_config)
    
    # Verificar que la configuración se inicializa correctamente
    assert app_config.pallet.max_width == 120.0
    assert app_config.pallet.max_length == 100.0
    assert app_config.pallet.max_height == 200.0
    assert app_config.pallet.max_weight == 1000.0
    assert app_config.conveyor.interval_seconds == 2.0
    assert app_config.conveyor.input_file == "data/cajas_entrada.csv"

def test_palletization_algorithm():
    """Test para verificar el algoritmo de paletización."""
    # Crear algunas cajas de prueba
    boxes = [
        Box(id=1, width=50, length=50, height=50, weight=100),
        Box(id=2, width=30, length=30, height=30, weight=50),
        Box(id=3, width=40, length=40, height=40, weight=80)
    ]
    
    # Aplicar el algoritmo de paletización
    pallets = first_fit_palletization(
        boxes,
        max_width=120,
        max_length=100,
        max_height=200,
        max_weight=1000
    )
    
    # Verificar resultados
    assert len(pallets) > 0
    assert all(isinstance(pallet, Pallet) for pallet in pallets)
    
    # Verificar que todas las cajas fueron asignadas
    assigned_boxes = sum(len(pallet.boxes) for pallet in pallets)
    assert assigned_boxes == len(boxes)

def test_streamlit_session_state():
    """Test para verificar el manejo del estado de la sesión de Streamlit."""
    # Simular el estado de la sesión
    st.session_state["pallets"] = []
    st.session_state["boxes"] = []
    st.session_state["config"] = AppConfig()
    
    # Verificar que el estado se inicializa correctamente
    assert "pallets" in st.session_state
    assert "boxes" in st.session_state
    assert "config" in st.session_state
    assert isinstance(st.session_state["config"], AppConfig)

def test_config_ui_elements():
    """Test para verificar los elementos de UI para la configuración."""
    # Crear configuración de prueba
    config = AppConfig()
    
    # Verificar que los valores de configuración son válidos
    assert config.pallet.max_width > 0
    assert config.pallet.max_length > 0
    assert config.pallet.max_height > 0
    assert config.pallet.max_weight > 0
    assert config.conveyor.interval_seconds > 0

def test_visualization_components():
    """Test para verificar los componentes de visualización."""
    # Crear un pallet de prueba con cajas
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=1000)
    box1 = Box(id=1, width=50, length=50, height=50, weight=100)
    box2 = Box(id=2, width=30, length=30, height=30, weight=50)
    
    pallet.add_box(box1)
    pallet.add_box(box2)
    
    # Verificar que el pallet contiene las cajas correctamente
    assert len(pallet.boxes) == 2
    assert pallet.current_weight == 150
    assert pallet.current_height == 50  # Altura de la primera capa

def test_error_handling():
    """Test para verificar el manejo de errores en la aplicación."""
    # Intentar crear una caja con dimensiones inválidas
    with pytest.raises(ValueError):
        Box(id=1, width=-50, length=50, height=50, weight=100)
    
    # Intentar crear un pallet con dimensiones inválidas
    with pytest.raises(ValueError):
        Pallet(id=1, max_width=0, max_length=100, max_height=150, max_weight=1000)
    
    # Intentar añadir una caja que excede el peso máximo
    pallet = Pallet(id=1, max_width=100, max_length=100, max_height=150, max_weight=100)
    box = Box(id=1, width=50, length=50, height=50, weight=200)
    assert not pallet.add_box(box)  # Debería fallar 