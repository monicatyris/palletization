# Documentación del Sistema de Paletización DHL

## 1. Descripción General
El sistema de paletización desarrollado es una herramienta interactiva que permite optimizar la colocación de cajas en pallets, considerando múltiples factores como dimensiones, peso, estabilidad y eficiencia espacial.

## 2. Características Principales

### 2.1 Interfaz de Usuario
- Visualización 3D interactiva de pallets y cajas
- Panel de control con configuración en tiempo real
- Historial detallado de la paletización
- Métricas de calidad en tiempo real
- Generación de reportes PDF

### 2.2 Algoritmos de Paletización
El sistema implementa varios algoritmos de paletización:

1. **First-Fit**
   - Coloca cada caja en el primer pallet disponible que pueda contenerla
   - Simple y rápido, pero puede no ser óptimo en términos de espacio

2. **Best-Fit Decreasing**
   - Ordena las cajas por volumen de mayor a menor
   - Coloca cada caja en el pallet que mejor se ajuste
   - Mejor utilización del espacio que First-Fit

3. **First-Fit Decreasing**
   - Ordena las cajas por volumen de mayor a menor
   - Coloca cada caja en el primer pallet disponible
   - Balance entre velocidad y eficiencia

4. **Guillotine**
   - Divide el espacio del pallet en rectángulos
   - Optimiza el uso del espacio considerando cortes
   - Eficiente para cajas de tamaños similares

5. **Best-Fit Lookahead**
   - Considera las próximas N cajas al decidir dónde colocar la caja actual
   - Calcula un score basado en:
     - Utilización del espacio (40%)
     - Potencial para cajas futuras (30%)
     - Estabilidad (20%)
     - Distribución del peso (10%)

### 2.3 Métricas de Calidad
El sistema calcula y muestra métricas de calidad para cada pallet:

1. **Utilización del Volumen (40%)**
   - Calcula la proporción del volumen total del pallet que está siendo utilizado
   - Valores altos indican mejor aprovechamiento del espacio

2. **Distribución del Peso (30%)**
   - Evalúa el centro de masa del pallet
   - Mejor puntuación cuando el centro de masa está cerca del centro del pallet
   - Importante para la estabilidad durante el transporte

3. **Estabilidad de la Carga (20%)**
   - Verifica que cada caja tenga soporte adecuado
   - Penaliza cajas sin soporte completo
   - Crítico para la seguridad durante el manejo

4. **Utilización de la Altura (10%)**
   - Mide el aprovechamiento de la altura máxima permitida
   - Ayuda a optimizar el espacio vertical

## 3. Configuración del Sistema

### 3.1 Parámetros del Pallet
- Ancho máximo (cm)
- Largo máximo (cm)
- Alto máximo (cm)
- Peso máximo (kg)

### 3.2 Parámetros de la Cinta Transportadora
- Intervalo entre cajas (segundos)
- Archivo de entrada de cajas (CSV)

### 3.3 Parámetros del Algoritmo
- Selección del algoritmo de paletización
- Número de cajas a mirar adelante (para Best-Fit Lookahead)

## 4. Entrada de Datos
El sistema acepta archivos CSV con la siguiente estructura:
```csv
id,width,length,height,weight
1,30,20,15,5
2,40,30,20,15
...
```

## 5. Salida y Reportes
- Visualización 3D interactiva
- Historial detallado de la paletización
- Métricas de calidad por pallet
- Reporte PDF con resumen de la simulación

## 6. Tecnologías Utilizadas
- Python 3.x
- Streamlit (interfaz web)
- Matplotlib (visualización 3D)
- ReportLab (generación de PDFs)
- NumPy (cálculos matemáticos)

## 7. Próximos Pasos
- Implementación de algoritmos adicionales
- Optimización de la visualización 3D
- Mejora en las métricas de calidad
- Integración con sistemas de gestión de almacén
- Análisis predictivo de la mejor configuración

# 5. Diseño del Algoritmo Subóptimo

## 5.1 Investigación de Algoritmos de Paletización

### 5.1.1 Análisis de Algoritmos Existentes
Durante la investigación inicial, se analizaron varios algoritmos clásicos de paletización:

1. **Algoritmos de Primera Clase**
   - First-Fit
   - Best-Fit
   - Next-Fit
   - Características: Simples, rápidos, pero con limitaciones en la optimización del espacio

2. **Algoritmos de Segunda Clase**
   - First-Fit Decreasing
   - Best-Fit Decreasing
   - Características: Mejor utilización del espacio, pero requieren ordenamiento previo

3. **Algoritmos de Tercera Clase**
   - Guillotine
   - Skyline
   - Características: Consideran la geometría del espacio, más complejos pero más eficientes

