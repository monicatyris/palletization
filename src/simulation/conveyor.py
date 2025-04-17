import pandas as pd
import time
from typing import List
from ..core.box import Box
from ..core.pallet import Pallet
from ..core.algorithms import first_fit_palletization

class CintaTransportadora:
    """Clase que simula una cinta transportadora para el procesamiento de cajas."""
    
    def __init__(self, archivo_cajas: str, intervalo_segundos: float = 2.0):
        """
        Inicializa la cinta transportadora.
        
        Args:
            archivo_cajas: Ruta al archivo CSV con los datos de las cajas
            intervalo_segundos: Tiempo entre la llegada de cada caja
        """
        self.archivo_cajas = archivo_cajas
        self.intervalo_segundos = intervalo_segundos
        self.cajas: List[Box] = []
        self.pallets: List[Pallet] = []
        self.max_width = 100  # cm
        self.max_length = 100  # cm
        self.max_height = 150  # cm
        self.max_weight = 1000  # kg

    def cargar_cajas(self) -> None:
        """Carga las cajas desde el archivo CSV y simula su llegada a la cinta."""
        df = pd.read_csv(self.archivo_cajas)
        print("\n📦 Cargando cajas de la cinta transportadora...")
        print("=" * 50)
        
        for _, row in df.iterrows():
            # Simular el tiempo que tarda en llegar cada caja
            time.sleep(self.intervalo_segundos)
            
            # Crear la caja
            box = Box(
                id=int(row['id']),
                width=float(row['width']),
                length=float(row['length']),
                height=float(row['height']),
                weight=float(row['weight'])
            )
            
            print(f"\n⏳ Nueva caja detectada en la cinta:")
            print(f"   ID: {box.id}")
            print(f"   Dimensiones: {box.width}x{box.length}x{box.height} cm")
            print(f"   Peso: {box.weight} kg")
            
            # Añadir la caja a la lista
            self.cajas.append(box)
            
            # Realizar la paletización con las cajas disponibles hasta el momento
            self.pallets = first_fit_palletization(
                boxes=self.cajas,
                max_width=self.max_width,
                max_length=self.max_length,
                max_height=self.max_height,
                max_weight=self.max_weight
            )
            
            # Mostrar estado actual de la paletización
            print("\n📊 Estado actual de la paletización:")
            print(f"   Cajas procesadas: {len(self.cajas)}")
            print(f"   Pallets utilizados: {len(self.pallets)}")

def simular_cinta(archivo_cajas: str, intervalo_segundos: float = 3.0) -> None:
    """
    Función principal para ejecutar la simulación de la cinta transportadora.
    
    Args:
        archivo_cajas: Ruta al archivo CSV con los datos de las cajas
        intervalo_segundos: Tiempo entre la llegada de cada caja
    """
    # Crear instancia de la cinta transportadora
    cinta = CintaTransportadora(
        archivo_cajas=archivo_cajas,
        intervalo_segundos=intervalo_segundos
    )
    
    # Iniciar la simulación
    print("\n🔄 Iniciando simulación de cinta transportadora...")
    print("=" * 50)
    cinta.cargar_cajas()
    
    # Mostrar resumen final
    print("\n✅ Simulación completada")
    print("=" * 50) 