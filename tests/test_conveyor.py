import pytest
import os
import tempfile
import pandas as pd
from src.simulation.conveyor import CintaTransportadora

def create_temp_csv():
    """Crea un archivo CSV temporal con datos de prueba."""
    data = {
        'id': [1, 2, 3],
        'width': [50, 30, 20],
        'length': [50, 30, 20],
        'height': [50, 30, 20],
        'weight': [100, 50, 30]
    }
    df = pd.DataFrame(data)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
    df.to_csv(temp_file.name, index=False)
    return temp_file.name

def test_conveyor_initialization():
    """Test para verificar la inicialización correcta de la cinta transportadora."""
    temp_file = create_temp_csv()
    try:
        conveyor = CintaTransportadora(temp_file)
        assert conveyor.archivo_cajas == temp_file
        assert conveyor.intervalo_segundos == 2.0
        assert len(conveyor.cajas) == 0
        assert len(conveyor.pallets) == 0
        assert conveyor.max_width == 100
        assert conveyor.max_length == 100
        assert conveyor.max_height == 150
        assert conveyor.max_weight == 1000
    finally:
        os.unlink(temp_file)

def test_conveyor_load_boxes():
    """Test para verificar la carga correcta de cajas desde el archivo CSV."""
    temp_file = create_temp_csv()
    try:
        conveyor = CintaTransportadora(temp_file, intervalo_segundos=0)
        conveyor.cargar_cajas()
        
        assert len(conveyor.cajas) == 3
        assert len(conveyor.pallets) > 0
        
        # Verificar que las cajas se cargaron correctamente
        box_ids = [box.id for box in conveyor.cajas]
        assert box_ids == [1, 2, 3]
        
        # Verificar que las cajas se asignaron a pallets
        total_boxes_in_pallets = sum(len(pallet.boxes) for pallet in conveyor.pallets)
        assert total_boxes_in_pallets == 3
    finally:
        os.unlink(temp_file)

def test_conveyor_invalid_file():
    """Test para verificar el manejo de archivos inválidos."""
    with pytest.raises(FileNotFoundError):
        CintaTransportadora("archivo_inexistente.csv")

def test_conveyor_invalid_csv_format():
    """Test para verificar el manejo de archivos CSV con formato inválido."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.csv')
    try:
        with open(temp_file.name, 'w') as f:
            f.write("invalid,data\n1,2,3")
        
        conveyor = CintaTransportadora(temp_file.name)
        with pytest.raises(Exception):
            conveyor.cargar_cajas()
    finally:
        os.unlink(temp_file.name)

def test_conveyor_box_placement():
    """Test para verificar la colocación correcta de cajas en los pallets."""
    temp_file = create_temp_csv()
    try:
        conveyor = CintaTransportadora(temp_file, intervalo_segundos=0)
        conveyor.cargar_cajas()
        
        # Verificar que las cajas están colocadas correctamente
        for pallet in conveyor.pallets:
            for box in pallet.boxes:
                # Verificar que la posición está dentro de los límites del pallet
                x, y, z = box.position
                assert 0 <= x <= pallet.max_width - box.width
                assert 0 <= y <= pallet.max_length - box.length
                assert 0 <= z <= pallet.max_height - box.height
                
                # Verificar que el peso no excede el límite
                assert pallet.current_weight <= pallet.max_weight
    finally:
        os.unlink(temp_file) 