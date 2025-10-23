import json
from datetime import datetime
from typing import Dict, List, Any
from .box import Box
from .pallet import Pallet


class MQTTMessageGenerator:
    """Generador de mensajes MQTT para comunicación con el robot en tiempo real."""
    
    def __init__(self):
        self.pallet_counter = 0
    
    def _get_timestamp(self) -> str:
        """Genera timestamp en formato ISO 8601."""
        return datetime.utcnow().isoformat() + "Z"
    
    def _generate_pallet_id(self, pallet_index: int) -> str:
        """Genera ID único del pallet."""
        return f"P{datetime.now().strftime('%Y%m%d')}{pallet_index:03d}"
    
    def _get_pallet_location(self, pallet_index: int) -> str:
        """Determina la ubicación del pallet (A, B, C, etc.)."""
        return chr(65 + pallet_index)  # A=0, B=1, C=2, etc.
    
    def generate_start_pallet_message(self, pallet: Pallet, pallet_index: int) -> Dict[str, Any]:
        """
        Genera mensaje de inicio de pallet (START_PALLET).
        
        Args:
            pallet: Objeto Pallet con la configuración
            pallet_index: Índice del pallet (0, 1, 2, etc.)
        
        Returns:
            Dict con el mensaje JSON formateado
        """
        return {
            "instruction_type": "START_PALLET",
            "timestamp": self._get_timestamp(),
            "pallet_id": self._generate_pallet_id(pallet_index),
            "pallet_loc": self._get_pallet_location(pallet_index),
            "dimensions": {
                "width": pallet.max_width,
                "length": pallet.max_length,
                "height": pallet.max_height
            }
        }
    
    def generate_place_package_message(
        self, 
        box: Box, 
        pallet: Pallet, 
        pallet_index: int,
        algorithm_used: str,
        quality_score: float
    ) -> Dict[str, Any]:
        """
        Genera mensaje de colocación de caja (PLACE_PACKAGE).
        
        Args:
            box: Objeto Box que se está colocando
            pallet: Objeto Pallet donde se coloca la caja
            pallet_index: Índice del pallet
            algorithm_used: Nombre del algoritmo utilizado
            quality_score: Puntuación de calidad del pallet
        
        Returns:
            Dict con el mensaje JSON formateado
        """
        return {
            "instruction_type": "PLACE_PACKAGE",
            "timestamp": self._get_timestamp(),
            "pallet_id": self._generate_pallet_id(pallet_index),
            "package": {
                "package_id": int(box.id) if box.id.isdigit() else hash(box.id) % 1000000,
                "dimensions": {
                    "width": box.get_effective_width(),
                    "length": box.get_effective_length(),
                    "height": box.get_effective_height()
                },
                "position": {
                    "x": box.position[0] if hasattr(box, 'position') and box.position else 0.0,
                    "y": box.position[1] if hasattr(box, 'position') and box.position else 0.0,
                    "z": box.position[2] if hasattr(box, 'position') and box.position else 0.0
                },
                "rotation": 0 if box.orientation.name == "NORMAL" else 90,  # 0° para NORMAL, 90° para ROTATED_90
                "weight": box.weight
            },
            "placement_status": "ok",
            "metadata": {
                "algorithm_used": algorithm_used.lower().replace(" ", "_"),
                "parameters": {},  # Se puede expandir con parámetros específicos del algoritmo
                "quality_score": quality_score,
                "total_weight": pallet.current_weight
            }
        }
    
    def generate_complete_pallet_message(
        self, 
        pallet: Pallet, 
        pallet_index: int,
        quality_score: float,
        used_volume: float
    ) -> Dict[str, Any]:
        """
        Genera mensaje de completado de pallet (COMPLETE_PALLET).
        
        Args:
            pallet: Objeto Pallet completado
            pallet_index: Índice del pallet
            quality_score: Puntuación de calidad final del pallet
            used_volume: Volumen utilizado del pallet (0.0 a 1.0)
        
        Returns:
            Dict con el mensaje JSON formateado
        """
        # Generar lista de IDs de paquetes
        package_id_list = []
        for box in pallet.boxes:
            if box.id.isdigit():
                package_id_list.append(int(box.id))
            else:
                package_id_list.append(hash(box.id) % 1000000)
        
        return {
            "instruction_type": "COMPLETE_PALLET",
            "timestamp": self._get_timestamp(),
            "pallet_id": self._generate_pallet_id(pallet_index),
            "package_id_list": package_id_list,
            "replace_pallet": True,  # Por defecto, se reemplaza el pallet
            "manual_interruption": False,  # Por defecto, no hay interrupción manual
            "metadata": {
                "total_boxes": len(pallet.boxes),
                "total_weight": pallet.current_weight,
                "quality_score": quality_score,
                "used_volume": used_volume
            }
        }
    
    def generate_waste_pallet_message(
        self, 
        waste_pallet: Pallet,
        pallet_index: int
    ) -> Dict[str, Any]:
        """
        Genera mensaje especial para el pallet de desechos.
        
        Args:
            waste_pallet: Objeto Pallet de desechos
            pallet_index: Índice del pallet de desechos
        
        Returns:
            Dict con el mensaje JSON formateado
        """
        return {
            "instruction_type": "WASTE_PALLET",
            "timestamp": self._get_timestamp(),
            "pallet_id": self._generate_pallet_id(pallet_index),
            "pallet_loc": "W",  # W para Waste/Desecho
            "waste_info": {
                "total_packages": len(waste_pallet.boxes),
                "total_weight": waste_pallet.current_weight,
                "waste_reasons": self._get_waste_reasons(waste_pallet)
            }
        }
    
    def _get_waste_reasons(self, waste_pallet: Pallet) -> List[Dict[str, Any]]:
        """
        Obtiene las razones por las que cada caja fue enviada al pallet de desechos.
        
        Args:
            waste_pallet: Objeto Pallet de desechos
        
        Returns:
            Lista de diccionarios con información de cada caja en desechos
        """
        waste_reasons = []
        for box in waste_pallet.boxes:
            waste_reasons.append({
                "package_id": int(box.id) if box.id.isdigit() else hash(box.id) % 1000000,
                "dimensions": {
                    "width": box.get_effective_width(),
                    "length": box.get_effective_length(),
                    "height": box.get_effective_height()
                },
                "weight": box.weight,
                "reason": "dimensions_exceed_pallet"  # Razón por defecto
            })
        return waste_reasons
    
    def send_message(self, message: Dict[str, Any]) -> str:
        """
        Convierte el mensaje a formato JSON string.
        
        Args:
            message: Diccionario con el mensaje
        
        Returns:
            String JSON del mensaje
        """
        return json.dumps(message, indent=2, ensure_ascii=False)
    
    def send_to_robot(self, message: Dict[str, Any]) -> None:
        """
        Envía mensaje al robot (por ahora solo imprime en consola).
        En el futuro se conectará al broker MQTT real.
        
        Args:
            message: Diccionario con el mensaje a enviar
        """
        json_message = self.send_message(message)
        print(f"\n📡 [MQTT] Enviando mensaje al robot:")
        print(f"🔧 Tipo: {message['instruction_type']}")
        print(f"📦 Pallet ID: {message.get('pallet_id', 'N/A')}")
        print(f"⏰ Timestamp: {message.get('timestamp', 'N/A')}")
        
        if message['instruction_type'] == 'PLACE_PACKAGE':
            package = message.get('package', {})
            print(f"📦 Caja ID: {package.get('package_id', 'N/A')}")
            print(f"📍 Posición: ({package.get('position', {}).get('x', 0)}, {package.get('position', {}).get('y', 0)}, {package.get('position', {}).get('z', 0)})")
            print(f"🔄 Rotación: {package.get('rotation', 0)}°")
            print(f"📏 Dimensiones: {package.get('dimensions', {}).get('width', 0)}x{package.get('dimensions', {}).get('length', 0)}x{package.get('dimensions', {}).get('height', 0)}")
            print(f"⚖️ Peso: {package.get('weight', 0)} kg")
        elif message['instruction_type'] == 'COMPLETE_PALLET':
            metadata = message.get('metadata', {})
            print(f"📊 Total cajas: {metadata.get('total_boxes', 0)}")
            print(f"⚖️ Peso total: {metadata.get('total_weight', 0)} kg")
            print(f"🎯 Calidad: {metadata.get('quality_score', 0)}")
        
        print(f"📄 JSON completo:")
        print(json_message)
        print("=" * 80)


