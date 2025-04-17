import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from core.pallet import Pallet
from core.box import Box
from matplotlib.colors import LinearSegmentedColormap
from typing import List

def get_box_color(weight: float) -> tuple:
    """
    Asigna un color a la caja basado en su peso usando un gradiente fijo.
    Los colores se asignan en rangos de 10 kg desde 0 a 60 kg.
    Para pesos mayores a 60 kg se usa un rojo oscuro.
    """
    # Definir los rangos de peso y sus colores correspondientes
    weight_ranges = [
        (0, 10),    # 0-10 kg
        (10, 20),   # 10-20 kg
        (20, 30),   # 20-30 kg
        (30, 40),   # 30-40 kg
        (40, 50),   # 40-50 kg
        (50, 60)    # 50-60 kg
    ]
    
    # Colores del gradiente viridis (6 colores)
    colors = [
        (0.267004, 0.004874, 0.329415),  # Morado oscuro
        (0.127568, 0.566949, 0.550556),  # Verde azulado
        (0.369214, 0.788888, 0.382914),  # Verde claro
        (0.993248, 0.906157, 0.143936),  # Amarillo
        (0.988235, 0.552941, 0.235294),  # Naranja
        (0.988235, 0.121569, 0.121569),  # Rojo
        (0.5, 0.0, 0.0)                  # Rojo oscuro para >60 kg
    ]
    
    # Encontrar el rango correspondiente al peso
    for i, (min_weight, max_weight) in enumerate(weight_ranges):
        if min_weight <= weight < max_weight:
            return colors[i]
    
    # Si el peso es mayor a 60 kg, usar rojo oscuro
    return colors[-1]

def visualize_pallets(pallets: List[Pallet], rotation_angle: float = 45) -> plt.Figure:
    """
    Visualiza los pallets en 3D usando matplotlib.
    
    Returns:
        plt.Figure: La figura de matplotlib con la visualización
    """
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Dibujar cada pallet
    for pallet in pallets:
        # Dibujar el pallet (base)
        ax.bar3d(0, 0, 0, 
                pallet.max_width, pallet.max_length, 0.1,
                color='gray', alpha=0.3)
        
        # Dibujar cada caja en el pallet
        for box in pallet.boxes:
            color = get_box_color(box.weight)
            ax.bar3d(box.position[0], box.position[1], box.position[2],
                    box.width, box.length, box.height,
                    color=color, alpha=0.8)
    
    # Configurar la vista
    ax.view_init(elev=20, azim=rotation_angle)
    ax.set_xlabel('Ancho (cm)')
    ax.set_ylabel('Largo (cm)')
    ax.set_zlabel('Alto (cm)')
    
    # Crear la barra de colores personalizada
    from matplotlib.colors import ListedColormap
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import BoundaryNorm
    
    # Definir los colores y los límites de los rangos
    colors = [
        (0.267004, 0.004874, 0.329415),  # Morado oscuro (0-10 kg)
        (0.127568, 0.566949, 0.550556),  # Verde azulado (10-20 kg)
        (0.369214, 0.788888, 0.382914),  # Verde claro (20-30 kg)
        (0.993248, 0.906157, 0.143936),  # Amarillo (30-40 kg)
        (0.988235, 0.552941, 0.235294),  # Naranja (40-50 kg)
        (0.988235, 0.121569, 0.121569),  # Rojo (50-60 kg)
        (0.5, 0.0, 0.0)                  # Rojo oscuro (>60 kg)
    ]
    
    # Definir los límites de los rangos
    bounds = [0, 10, 20, 30, 40, 50, 60, 70]
    
    # Crear el mapa de colores personalizado
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(bounds, cmap.N)
    
    # Crear el mapeador de colores
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    
    # Añadir la barra de colores
    cbar = plt.colorbar(sm, ax=ax, orientation='vertical', pad=0.1)
    cbar.set_label('Peso (kg)')
    
    # Establecer los ticks y etiquetas de la barra de colores
    cbar.set_ticks([5, 15, 25, 35, 45, 55, 65])
    cbar.set_ticklabels(['0-10', '10-20', '20-30', '30-40', '40-50', '50-60', '>60'])
    
    plt.tight_layout()
    return fig

def print_palletization_summary(pallets: List[Pallet]) -> None:
    """Imprime un resumen de la paletización."""
    print(f"\nResumen de Paletización:")
    print(f"Total de pallets utilizados: {len(pallets)}")
    
    for i, pallet in enumerate(pallets, 1):
        print(f"\nPallet {i}:")
        print(f"- Peso total: {pallet.current_weight:.1f} kg")
        print(f"- Número de cajas: {len(pallet.boxes)}")
        print(f"- Altura utilizada: {max((box.position[2] + box.height for box in pallet.boxes), default=0):.1f} cm")
        
        # Agrupar cajas por capa
        layers = {}
        for box in pallet.boxes:
            z = box.position[2]
            if z not in layers:
                layers[z] = []
            layers[z].append(box)
        
        print("\nDistribución por capas:")
        for z in sorted(layers.keys()):
            print(f"  Capa a {z} cm:")
            for box in layers[z]:
                print(f"    - Caja {box.id}: {box.width}x{box.length}x{box.height} cm, {box.weight} kg") 