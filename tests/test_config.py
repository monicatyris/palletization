import pytest
import os
import tempfile
import yaml
from src.config.config import load_config, save_config, AppConfig, PalletConfig, ConveyorConfig

def test_pallet_config_creation():
    """Test para verificar la creación de configuración de pallet."""
    config = PalletConfig()
    assert config.max_width == 120.0
    assert config.max_length == 100.0
    assert config.max_height == 200.0
    assert config.max_weight == 1000.0

def test_conveyor_config_creation():
    """Test para verificar la creación de configuración de cinta transportadora."""
    config = ConveyorConfig()
    assert config.interval_seconds == 2.0
    assert config.input_file == "data/cajas_entrada.csv"

def test_app_config_creation():
    """Test para verificar la creación de configuración de la aplicación."""
    pallet_config = PalletConfig()
    conveyor_config = ConveyorConfig()
    app_config = AppConfig(pallet=pallet_config, conveyor=conveyor_config)
    
    assert app_config.pallet == pallet_config
    assert app_config.conveyor == conveyor_config

def test_load_config_default():
    """Test para verificar la carga de configuración por defecto."""
    config = load_config("non_existent_file.yaml")
    assert isinstance(config, AppConfig)
    assert isinstance(config.pallet, PalletConfig)
    assert isinstance(config.conveyor, ConveyorConfig)

def test_save_and_load_config():
    """Test para verificar el guardado y carga de configuración."""
    # Crear un archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml')
    try:
        # Crear configuración
        pallet_config = PalletConfig(
            max_width=150.0,
            max_length=120.0,
            max_height=180.0,
            max_weight=1200.0
        )
        conveyor_config = ConveyorConfig(
            interval_seconds=3.0,
            input_file="data/ejemplo.csv"
        )
        app_config = AppConfig(pallet=pallet_config, conveyor=conveyor_config)
        
        # Guardar configuración
        save_config(app_config, temp_file.name)
        
        # Cargar configuración
        loaded_config = load_config(temp_file.name)
        
        # Verificar que los valores se cargaron correctamente
        assert loaded_config.pallet.max_width == 150.0
        assert loaded_config.pallet.max_length == 120.0
        assert loaded_config.pallet.max_height == 180.0
        assert loaded_config.pallet.max_weight == 1200.0
        assert loaded_config.conveyor.interval_seconds == 3.0
        assert loaded_config.conveyor.input_file == "data/ejemplo.csv"
    finally:
        os.unlink(temp_file.name)

def test_load_invalid_config():
    """Test para verificar el manejo de archivos de configuración inválidos."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.yaml')
    try:
        # Escribir un archivo YAML inválido
        with open(temp_file.name, 'w') as f:
            f.write("invalid: yaml: content")
        
        # Debería cargar la configuración por defecto
        config = load_config(temp_file.name)
        assert isinstance(config, AppConfig)
    finally:
        os.unlink(temp_file.name)

def test_config_validation():
    """Test para verificar la validación de valores de configuración."""
    with pytest.raises(ValueError):
        PalletConfig(max_width=-100)
    
    with pytest.raises(ValueError):
        PalletConfig(max_length=0)
    
    with pytest.raises(ValueError):
        PalletConfig(max_height=-50)
    
    with pytest.raises(ValueError):
        PalletConfig(max_weight=0)
    
    with pytest.raises(ValueError):
        ConveyorConfig(interval_seconds=-1) 