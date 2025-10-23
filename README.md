# Sistema de Paletización DHL

Sistema de paletización inteligente que utiliza múltiples algoritmos para optimizar la colocación de cajas en pallets, con soporte para rotación de cajas, detección de violaciones de estabilidad y simulación de mensajes MQTT en tiempo real.

## Características Principales

### **Algoritmos de Paletización**
- **First-Fit** - Colocación secuencial simple
- **Best-Fit Decreasing** - Optimización por tamaño decreciente
- **First-Fit Decreasing** - Primera coincidencia con ordenamiento
- **Guillotine** - Algoritmo de corte guillotina
- **Best-Fit Lookahead** - Consideración de cajas futuras
- **Weight-Based** - Distribución por peso
- **KNN-Based** - Clustering inteligente con K-Nearest Neighbors

### **Sistema de Rotación de Cajas**
- ✅ Rotación automática de 90° para optimizar el espacio
- ✅ Evaluación de ambas orientaciones (0°/180° y 90°/270°)
- ✅ Orientación estándar: cara más larga como ancho, base más ancha como largo

### **Detección de Violaciones de Estabilidad**
- **Warnings inteligentes** cuando se sobrepasan límites de estabilidad
- **Configuración flexible** de límites de apilado
- **Estadísticas detalladas** de violaciones detectadas
- **Condiciones relajadas** para permitir más apilado (25% área, 30% peso)

### **Sistema MQTT en Tiempo Real**
- **Simulación de lector de barras** con mensajes MQTT
- **Simulación de robot** con confirmaciones de colocación
- **Sistema de cola** para procesamiento secuencial de cajas
- **Base de datos integrada** usando archivos CSV
- **Métricas en tiempo real** del estado del sistema

### **Interfaz Avanzada**
- **Modo Simulación** - Procesamiento tradicional de lotes
- **Modo Tiempo Real (MQTT)** - Simulación de flujo MQTT
- **Visualización 3D** interactiva de pallets y cajas
- **Historial detallado** con rotación y dimensiones efectivas
- **Exportación PDF** con reportes completos

## Requisitos

- Python 3.8+
- Dependencias listadas en `requirements.txt`

## Instalación

1. Clonar el repositorio:
```bash
git clone https://github.com/tu-usuario/sistema-paletizacion.git
cd sistema-paletizacion
```

2. Crear un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## 📁 Estructura del Proyecto

```
sistema-paletizacion/
├── src/
│   ├── core/                          # Núcleo del sistema
│   │   ├── box.py                     # Clase Box con rotaciones
│   │   ├── pallet.py                  # Clase Pallet con validador
│   │   ├── algorithms.py              # 7 algoritmos de paletización
│   │   ├── stacking_validator.py      # Validador de condiciones de apilado
│   │   ├── box_database.py            # Base de datos de cajas
│   │   ├── box_queue.py               # Cola asíncrona de cajas
│   │   ├── sync_box_queue.py          # Cola síncrona para Streamlit
│   │   ├── mqtt_message_handler.py    # Generador de mensajes MQTT
│   │   ├── mqtt_messages.py           # Mensajes MQTT existentes
│   │   ├── mqtt_publisher.py          # Publicador MQTT
│   │   └── queue_simulator.py         # Simulador del sistema
│   ├── visualization/
│   │   └── plotter.py                 # Visualización 3D
│   ├── simulation/
│   │   └── conveyor.py                # Simulación de cinta
│   ├── config/
│   │   └── config.py                  # Configuración del sistema
│   └── app.py                         # Aplicación Streamlit principal
├── config/
│   ├── default_config.yaml            # Configuración por defecto
│   └── secrets.toml                   # Configuración sensible (gitignored)
├── data/                              # Datos de entrada
│   ├── cajas_entrada.csv              # Datos de prueba originales
│   ├── cajas_entrada_prueba.csv       # Datos de prueba adicionales
│   ├── datos_para_paletizacion.csv    # Datos DHL normalizados
│   ├── datos_para_paletizacion_variado.csv
│   └── datos_para_paletizacion_extendido.csv
├── docs/
│   └── documentacion_proyecto.md      # Documentación técnica
├── requirements.txt                   # Dependencias Python
├── .gitignore                         # Archivos excluidos de Git
└── README.md                          # Este archivo
```

## Uso

### **Aplicación Web Principal**

Para iniciar la aplicación web:

```bash
streamlit run src/app.py
```

La aplicación incluye **dos modos de operación**:

#### **Modo Simulación**
- Configurar parámetros de pallets y cinta transportadora
- Seleccionar algoritmo de paletización (7 opciones)
- Cargar archivos CSV con datos de cajas
- Visualizar la paletización en 3D
- Ver estadísticas y detalles de la paletización
- Exportar reportes en PDF

