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
Durante la investigación inicial, se analizaron varios algoritmos de paletización, cada uno con sus propias ventajas y limitaciones:

1. **Algoritmos de Primera Generación**
   - **First-Fit (FF)**
     - Enfoque simple y directo
     - Coloca cada caja en el primer pallet disponible que pueda contenerla
     - Ventaja: Implementación sencilla y rápida
     - Desventaja: Puede resultar en una utilización subóptima del espacio

   - **Best-Fit (BF)**
     - Busca el pallet que mejor se ajuste para cada caja
     - Ventaja: Mejor utilización del espacio que First-Fit
     - Desventaja: Mayor complejidad computacional

2. **Algoritmos de Segunda Generación**
   - **First-Fit Decreasing (FFD)**
     - Ordena las cajas por volumen de mayor a menor
     - Aplica la estrategia First-Fit sobre cajas ordenadas
     - Ventaja: Mejor utilización del espacio que FF
     - Desventaja: Requiere ordenamiento previo

   - **Best-Fit Decreasing (BFD)**
     - Ordena las cajas por volumen de mayor a menor
     - Aplica la estrategia Best-Fit sobre cajas ordenadas
     - Ventaja: Mejor utilización del espacio que FFD
     - Desventaja: Mayor tiempo de procesamiento

3. **Algoritmos de Tercera Generación**
   - **Guillotine**
     - Divide el espacio del pallet en rectángulos
     - Optimiza el uso del espacio considerando cortes
     - Ventaja: Eficiente para cajas de tamaños similares
     - Desventaja: Puede dejar espacios inutilizables

   - **Best-Fit Lookahead (BFL)**
     - Considera las próximas N cajas al decidir dónde colocar la caja actual
     - Implementa un sistema de puntuación multicriterio
     - Ventaja: Mejor toma de decisiones considerando el futuro
     - Desventaja: Mayor complejidad y tiempo de procesamiento

### 5.1.2 Selección del Algoritmo Base
Después del análisis, se seleccionó el algoritmo Best-Fit Lookahead como base por las siguientes razones:

1. **Ventajas Competitivas**
   - Mejor utilización del espacio
   - Consideración de futuras cajas
   - Sistema de puntuación multicriterio
   - Adaptabilidad a diferentes escenarios

2. **Sistema de Puntuación**
   El algoritmo utiliza un sistema de puntuación ponderado:
   - Utilización del espacio (40%)
   - Potencial para cajas futuras (30%)
   - Estabilidad (20%)
   - Distribución del peso (10%)

### 5.1.3 Mejoras Implementadas
Se han implementado varias mejoras al algoritmo base:

1. **Optimización de la Búsqueda**
   - Reducción del espacio de búsqueda
   - Implementación de heurísticas para acelerar la toma de decisiones
   - Caché de resultados para posiciones frecuentes

2. **Sistema de Validación**
   - Verificación de restricciones en tiempo real
   - Validación de estabilidad
   - Comprobación de límites de peso

3. **Métricas de Calidad**
   - Implementación de sistema de puntuación detallado
   - Monitoreo en tiempo real
   - Historial de decisiones

### 5.1.4 Resultados Esperados
El algoritmo subóptimo diseñado se espera que logre:

1. **Eficiencia**
   - Utilización del espacio > 85%
   - Tiempo de procesamiento < 1 segundo por caja
   - Estabilidad de carga > 90%

2. **Flexibilidad**
   - Adaptación a diferentes tipos de cajas
   - Manejo de restricciones variables
   - Escalabilidad para diferentes volúmenes

3. **Calidad**
   - Distribución uniforme del peso
   - Estabilidad garantizada
   - Optimización del espacio vertical 