### 5.1.2 Selección de Algoritmos para Implementación
Se seleccionaron los siguientes algoritmos para implementación basándose en:
- Complejidad computacional
- Eficiencia en la utilización del espacio
- Adaptabilidad a diferentes tipos de cajas
- Facilidad de implementación

1. **First-Fit**
   - Implementación inicial como base de referencia
   - Complejidad: O(n)
   - Ventajas: Simple y rápido
   - Desventajas: Puede dejar espacios vacíos significativos

2. **Best-Fit Decreasing**
   - Mejora significativa en la utilización del espacio
   - Complejidad: O(n log n) por el ordenamiento
   - Ventajas: Mejor aprovechamiento del espacio
   - Desventajas: Mayor tiempo de procesamiento

3. **First-Fit Decreasing**
   - Balance entre velocidad y eficiencia
   - Complejidad: O(n log n)
   - Ventajas: Buen rendimiento general
   - Desventajas: No siempre encuentra la solución óptima

4. **Guillotine**
   - Enfoque geométrico avanzado
   - Complejidad: O(n²)
   - Ventajas: Excelente para cajas de tamaños similares
   - Desventajas: Más complejo de implementar

5. **Best-Fit Lookahead (Desarrollo Propio)**
   - Algoritmo híbrido que combina características de los anteriores
   - Complejidad: O(n²)
   - Características innovadoras:
     - Consideración de cajas futuras
     - Sistema de puntuación multidimensional
     - Optimización de múltiples factores simultáneamente

## 5.2 Diseño del Algoritmo Best-Fit Lookahead

### 5.2.1 Estructura General
```python
def best_fit_lookahead_palletization(boxes, pallet_dimensions, lookahead=3):
    # 1. Ordenar cajas por volumen (decreciente)
    # 2. Inicializar lista de pallets
    # 3. Para cada caja:
    #    a. Obtener las siguientes N cajas (lookahead)
    #    b. Evaluar todas las posiciones posibles
    #    c. Calcular score para cada posición
    #    d. Seleccionar mejor posición
    #    e. Actualizar estado del pallet
```

### 5.2.2 Sistema de Puntuación
El algoritmo utiliza un sistema de puntuación multidimensional:

1. **Utilización del Espacio (40%)**
   - Calcula el volumen ocupado vs. volumen total
   - Considera espacios vacíos
   - Evalúa la compactación de las cajas

2. **Potencial para Cajas Futuras (30%)**
   - Analiza las N siguientes cajas
   - Evalúa la compatibilidad de tamaños
   - Predice la utilización del espacio restante

3. **Estabilidad (20%)**
   - Verifica el soporte de cada caja
   - Evalúa el centro de masa
   - Considera la distribución del peso

4. **Distribución del Peso (10%)**
   - Calcula el centro de masa
   - Evalúa el balance del pallet
   - Considera restricciones de peso máximo

### 5.2.3 Optimizaciones Implementadas

1. **Preprocesamiento**
   - Ordenamiento eficiente de cajas
   - Filtrado de cajas inviables
   - Agrupación por características similares

2. **Evaluación de Posiciones**
   - Uso de estructuras de datos espaciales
   - Cálculo rápido de intersecciones
   - Memoización de resultados intermedios

3. **Gestión de Memoria**
   - Reutilización de estructuras de datos
   - Limpieza periódica de estados intermedios
   - Optimización de uso de memoria

## 5.3 Resultados y Comparativas

### 5.3.1 Métricas de Rendimiento
- Tiempo de ejecución promedio
- Utilización del espacio
- Número de pallets utilizados
- Estabilidad de la carga

### 5.3.2 Comparativa entre Algoritmos
| Algoritmo | Tiempo | Espacio | Estabilidad | Complejidad |
|-----------|--------|---------|-------------|-------------|
| First-Fit | O(n)   | 65-75%  | Media       | Baja        |
| Best-Fit  | O(n²)  | 75-85%  | Alta        | Media       |
| Lookahead | O(n²)  | 80-90%  | Muy Alta    | Alta        |

## 5.4 Conclusiones y Mejoras Futuras

### 5.4.1 Conclusiones
- El algoritmo Best-Fit Lookahead demuestra mejor rendimiento general
- La consideración de cajas futuras mejora significativamente la utilización del espacio
- El sistema de puntuación multidimensional permite optimizar múltiples factores simultáneamente

### 5.4.2 Mejoras Propuestas
1. **Optimizaciones de Rendimiento**
   - Paralelización del cálculo de scores
   - Mejora en las estructuras de datos espaciales
   - Reducción de la complejidad computacional

2. **Mejoras en la Calidad**
   - Refinamiento del sistema de puntuación
   - Consideración de más factores en la evaluación
   - Mejora en la predicción de cajas futuras

3. **Extensiones**
   - Soporte para cajas irregulares
   - Consideración de restricciones adicionales
   - Integración con sistemas de aprendizaje automático 