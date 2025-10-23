import asyncio
import time
import random
from typing import List, Dict, Any
from .box_database import BoxDatabase
from .sync_box_queue import SyncBoxQueue
from .mqtt_message_handler import MQTTMessageHandler


class QueueSimulator:
    """Simulador del sistema de cola de cajas para testing."""
    
    def __init__(self, csv_file_path: str):
        self.database = BoxDatabase(csv_file_path)
        self.queue = SyncBoxQueue(self.database)
        self.message_handler = MQTTMessageHandler()
        self.simulation_running = False
        
    def simulate_barcode_scanner(self, box_ids: List[str] = None, delay: float = 1.0):
        """
        Simula el lector de barras escaneando cajas.
        
        Args:
            box_ids: Lista de IDs de cajas a escanear (si None, usa todas las de la BD)
            delay: Delay entre escaneos en segundos
        """
        if not box_ids:
            box_ids = self.database.get_all_box_ids()
        
        print(f"📱 Iniciando simulación del lector de barras...")
        print(f"📦 Cajas a escanear: {len(box_ids)}")
        print(f"⏱️ Delay entre escaneos: {delay}s")
        print("=" * 60)
        
        for i, box_id in enumerate(box_ids):
            if not self.simulation_running:
                print("⏹️ Simulación detenida por el usuario")
                break
            
            # Crear mensaje simulado del lector de barras
            barcode = f"BC{box_id.zfill(6)}"  # Simular código de barras
            message = self.message_handler.create_barcode_message(
                package_id=box_id,
                barcode=barcode,
                scanner_id=f"SCANNER_{i % 3 + 1:03d}"  # Rotar entre 3 escáneres
            )
            
            # Procesar mensaje
            success = self.queue.add_scanned_box(message)
            
            if success:
                print(f"✅ Escaneo {i+1}/{len(box_ids)}: Caja {box_id} añadida a la cola")
            else:
                print(f"❌ Escaneo {i+1}/{len(box_ids)}: Error con caja {box_id}")
            
            # Mostrar estado de la cola cada 5 cajas
            if (i + 1) % 5 == 0:
                print(self.queue.get_queue_summary())
            
            time.sleep(delay)
        
        print("🏁 Simulación del lector de barras completada")
    
    def simulate_robot_responses(self, delay: float = 2.0):
        """
        Simula las respuestas del robot a los comandos de colocación.
        
        Args:
            delay: Delay entre respuestas en segundos
        """
        print(f"🤖 Iniciando simulación de respuestas del robot...")
        print(f"⏱️ Delay entre respuestas: {delay}s")
        print("=" * 60)
        
        while self.simulation_running:
            # Primero, intentar procesar cajas de la cola
            box = self.queue.get_next_box()
            if box:
                print(f"🔄 Procesando caja {box.id} desde la cola")
                time.sleep(0.5)  # Simular tiempo de procesamiento
            
            # Obtener cajas en procesamiento
            processing_ids = self.queue.get_processing_box_ids()
            
            if not processing_ids:
                print("⏳ No hay cajas en procesamiento, esperando...")
                time.sleep(1.0)
                continue
            
            # Simular respuesta del robot para la primera caja en procesamiento
            box_id = processing_ids[0]
            
            # Simular éxito (95% de probabilidad) o fallo (5% de probabilidad)
            success = random.random() < 0.95
            
            # Crear mensaje de confirmación simulado
            pallet_id = f"P{random.randint(1, 3):03d}"  # Simular pallet aleatorio
            status = "SUCCESS" if success else "FAILED"
            
            message = self.message_handler.create_robot_confirmation(
                package_id=box_id,
                pallet_id=pallet_id,
                status=status
            )
            
            # Procesar confirmación
            if success:
                confirmed = self.queue.handle_robot_confirmation(message)
                if confirmed:
                    print(f"✅ Robot confirmó colocación exitosa de caja {box_id}")
                else:
                    print(f"❌ Error procesando confirmación de caja {box_id}")
            else:
                print(f"❌ Robot reportó fallo en colocación de caja {box_id}")
                self.queue.handle_robot_confirmation(message)
            
            time.sleep(delay)
    
    def start_simulation(self, box_ids: List[str] = None, 
                        scanner_delay: float = 1.0, 
                        robot_delay: float = 2.0):
        """
        Inicia la simulación completa del sistema.
        
        Args:
            box_ids: Lista de IDs de cajas a procesar
            scanner_delay: Delay del lector de barras
            robot_delay: Delay del robot
        """
        print("🚀 Iniciando simulación completa del sistema de cola...")
        print("=" * 60)
        
        self.simulation_running = True
        
        # Iniciar simulación del lector de barras y robot en paralelo
        import threading
        scanner_thread = threading.Thread(
            target=self.simulate_barcode_scanner,
            args=(box_ids, scanner_delay)
        )
        robot_thread = threading.Thread(
            target=self.simulate_robot_responses,
            args=(robot_delay,)
        )
        scanner_thread.daemon = True
        robot_thread.daemon = True
        scanner_thread.start()
        robot_thread.start()
        
        # Monitorear el progreso
        try:
            # Esperar a que el escáner termine
            scanner_thread.join()
            
            # Luego esperar a que el robot termine de procesar todas las cajas
            while self.simulation_running:
                status = self.queue.get_queue_status()
                
                if status['queue_length'] == 0 and status['processing_length'] == 0:
                    print("🎉 Todas las cajas han sido procesadas!")
                    break
                
                time.sleep(2)  # Mostrar estado cada 2 segundos
                
        except KeyboardInterrupt:
            print("\n⏹️ Simulación detenida por el usuario")
        
        finally:
            self.simulation_running = False
            self._show_final_stats()
    
    def stop_simulation(self):
        """Detiene la simulación."""
        self.simulation_running = False
        print("⏹️ Simulación detenida")
    
    def _show_final_stats(self):
        """Muestra estadísticas finales de la simulación."""
        print("\n" + "=" * 60)
        print("📊 ESTADÍSTICAS FINALES DE LA SIMULACIÓN")
        print("=" * 60)
        
        status = self.queue.get_queue_status()
        stats = status['stats']
        
        print(f"📦 Total escaneadas: {stats['total_scanned']}")
        print(f"✅ Total validadas: {stats['total_validated']}")
        print(f"📋 Total encoladas: {stats['total_queued']}")
        print(f"🔄 Total procesadas: {stats['total_processed']}")
        print(f"✅ Total completadas: {stats['total_completed']}")
        print(f"❌ Total fallidas: {stats['total_failed']}")
        
        print(f"\n📊 Estado final de la cola:")
        print(f"   Pendientes: {status['queue_length']}")
        print(f"   Procesando: {status['processing_length']}")
        print(f"   Completadas: {status['completed_count']}")
        
        # Mostrar cajas completadas
        completed_boxes = self.queue.get_completed_boxes()
        if completed_boxes:
            print(f"\n✅ Cajas completadas exitosamente:")
            for box in completed_boxes[:10]:  # Mostrar solo las primeras 10
                print(f"   - Caja {box.id}: {box.width}x{box.length}x{box.height} cm, {box.weight} kg")
            if len(completed_boxes) > 10:
                print(f"   ... y {len(completed_boxes) - 10} más")
    
    def test_single_box(self, box_id: str):
        """
        Prueba el procesamiento de una sola caja.
        
        Args:
            box_id: ID de la caja a procesar
        """
        print(f"🧪 Probando procesamiento de caja individual: {box_id}")
        print("=" * 60)
        
        # Simular escaneo
        barcode = f"BC{box_id.zfill(6)}"
        message = self.message_handler.create_barcode_message(
            package_id=box_id,
            barcode=barcode
        )
        
        print("1. Simulando escaneo del lector de barras...")
        success = self.queue.add_scanned_box(message)
        print(f"   Resultado: {'✅ Éxito' if success else '❌ Error'}")
        
        if success:
            print("\n2. Obteniendo siguiente caja de la cola...")
            box = self.queue.get_next_box()
            if box:
                print(f"   Caja obtenida: {box.id} ({box.width}x{box.length}x{box.height} cm, {box.weight} kg)")
                
                print("\n3. Simulando confirmación del robot...")
                time.sleep(1)  # Simular tiempo de procesamiento
                
                confirmation = self.message_handler.create_robot_confirmation(
                    package_id=box.id,
                    pallet_id="P001",
                    status="SUCCESS"
                )
                
                confirmed = self.queue.handle_robot_confirmation(confirmation)
                print(f"   Resultado: {'✅ Confirmado' if confirmed else '❌ Error'}")
            else:
                print("   ❌ No se pudo obtener caja de la cola")
        
        print("\n📊 Estado final de la cola:")
        print(self.queue.get_queue_summary())