# Función de conveniencia para uso directo
def create_mqtt_messages(
    pallets: List[Pallet],
    algorithm_used: str,
    quality_scores: List[float] = None
) -> List[Dict[str, Any]]:
    """
    Crea todos los mensajes MQTT para una simulación completa.
    
    Args:
        pallets: Lista de pallets de la simulación
        algorithm_used: Nombre del algoritmo utilizado
        quality_scores: Lista de puntuaciones de calidad por pallet
    
    Returns:
        Lista de mensajes MQTT
    """
    generator = MQTTMessageGenerator()
    messages = []
    
    # Filtrar pallets regulares (excluir pallet de desechos)
    regular_pallets = [p for p in pallets if not p.is_waste_pallet]
    waste_pallet = next((p for p in pallets if p.is_waste_pallet), None)
    
    # Generar mensajes para cada pallet regular
    for i, pallet in enumerate(regular_pallets):
        # Mensaje de inicio de pallet
        start_msg = generator.generate_start_pallet_message(pallet, i)
        messages.append(start_msg)
        
        # Mensajes de colocación de cajas
        for box in pallet.boxes:
            quality_score = quality_scores[i] if quality_scores and i < len(quality_scores) else 0.5
            place_msg = generator.generate_place_package_message(
                box, pallet, i, algorithm_used, quality_score
            )
            messages.append(place_msg)
        
        # Mensaje de completado de pallet
        quality_score = quality_scores[i] if quality_scores and i < len(quality_scores) else 0.5
        used_volume = sum(box.volume() for box in pallet.boxes) / pallet.volume()
        complete_msg = generator.generate_complete_pallet_message(
            pallet, i, quality_score, used_volume
        )
        messages.append(complete_msg)
    
    # Generar mensaje para pallet de desechos si existe
    if waste_pallet and waste_pallet.boxes:
        waste_msg = generator.generate_waste_pallet_message(waste_pallet, len(regular_pallets))
        messages.append(waste_msg)
    
    return messages


