import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import deque
from .box import Box
from .box_database import BoxDatabase
from .mqtt_message_handler import MQTTMessageHandler


class SyncBoxQueue:
    """Sistema de cola síncrono para manejo de cajas escaneadas (compatible con Streamlit)."""
    
    def __init__(self, database: BoxDatabase):
        self.database = database
        self.message_handler = MQTTMessageHandler()
        self.queue = deque()  # Cola FIFO de cajas
        self.processing_queue = deque()  # Cola de cajas en procesamiento
        self.completed_boxes = []  # Lista de cajas completadas
        self.lock = threading.Lock()  # Lock síncrono para operaciones thread-safe
        
        # Estadísticas
        self.stats = {
            "total_scanned": 0,
            "total_validated": 0,
            "total_queued": 0,
            "total_processed": 0,
            "total_completed": 0,
            "total_failed": 0
        }
    
    def add_scanned_box(self, message: Dict[str, Any]) -> bool:
        """
        Procesa mensaje del lector de barras y añade caja a la cola.
        
        Args:
            message: Mensaje JSON del lector de barras
            
        Returns:
            True si se añadió exitosamente, False si hay error
        """
        try:
            with self.lock:
                self.stats["total_scanned"] += 1
                
                # Procesar mensaje del lector de barras
                box = self.message_handler.handle_barcode_message(message)
                if not box:
                    print(f"❌ No se pudo procesar mensaje del lector de barras")
                    return False
                
                # Validar que la caja existe en la base de datos
                if not self.database.validate_box_exists(box.id):
                    print(f"❌ Caja {box.id} no encontrada en la base de datos")
                    return False
                
                self.stats["total_validated"] += 1
                
                # Obtener detalles completos de la caja
                complete_box = self.database.get_box_details(box.id)
                if not complete_box:
                    print(f"❌ No se pudieron obtener detalles de la caja {box.id}")
                    return False
                
                # Preservar metadatos del escaneo
                complete_box.barcode = getattr(box, 'barcode', '')
                complete_box.scanner_id = getattr(box, 'scanner_id', '')
                complete_box.scan_timestamp = getattr(box, 'scan_timestamp', datetime.utcnow().isoformat() + "Z")
                complete_box.queue_timestamp = datetime.utcnow().isoformat() + "Z"
                
                # Añadir a la cola
                self.queue.append(complete_box)
                self.stats["total_queued"] += 1
                
                print(f"✅ Caja {complete_box.id} añadida a la cola")
                print(f"📊 Estado de la cola: {len(self.queue)} cajas pendientes")
                
                return True
                
        except Exception as e:
            print(f"❌ Error añadiendo caja escaneada: {e}")
            return False
    
    def get_next_box(self) -> Optional[Box]:
        """
        Obtiene la siguiente caja a procesar de la cola.
        
        Returns:
            Objeto Box si hay cajas disponibles, None si la cola está vacía
        """
        try:
            with self.lock:
                if not self.queue:
                    print("📭 Cola vacía - no hay cajas para procesar")
                    return None
                
                # Mover caja de la cola principal a la cola de procesamiento
                box = self.queue.popleft()
                self.processing_queue.append(box)
                self.stats["total_processed"] += 1
                
                print(f"📦 Procesando caja {box.id} (peso: {box.weight} kg)")
                print(f"📊 Estado: {len(self.queue)} pendientes, {len(self.processing_queue)} procesando")
                
                return box
                
        except Exception as e:
            print(f"❌ Error obteniendo siguiente caja: {e}")
            return None
    
    def confirm_placement(self, package_id: str) -> bool:
        """
        Confirma que una caja fue colocada exitosamente.
        
        Args:
            package_id: ID de la caja colocada
            
        Returns:
            True si se confirmó exitosamente, False si hay error
        """
        try:
            with self.lock:
                # Buscar la caja en la cola de procesamiento
                box_found = None
                for i, box in enumerate(self.processing_queue):
                    if box.id == package_id:
                        box_found = box
                        # Remover usando del y slice
                        del self.processing_queue[i]
                        break
                
                if not box_found:
                    print(f"❌ Caja {package_id} no encontrada en la cola de procesamiento")
                    return False
                
                # Marcar como completada
                box_found.completion_timestamp = datetime.utcnow().isoformat() + "Z"
                self.completed_boxes.append(box_found)
                self.stats["total_completed"] += 1
                
                print(f"✅ Caja {package_id} confirmada como colocada exitosamente")
                print(f"📊 Estado: {len(self.queue)} pendientes, {len(self.processing_queue)} procesando, {len(self.completed_boxes)} completadas")
                
                return True
                
        except Exception as e:
            print(f"❌ Error confirmando colocación de caja {package_id}: {e}")
            return False
    
    def handle_robot_confirmation(self, message: Dict[str, Any]) -> bool:
        """
        Procesa mensaje de confirmación del robot.
        
        Args:
            message: Mensaje JSON de confirmación del robot
            
        Returns:
            True si se procesó exitosamente, False si hay error
        """
        try:
            # Procesar mensaje de confirmación
            success = self.message_handler.handle_robot_confirmation(message)
            
            if success:
                package_id = str(message.get("package_id", ""))
                return self.confirm_placement(package_id)
            else:
                # Manejar fallo en la colocación
                package_id = str(message.get("package_id", ""))
                self._handle_placement_failure(package_id)
                return False
                
        except Exception as e:
            print(f"❌ Error procesando confirmación del robot: {e}")
            return False
    
    def _handle_placement_failure(self, package_id: str):
        """Maneja fallo en la colocación de una caja."""
        try:
            with self.lock:
                # Buscar la caja en la cola de procesamiento
                box_found = None
                for i, box in enumerate(self.processing_queue):
                    if box.id == package_id:
                        box_found = box
                        # Remover usando del y slice
                        del self.processing_queue[i]
                        break
                
                if box_found:
                    # Marcar como fallida y volver a la cola (opcional)
                    box_found.failure_timestamp = datetime.utcnow().isoformat() + "Z"
                    self.stats["total_failed"] += 1
                    print(f"❌ Caja {package_id} falló en la colocación - marcada como fallida")
                else:
                    print(f"❌ Caja {package_id} no encontrada para marcar como fallida")
                    
        except Exception as e:
            print(f"❌ Error manejando fallo de colocación: {e}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado actual de la cola.
        
        Returns:
            Diccionario con el estado de la cola
        """
        with self.lock:
            return {
                "queue_length": len(self.queue),
                "processing_length": len(self.processing_queue),
                "completed_count": len(self.completed_boxes),
                "stats": self.stats.copy(),
                "next_box_id": self.queue[0].id if self.queue else None,
                "processing_box_ids": [box.id for box in self.processing_queue]
            }
    
    def get_processing_box_ids(self) -> List[str]:
        """Obtiene lista de IDs de cajas en procesamiento."""
        with self.lock:
            return [box.id for box in self.processing_queue]
    
    def get_completed_boxes(self) -> List[Box]:
        """Obtiene lista de cajas completadas."""
        with self.lock:
            return self.completed_boxes.copy()
    
    def clear_completed_boxes(self):
        """Limpia la lista de cajas completadas."""
        with self.lock:
            self.completed_boxes.clear()
            print("🧹 Lista de cajas completadas limpiada")
    
    def get_queue_summary(self) -> str:
        """
        Obtiene resumen textual del estado de la cola.
        
        Returns:
            String con resumen del estado
        """
        status = self.get_queue_status()
        return f"""
📊 Estado de la Cola de Cajas:
   📦 Pendientes: {status['queue_length']}
   🔄 Procesando: {status['processing_length']}
   ✅ Completadas: {status['completed_count']}
   📈 Estadísticas: {status['stats']['total_scanned']} escaneadas, {status['stats']['total_queued']} encoladas, {status['stats']['total_completed']} completadas
        """
