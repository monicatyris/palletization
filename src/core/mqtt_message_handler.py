import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from .box import Box
from .mqtt_messages import MQTTMessageGenerator


class MQTTMessageHandler:
    """Manejador de mensajes MQTT entrantes (lector de barras, robot)."""
    
    def __init__(self):
        self.message_generator = MQTTMessageGenerator()
    
    def _get_timestamp(self) -> str:
        """Genera timestamp en formato ISO 8601."""
        return datetime.utcnow().isoformat() + "Z"
    
    def handle_barcode_message(self, message: Dict[str, Any]) -> Optional[Box]:
        """
        Procesa mensaje del lector de barras y crea objeto Box.
        
        Args:
            message: Mensaje JSON del lector de barras
            
        Returns:
            Objeto Box si es válido, None si hay error
        """
        try:
            # Validar formato del mensaje
            if not self._validate_barcode_message(message):
                print(f"❌ Mensaje de lector de barras inválido: {message}")
                return None
            
            package_data = message.get("package_data", {})
            package_id = str(package_data.get("package_id", ""))
            barcode = package_data.get("barcode", "")
            
            print(f"📱 [MQTT] Mensaje recibido del lector de barras:")
            print(f"   Scanner ID: {message.get('scanner_id', 'N/A')}")
            print(f"   Package ID: {package_id}")
            print(f"   Barcode: {barcode}")
            print(f"   Timestamp: {message.get('timestamp', 'N/A')}")
            
            # Crear Box básico (las dimensiones se obtendrán de la base de datos)
            box = Box(
                id=package_id,
                width=0.0,  # Se actualizará desde la base de datos
                length=0.0,  # Se actualizará desde la base de datos
                height=0.0,  # Se actualizará desde la base de datos
                weight=0.0   # Se actualizará desde la base de datos
            )
            
            # Añadir metadatos del escaneo
            box.barcode = barcode
            box.scanner_id = message.get("scanner_id", "")
            box.scan_timestamp = message.get("timestamp", self._get_timestamp())
            
            return box
            
        except Exception as e:
            print(f"❌ Error procesando mensaje de lector de barras: {e}")
            return None
    
    def handle_robot_confirmation(self, message: Dict[str, Any]) -> bool:
        """
        Procesa mensaje de confirmación del robot.
        
        Args:
            message: Mensaje JSON de confirmación del robot
            
        Returns:
            True si la confirmación es exitosa, False si hay error
        """
        try:
            # Validar formato del mensaje
            if not self._validate_robot_confirmation(message):
                print(f"❌ Mensaje de confirmación del robot inválido: {message}")
                return False
            
            package_id = message.get("package_id", "")
            status = message.get("status", "")
            pallet_id = message.get("pallet_id", "")
            
            print(f"🤖 [MQTT] Confirmación recibida del robot:")
            print(f"   Package ID: {package_id}")
            print(f"   Pallet ID: {pallet_id}")
            print(f"   Status: {status}")
            print(f"   Timestamp: {message.get('timestamp', 'N/A')}")
            
            if status == "SUCCESS":
                print(f"✅ Colocación exitosa de caja {package_id} en pallet {pallet_id}")
                return True
            else:
                print(f"❌ Error en colocación de caja {package_id}: {status}")
                return False
                
        except Exception as e:
            print(f"❌ Error procesando confirmación del robot: {e}")
            return False
    
    def _validate_barcode_message(self, message: Dict[str, Any]) -> bool:
        """Valida formato del mensaje del lector de barras."""
        required_fields = ["message_type", "timestamp", "scanner_id", "package_data"]
        
        if not all(field in message for field in required_fields):
            return False
        
        if message.get("message_type") != "BOX_SCANNED":
            return False
        
        package_data = message.get("package_data", {})
        if not isinstance(package_data, dict):
            return False
        
        required_package_fields = ["package_id", "barcode"]
        if not all(field in package_data for field in required_package_fields):
            return False
        
        return True
    
    def _validate_robot_confirmation(self, message: Dict[str, Any]) -> bool:
        """Valida formato del mensaje de confirmación del robot."""
        required_fields = ["message_type", "timestamp", "instruction_type", "pallet_id", "package_id", "status"]
        
        if not all(field in message for field in required_fields):
            return False
        
        if message.get("message_type") != "PLACEMENT_CONFIRMED":
            return False
        
        if message.get("instruction_type") != "PLACE_PACKAGE":
            return False
        
        return True
    
    def create_barcode_message(self, package_id: str, barcode: str, scanner_id: str = "SCANNER_001") -> Dict[str, Any]:
        """
        Crea mensaje simulado del lector de barras (para testing).
        
        Args:
            package_id: ID de la caja
            barcode: Código de barras
            scanner_id: ID del escáner
            
        Returns:
            Mensaje JSON simulado
        """
        return {
            "message_type": "BOX_SCANNED",
            "timestamp": self._get_timestamp(),
            "scanner_id": scanner_id,
            "package_data": {
                "package_id": package_id,
                "barcode": barcode
            }
        }
    
    def create_robot_confirmation(self, package_id: str, pallet_id: str, status: str = "SUCCESS") -> Dict[str, Any]:
        """
        Crea mensaje simulado de confirmación del robot (para testing).
        
        Args:
            package_id: ID de la caja
            pallet_id: ID del pallet
            status: Estado de la colocación
            
        Returns:
            Mensaje JSON simulado
        """
        return {
            "message_type": "PLACEMENT_CONFIRMED",
            "timestamp": self._get_timestamp(),
            "instruction_type": "PLACE_PACKAGE",
            "pallet_id": pallet_id,
            "package_id": package_id,
            "status": status
        }
