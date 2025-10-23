import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from core.pallet import Pallet
from core.box import Box
from matplotlib.colors import LinearSegmentedColormap
from typing import List

def get_box_color(weight: float) -> tuple:
    """
    Asigna un color a la caja basado en su peso usando un gradiente optimizado para 0-10 kg.
    Los colores se asignan en rangos de 1 kg desde 0 a 10 kg.
    Para pesos mayores a 10 kg se usa un rojo oscuro.
    """
    # Definir los rangos de peso y sus colores correspondientes (0-10 kg)
    weight_ranges = [
        (0, 1),     # 0-1 kg
        (1, 2),     # 1-2 kg
        (2, 3),     # 2-3 kg
        (3, 4),     # 3-4 kg
        (4, 5),     # 4-5 kg
        (5, 6),     # 5-6 kg
        (6, 7),     # 6-7 kg
        (7, 8),     # 7-8 kg
        (8, 9),     # 8-9 kg
        (9, 10)     # 9-10 kg
    ]
    
    # Colores del gradiente optimizado para 0-10 kg (10 colores)
    colors = [
        (0.267004, 0.004874, 0.329415),  # Morado muy oscuro (0-1 kg)
        (0.190631, 0.407061, 0.556089),  # Azul oscuro (1-2 kg)
        (0.208031, 0.718701, 0.472873),  # Verde azulado (2-3 kg)
        (0.369214, 0.788888, 0.382914),  # Verde claro (3-4 kg)
        (0.631373, 0.843137, 0.415686),  # Verde amarillento (4-5 kg)
        (0.993248, 0.906157, 0.143936),  # Amarillo (5-6 kg)
        (0.988235, 0.705882, 0.235294),  # Amarillo naranja (6-7 kg)
        (0.988235, 0.552941, 0.235294),  # Naranja (7-8 kg)
        (0.988235, 0.337255, 0.178431),  # Naranja rojizo (8-9 kg)
        (0.988235, 0.121569, 0.121569),  # Rojo (9-10 kg)
        (0.5, 0.0, 0.0)                  # Rojo oscuro para >10 kg
    ]
    
    # Encontrar el rango correspondiente al peso
    for i, (min_weight, max_weight) in enumerate(weight_ranges):
        if min_weight <= weight < max_weight:
            return colors[i]
    
    # Si el peso es mayor a 10 kg, usar rojo oscuro
    return colors[-1]

def visualize_pallets(pallets: List[Pallet], rotation_angle: float = 45) -> plt.Figure:
    """
    Visualiza los pallets en 3D usando matplotlib.
    Cada pallet se muestra en una visualización completamente separada.
    
    Returns:
        plt.Figure: La figura de matplotlib con la visualización
    """
    if not pallets:
        # Si no hay pallets, crear una figura vacía
        fig = plt.figure(figsize=(12, 8))
        ax = fig.add_subplot(111, projection='3d')
        ax.text(0.5, 0.5, 0.5, 'No hay pallets para mostrar', 
                ha='center', va='center', transform=ax.transAxes, fontsize=14)
        return fig
    
    # Filtrar pallets regulares (excluir el pallet de desechos)
    regular_pallets = [p for p in pallets if not p.is_waste_pallet]
    
    # Calcular el número de filas y columnas para los subplots
    num_pallets = len(regular_pallets)
    if num_pallets == 1:
        cols = 1
        rows = 1
    elif num_pallets == 2:
        cols = 2
        rows = 1
    else:
        cols = 2
        rows = (num_pallets + 1) // 2  # Redondear hacia arriba
    
    # Crear la figura con subplots
    fig = plt.figure(figsize=(6 * cols, 5 * rows))
    
    # Crear un subplot para cada pallet
    for i, pallet in enumerate(regular_pallets):
        # Crear subplot para este pallet
        ax = fig.add_subplot(rows, cols, i + 1, projection='3d')
        
        # Dibujar el pallet (base)
        ax.bar3d(0, 0, 0, 
                pallet.max_width, pallet.max_length, 0.1,
                color='gray', alpha=0.3)
        
        # Dibujar cada caja en el pallet
        for box in pallet.boxes:
            color = get_box_color(box.weight)
            # Verificar que la posición es válida
            if (hasattr(box, 'position') and box.position and 
                len(box.position) >= 3 and 
                all(isinstance(coord, (int, float)) for coord in box.position)):
                ax.bar3d(box.position[0], box.position[1], box.position[2],
                        box.get_effective_width(), box.get_effective_length(), box.get_effective_height(),
                        color=color, alpha=0.8)
            else:
                print(f"⚠️ Caja {box.id} tiene posición inválida: {box.position}")
        
        # Configurar la vista para este subplot
        ax.view_init(elev=20, azim=rotation_angle)
        ax.set_xlabel('Ancho (cm)')
        ax.set_ylabel('Largo (cm)')
        ax.set_zlabel('Alto (cm)')
        
        # Añadir título del pallet
        ax.set_title(f'Pallet {i+1} - {len(pallet.boxes)} cajas, {pallet.current_weight:.1f} kg', 
                    fontsize=12, fontweight='bold', pad=20)
        
        # Ajustar límites para este pallet específico
        ax.set_xlim(0, pallet.max_width)
        ax.set_ylim(0, pallet.max_length)
        ax.set_zlim(0, pallet.max_height)
    
    # Si hay un número impar de pallets, ocultar el último subplot vacío
    if num_pallets % 2 == 1 and num_pallets > 1:
        ax = fig.add_subplot(rows, cols, num_pallets + 1, projection='3d')
        ax.set_visible(False)
    
    # Crear la barra de colores personalizada (solo una vez)
    from matplotlib.colors import ListedColormap
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import BoundaryNorm
    
    # Definir los colores y los límites de los rangos (0-10 kg)
    colors = [
        (0.267004, 0.004874, 0.329415),  # Morado muy oscuro (0-1 kg)
        (0.190631, 0.407061, 0.556089),  # Azul oscuro (1-2 kg)
        (0.208031, 0.718701, 0.472873),  # Verde azulado (2-3 kg)
        (0.369214, 0.788888, 0.382914),  # Verde claro (3-4 kg)
        (0.631373, 0.843137, 0.415686),  # Verde amarillento (4-5 kg)
        (0.993248, 0.906157, 0.143936),  # Amarillo (5-6 kg)
        (0.988235, 0.705882, 0.235294),  # Amarillo naranja (6-7 kg)
        (0.988235, 0.552941, 0.235294),  # Naranja (7-8 kg)
        (0.988235, 0.337255, 0.178431),  # Naranja rojizo (8-9 kg)
        (0.988235, 0.121569, 0.121569),  # Rojo (9-10 kg)
        (0.5, 0.0, 0.0)                  # Rojo oscuro (>10 kg)
    ]
    
    # Definir los límites de los rangos (0-10 kg)
    bounds = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    
    # Crear el mapa de colores personalizado
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(bounds, cmap.N)
    
    # Crear el mapeador de colores
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    
    # Añadir la barra de colores (solo en el primer subplot)
    if num_pallets > 0:
        cbar = plt.colorbar(sm, ax=fig.axes[0], orientation='vertical', pad=0.1)
        cbar.set_label('Peso (kg)')
        
        # Establecer los ticks y etiquetas de la barra de colores (0-10 kg)
        cbar.set_ticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5])
        cbar.set_ticklabels(['0-1', '1-2', '2-3', '3-4', '4-5', '5-6', '6-7', '7-8', '8-9', '9-10', '>10'])
    
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