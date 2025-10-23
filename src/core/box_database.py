import pandas as pd
from typing import Dict, List, Any, Optional
from .box import Box


class BoxDatabase:
    """Base de datos de cajas basada en archivos CSV."""
    
    def __init__(self, csv_file_path: str = None):
        self.csv_file_path = csv_file_path
        self.database = None
        self.box_cache = {}  # Cache para búsquedas rápidas
        
        if csv_file_path:
            self.load_database(csv_file_path)
    
    def load_database(self, csv_file_path: str) -> bool:
        """
        Carga la base de datos desde un archivo CSV.
        
        Args:
            csv_file_path: Ruta al archivo CSV
            
        Returns:
            True si se cargó exitosamente, False si hay error
        """
        try:
            print(f"📚 Cargando base de datos desde: {csv_file_path}")
            self.database = pd.read_csv(csv_file_path)
            self.csv_file_path = csv_file_path
            
            # Crear cache para búsquedas rápidas
            self.box_cache = {}
            for _, row in self.database.iterrows():
                box_id = str(row['id'])
                self.box_cache[box_id] = {
                    'width': float(row['width']),
                    'length': float(row['length']),
                    'height': float(row['height']),
                    'weight': float(row['weight'])
                }
            
            print(f"✅ Base de datos cargada exitosamente: {len(self.database)} cajas")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando base de datos: {e}")
            return False
    
    def validate_box_exists(self, package_id: str) -> bool:
        """
        Valida si una caja existe en la base de datos.
        
        Args:
            package_id: ID de la caja a validar
            
        Returns:
            True si existe, False si no existe
        """
        if not self.database is not None:
            print("❌ Base de datos no cargada")
            return False
        
        exists = package_id in self.box_cache
        print(f"🔍 Validando caja {package_id}: {'✅ Existe' if exists else '❌ No existe'}")
        return exists
    
    def get_box_details(self, package_id: str) -> Optional[Box]:
        """
        Obtiene los detalles completos de una caja desde la base de datos.
        
        Args:
            package_id: ID de la caja
            
        Returns:
            Objeto Box con todos los detalles, None si no existe
        """
        if not self.validate_box_exists(package_id):
            return None
        
        try:
            box_data = self.box_cache[package_id]
            
            # Crear objeto Box con datos de la base de datos
            box = Box(
                id=package_id,
                width=box_data['width'],
                length=box_data['length'],
                height=box_data['height'],
                weight=box_data['weight']
            )
            
            print(f"📦 Datos de caja {package_id} obtenidos:")
            print(f"   Dimensiones: {box.width}x{box.length}x{box.height} cm")
            print(f"   Peso: {box.weight} kg")
            print(f"   Volumen: {box.volume():.1f} cm³")
            
            return box
            
        except Exception as e:
            print(f"❌ Error obteniendo detalles de caja {package_id}: {e}")
            return None
    
    def get_all_box_ids(self) -> List[str]:
        """
        Obtiene lista de todos los IDs de cajas en la base de datos.
        
        Returns:
            Lista de IDs de cajas
        """
        if not self.database is not None:
            return []
        
        return list(self.box_cache.keys())
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la base de datos.
        
        Returns:
            Diccionario con estadísticas
        """
        if not self.database is not None:
            return {"error": "Base de datos no cargada"}
        
        stats = {
            "total_boxes": len(self.database),
            "csv_file": self.csv_file_path,
            "dimensions": {
                "width_range": [self.database['width'].min(), self.database['width'].max()],
                "length_range": [self.database['length'].min(), self.database['length'].max()],
                "height_range": [self.database['height'].min(), self.database['height'].max()],
                "weight_range": [self.database['weight'].min(), self.database['weight'].max()]
            }
        }
        
        return stats
    
    def search_boxes_by_criteria(self, 
                                min_width: float = None, 
                                max_width: float = None,
                                min_length: float = None, 
                                max_length: float = None,
                                min_height: float = None, 
                                max_height: float = None,
                                min_weight: float = None, 
                                max_weight: float = None) -> List[str]:
        """
        Busca cajas que cumplan ciertos criterios.
        
        Args:
            min_width, max_width: Rango de ancho
            min_length, max_length: Rango de largo
            min_height, max_height: Rango de alto
            min_weight, max_weight: Rango de peso
            
        Returns:
            Lista de IDs de cajas que cumplen los criterios
        """
        if not self.database is not None:
            return []
        
        # Crear máscara de filtrado
        mask = pd.Series([True] * len(self.database))
        
        if min_width is not None:
            mask &= (self.database['width'] >= min_width)
        if max_width is not None:
            mask &= (self.database['width'] <= max_width)
        if min_length is not None:
            mask &= (self.database['length'] >= min_length)
        if max_length is not None:
            mask &= (self.database['length'] <= max_length)
        if min_height is not None:
            mask &= (self.database['height'] >= min_height)
        if max_height is not None:
            mask &= (self.database['height'] <= max_height)
        if min_weight is not None:
            mask &= (self.database['weight'] >= min_weight)
        if max_weight is not None:
            mask &= (self.database['weight'] <= max_weight)
        
        filtered_boxes = self.database[mask]
        return [str(box_id) for box_id in filtered_boxes['id']]
