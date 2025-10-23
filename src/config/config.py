from dataclasses import dataclass
from typing import Dict, Any, List
import yaml
import os

@dataclass
class PalletConfig:
    """Configuración de un pallet individual."""
    max_width: float = 120.0  # cm
    max_length: float = 100.0  # cm
    max_height: float = 200.0  # cm
    max_weight: float = 1000.0  # kg

@dataclass
class ConveyorConfig:
    """Configuración de la cinta transportadora."""
    interval_seconds: float = 2.0  # segundos entre cajas
    input_file: str = "data/cajas_entrada.csv"

@dataclass
class AppConfig:
    """Configuración general de la aplicación."""
    pallets: List[PalletConfig]  # Lista de configuraciones de pallets
    conveyor: ConveyorConfig

def load_config(config_path: str = "config/default_config.yaml") -> AppConfig:
    """
    Carga la configuración desde un archivo YAML.
    
    Args:
        config_path: Ruta al archivo de configuración
        
    Returns:
        Objeto AppConfig con la configuración cargada
    """
    if not os.path.exists(config_path):
        # Si no existe el archivo, usar valores por defecto
        return AppConfig(
            pallets=[PalletConfig()],  # Un pallet por defecto
            conveyor=ConveyorConfig()
        )
    
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    
    # Cargar configuración de pallets
    pallets_data = config_data.get('pallets', [{}])
    pallets_config = [PalletConfig(**pallet_data) for pallet_data in pallets_data]
    
    # Si no hay pallets configurados, usar uno por defecto
    if not pallets_config:
        pallets_config = [PalletConfig()]
    
    conveyor_config = ConveyorConfig(**config_data.get('conveyor', {}))
    
    return AppConfig(
        pallets=pallets_config,
        conveyor=conveyor_config
    )

def save_config(config: AppConfig, config_path: str = "config/default_config.yaml") -> None:
    """
    Guarda la configuración en un archivo YAML.
    
    Args:
        config: Objeto AppConfig con la configuración
        config_path: Ruta donde guardar el archivo de configuración
    """
    config_dict = {
        'pallets': [
            {
                'max_width': pallet.max_width,
                'max_length': pallet.max_length,
                'max_height': pallet.max_height,
                'max_weight': pallet.max_weight
            }
            for pallet in config.pallets
        ],
        'conveyor': {
            'interval_seconds': config.conveyor.interval_seconds,
            'input_file': config.conveyor.input_file
        }
    }
    
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False) 