#### **Modo Tiempo Real (MQTT)**
- Simular escaneo de cajas con lector de barras
- Procesar cajas una por una en tiempo real
- Simular confirmaciones del robot
- Monitorear estado de la cola en tiempo real
- Ver métricas de procesamiento
- Configurar límites de estabilidad

### **Configuración de Límites de Apilado**

En la interfaz web puedes configurar:
- **Área de soporte mínima** (10-100%)
- **Peso de soporte mínimo** (10-100%)
- **Permitir violaciones** de estabilidad
- **Mostrar warnings** detallados

### **Simulación de Cinta Transportadora**

Para ejecutar la simulación independiente:

```bash
python src/simulation/conveyor.py
```

## Formato del Archivo CSV

El archivo CSV debe contener las siguientes columnas:
- `id`: Identificador único de la caja
- `width`: Ancho de la caja (cm) - **Cara más larga**
- `length`: Largo de la caja (cm) - **Base más ancha**
- `height`: Alto de la caja (cm)
- `weight`: Peso de la caja (kg)

### **Orientación Estándar**
Las cajas deben estar en orientación estándar:
- **Width** = Cara más larga (paralela a la cinta)
- **Length** = Base más ancha (paralela a la cinta)
- **Height** = Altura (sin cambios)

## Configuración

### **Interfaz Web**
- Parámetros de pallets (dimensiones, peso máximo)
- Algoritmo de paletización
- Límites de estabilidad
- Archivo de datos CSV

### **Archivos de Configuración**
- `config/default_config.yaml` - Configuración por defecto
- `config/secrets.toml` - Configuración sensible (no incluido en Git)

## 🔌 API y Mensajes MQTT

### **Mensajes de Entrada (Lector de Barras)**
```json
{
  "message_type": "BOX_SCANNED",
  "timestamp": "2024-01-15T10:30:00Z",
  "scanner_id": "SCANNER_001",
  "package_data": {
    "package_id": "123",
    "barcode": "ABC123456"
  }
}
```

### **Mensajes de Salida (Comando al Robot)**
```json
{
  "message_type": "PLACE_PACKAGE",
  "timestamp": "2024-01-15T10:30:05Z",
  "package_id": "123",
  "pallet_id": "PALLET_1",
  "position": {"x": 10.5, "y": 15.2, "z": 25.0},
  "rotation": 90,
  "dimensions": {"width": 30.0, "length": 20.0, "height": 15.0}
}
```

### **Mensajes de Confirmación (Robot)**
```json
{
  "message_type": "PLACEMENT_CONFIRMED",
  "timestamp": "2024-01-15T10:30:10Z",
  "package_id": "123",
  "pallet_id": "PALLET_1",
  "status": "SUCCESS"
}
```

## 🧪 Testing

### **Scripts de Prueba Disponibles**
```bash
# Probar sistema de cola MQTT
python test_queue_system.py database
python test_queue_system.py single
python test_queue_system.py multiple
python test_queue_system.py full

# Probar sistema de detección de violaciones
python test_stacking_system.py
```

### **Datos de Prueba Incluidos**
- `data/cajas_entrada.csv` - Datos de prueba originales
- `data/cajas_entrada_prueba.csv` - Datos de prueba adicionales
- `data/datos_para_paletizacion*.csv` - Datos DHL normalizados

## Algoritmos de Paletización

| Algoritmo | Descripción | Mejor para |
|-----------|-------------|------------|
| **First-Fit** | Colocación secuencial simple | Casos básicos |
| **Best-Fit Decreasing** | Optimización por tamaño decreciente | Maximizar utilización |
| **First-Fit Decreasing** | Primera coincidencia con ordenamiento | Balance eficiencia/velocidad |
| **Guillotine** | Algoritmo de corte guillotina | Cajas rectangulares |
| **Best-Fit Lookahead** | Consideración de cajas futuras | Optimización avanzada |
| **Weight-Based** | Distribución por peso | Control de peso |
| **KNN-Based** | Clustering inteligente | Datos complejos |

## Desarrollo

### **Estructura de Clases Principales**
- `Box` - Representa una caja con rotaciones
- `Pallet` - Representa un pallet con validador de estabilidad
- `BoxDatabase` - Base de datos de cajas basada en CSV
- `SyncBoxQueue` - Cola síncrona para procesamiento
- `StackingValidator` - Validador de condiciones de apilado
- `MQTTMessageHandler` - Generador de mensajes MQTT

### **Configuración de Desarrollo**
```bash
# Instalar dependencias de desarrollo
pip install -r requirements.txt

# Ejecutar tests
python -m pytest tests/

# Formatear código
black src/
isort src/
```

## Contribuir

1. Hacer fork del repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.