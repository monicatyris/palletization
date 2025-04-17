# Sistema de Paletización

Sistema de paletización inteligente que utiliza el algoritmo First-Fit para optimizar la colocación de cajas en pallets.

## Características

- Algoritmo First-Fit para la colocación óptima de cajas
- Visualización 3D de los pallets y cajas
- Simulación de cinta transportadora
- Interfaz web con Streamlit
- Configuración personalizable
- Soporte para múltiples capas de cajas

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

## Estructura del Proyecto

```
sistema-paletizacion/
├── src/
│   ├── core/
│   │   ├── box.py
│   │   ├── pallet.py
│   │   └── algorithms.py
│   ├── visualization/
│   │   └── plotter.py
│   ├── simulation/
│   │   └── conveyor.py
│   ├── config/
│   │   └── config.py
│   └── app.py
├── config/
│   └── default_config.yaml
├── data/
│   └── cajas_entrada.csv
├── requirements.txt
└── README.md
```

## Uso

### Aplicación Web

Para iniciar la aplicación web:

```bash
streamlit run src/app.py
```

La aplicación permite:
- Configurar parámetros de pallets y cinta transportadora
- Cargar archivos CSV con datos de cajas
- Visualizar la paletización en 3D
- Ver estadísticas y detalles de la paletización

### Simulación de Cinta Transportadora

Para ejecutar la simulación:

```bash
python src/simulation/conveyor.py
```

## Formato del Archivo CSV

El archivo CSV debe contener las siguientes columnas:
- `id`: Identificador único de la caja
- `width`: Ancho de la caja (cm)
- `length`: Largo de la caja (cm)
- `height`: Alto de la caja (cm)
- `weight`: Peso de la caja (kg)

## Configuración

Los parámetros del sistema se pueden configurar en:
- Interfaz web de Streamlit
- Archivo `config/default_config.yaml`

## Contribuir

1. Hacer fork del repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles. 