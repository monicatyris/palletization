"""
MQTT Publisher para el sistema de paletización DHL.
Permite publicar eventos de paletización a través de MQTT.
"""

import json
from typing import Optional
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MQTTPublisher:
    """
    Clase para publicar eventos de paletización a través de MQTT.
    """
    
    def __init__(self, broker: str = "localhost", port: int = 1883, topic: str = "palletization/robot"):
        """
        Inicializa el publicador MQTT.
        
        Args:
            broker: Dirección del broker MQTT
            port: Puerto del broker MQTT
            topic: Tópico base para las publicaciones
        """
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = None
        self.connected = False
        
        # Intentar importar paho-mqtt si está disponible
        try:
            import paho.mqtt.client as mqtt
            self.mqtt = mqtt
            self._setup_client()
        except ImportError:
            logger.warning("paho-mqtt no está instalado. MQTT estará deshabilitado.")
            self.mqtt = None
    
    def _setup_client(self):
        """Configura el cliente MQTT."""
        if self.mqtt is None:
            return
            
        try:
            self.client = self.mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            # Intentar conectar
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                self.connected = True
                logger.info(f"Conectado al broker MQTT {self.broker}:{self.port}")
            except Exception as e:
                logger.warning(f"No se pudo conectar al broker MQTT: {e}")
                self.connected = False
                
        except Exception as e:
            logger.error(f"Error configurando cliente MQTT: {e}")
            self.connected = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback cuando se conecta al broker."""
        if rc == 0:
            logger.info("Conectado exitosamente al broker MQTT")
            self.connected = True
        else:
            logger.error(f"Error conectando al broker MQTT: {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback cuando se desconecta del broker."""
        logger.info("Desconectado del broker MQTT")
        self.connected = False
    
    def publish_box_placement(self, box, pallet, position):
        """
        Publica el evento de colocación de una caja.
        
        Args:
            box: Objeto Box que se está colocando
            pallet: Objeto Pallet donde se coloca
            position: Posición (x, y, z) donde se coloca
        """
        if not self.connected or self.client is None:
            return
            
        try:
            message = {
                "event": "box_placement",
                "box_id": getattr(box, 'id', 'unknown'),
                "box_dimensions": {
                    "width": box.width,
                    "length": box.length,
                    "height": box.height
                },
                "box_weight": getattr(box, 'weight', 0),
                "position": position,
                "pallet_id": getattr(pallet, 'id', 'unknown'),
                "timestamp": self._get_timestamp()
            }
            
            topic = f"{self.topic}/box_placement"
            self.client.publish(topic, json.dumps(message))
            logger.debug(f"Publicado evento box_placement: {message}")
            
        except Exception as e:
            logger.error(f"Error publicando evento box_placement: {e}")
    
    def publish_pallet_complete(self, pallet):
        """
        Publica el evento de pallet completado.
        
        Args:
            pallet: Objeto Pallet que se completó
        """
        if not self.connected or self.client is None:
            return
            
        try:
            message = {
                "event": "pallet_complete",
                "pallet_id": getattr(pallet, 'id', 'unknown'),
                "total_boxes": len(pallet.boxes),
                "total_weight": pallet.current_weight,
                "utilization_percentage": (pallet.current_weight / pallet.max_weight) * 100,
                "timestamp": self._get_timestamp()
            }
            
            topic = f"{self.topic}/pallet_complete"
            self.client.publish(topic, json.dumps(message))
            logger.debug(f"Publicado evento pallet_complete: {message}")
            
        except Exception as e:
            logger.error(f"Error publicando evento pallet_complete: {e}")
    
    def publish_simulation_start(self, config):
        """
        Publica el evento de inicio de simulación.
        
        Args:
            config: Configuración de la simulación
        """
        if not self.connected or self.client is None:
            return
            
        try:
            message = {
                "event": "simulation_start",
                "config": {
                    "max_width": config.pallet.max_width,
                    "max_length": config.pallet.max_length,
                    "max_height": config.pallet.max_height,
                    "max_weight": config.pallet.max_weight
                },
                "timestamp": self._get_timestamp()
            }
            
            topic = f"{self.topic}/simulation_start"
            self.client.publish(topic, json.dumps(message))
            logger.debug(f"Publicado evento simulation_start: {message}")
            
        except Exception as e:
            logger.error(f"Error publicando evento simulation_start: {e}")
    
    def publish_simulation_complete(self, pallets, total_boxes):
        """
        Publica el evento de simulación completada.
        
        Args:
            pallets: Lista de pallets generados
            total_boxes: Total de cajas procesadas
        """
        if not self.connected or self.client is None:
            return
            
        try:
            message = {
                "event": "simulation_complete",
                "total_pallets": len(pallets),
                "total_boxes": total_boxes,
                "average_boxes_per_pallet": total_boxes / len(pallets) if pallets else 0,
                "timestamp": self._get_timestamp()
            }
            
            topic = f"{self.topic}/simulation_complete"
            self.client.publish(topic, json.dumps(message))
            logger.debug(f"Publicado evento simulation_complete: {message}")
            
        except Exception as e:
            logger.error(f"Error publicando evento simulation_complete: {e}")
    
    def _get_timestamp(self):
        """Obtiene el timestamp actual."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def disconnect(self):
        """Desconecta del broker MQTT."""
        if self.client and self.connected:
            try:
                self.client.loop_stop()
                self.client.disconnect()
                self.connected = False
                logger.info("Desconectado del broker MQTT")
            except Exception as e:
                logger.error(f"Error desconectando del broker MQTT: {e}")
    
    def __del__(self):
        """Destructor para limpiar la conexión."""
        self.disconnect() 