# Funciones para envío en tiempo real durante la palletización
def send_start_pallet_message(pallet: Pallet, pallet_index: int) -> None:
    """
    Envía mensaje de inicio de pallet en tiempo real.
    
    Args:
        pallet: Objeto Pallet que se está iniciando
        pallet_index: Índice del pallet
    """
    generator = MQTTMessageGenerator()
    message = generator.generate_start_pallet_message(pallet, pallet_index)
    generator.send_to_robot(message)


def send_place_package_message(
    box: Box, 
    pallet: Pallet, 
    pallet_index: int,
    algorithm_used: str,
    quality_score: float
) -> None:
    """
    Envía mensaje de colocación de caja en tiempo real.
    
    Args:
        box: Objeto Box que se está colocando
        pallet: Objeto Pallet donde se coloca la caja
        pallet_index: Índice del pallet
        algorithm_used: Nombre del algoritmo utilizado
        quality_score: Puntuación de calidad actual del pallet
    """
    generator = MQTTMessageGenerator()
    message = generator.generate_place_package_message(
        box, pallet, pallet_index, algorithm_used, quality_score
    )
    generator.send_to_robot(message)


def send_complete_pallet_message(
    pallet: Pallet, 
    pallet_index: int,
    quality_score: float,
    used_volume: float
) -> None:
    """
    Envía mensaje de completado de pallet en tiempo real.
    
    Args:
        pallet: Objeto Pallet que se completó
        pallet_index: Índice del pallet
        quality_score: Puntuación de calidad final del pallet
        used_volume: Volumen utilizado del pallet (0.0 a 1.0)
    """
    generator = MQTTMessageGenerator()
    message = generator.generate_complete_pallet_message(
        pallet, pallet_index, quality_score, used_volume
    )
    generator.send_to_robot(message)
