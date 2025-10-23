import streamlit as st
import pandas as pd
import time
import asyncio
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from core.box import Box
from core.pallet import Pallet
from core.algorithms import (
    first_fit_palletization,
    best_fit_decreasing_palletization,
    first_fit_decreasing_palletization,
    guillotine_palletization,
    best_fit_lookahead_palletization,
    multi_pallet_palletization,
    calculate_pallet_quality,
    weight_based_palletization,
    knn_based_palletization,
    preprocess_knn_clustering
)
from visualization.plotter import visualize_pallets, print_palletization_summary
from config.config import AppConfig, PalletConfig, ConveyorConfig
from core.box_database import BoxDatabase
from core.sync_box_queue import SyncBoxQueue
from core.mqtt_message_handler import MQTTMessageHandler
from core.queue_simulator import QueueSimulator
import os
# from core.mqtt_publisher import MQTTPublisher
import plotly.graph_objects as go
import numpy as np
import json
from typing import List

def calculate_pallet_metrics(pallet: Pallet) -> dict:
    """Calcula métricas importantes del pallet."""
    return {
        "peso_utilizado": pallet.current_weight,
        "peso_maximo": pallet.max_weight,
        "porcentaje_peso": (pallet.current_weight / pallet.max_weight) * 100,
        "volumen_utilizado": sum(box.volume() for box in pallet.boxes),
        "volumen_total": pallet.max_width * pallet.max_length * pallet.max_height,
        "porcentaje_volumen": (sum(box.volume() for box in pallet.boxes) / 
                             (pallet.max_width * pallet.max_length * pallet.max_height)) * 100,
        "altura_utilizada": max((box.position[2] + box.height for box in pallet.boxes), default=0),
        "altura_maxima": pallet.max_height,
        "porcentaje_altura": (max((box.position[2] + box.height for box in pallet.boxes), default=0) / 
                            pallet.max_height) * 100
    }

def initialize_queue_system():
    """Inicializa el sistema de cola de cajas para modo tiempo real."""
    if st.session_state["box_database"] is None:
        st.session_state["box_database"] = BoxDatabase("data/datos_para_paletizacion_extendido.csv")
        st.session_state["box_queue"] = SyncBoxQueue(st.session_state["box_database"])
        st.session_state["mqtt_handler"] = MQTTMessageHandler()
        st.session_state["queue_simulator"] = QueueSimulator("data/datos_para_paletizacion_extendido.csv")

def find_pallet_for_box(box_id: str, pallets: List[Pallet]) -> str:
    """
    Encuentra en qué pallet se colocó una caja específica.
    
    Args:
        box_id: ID de la caja a buscar
        pallets: Lista de pallets donde buscar
    
    Returns:
        String con el identificador del pallet (ej: "Pallet 1", "Pallet 2")
    """
    for i, pallet in enumerate(pallets):
        for box in pallet.boxes:
            if box.id == box_id:
                return f"Pallet {i+1}"
    return "No asignado"

def get_waste_reason(box: Box, pallet_configs: List) -> str:
    """
    Determina la razón por la que una caja fue enviada al pallet de desechos.
    
    Args:
        box: La caja que no se pudo colocar
        pallet_configs: Lista de configuraciones de pallets
    
    Returns:
        String con la razón del desecho
    """
    reasons = []
    
    for i, config in enumerate(pallet_configs):
        # Verificar dimensiones
        if (box.width > config.max_width or 
            box.length > config.max_length or 
            box.height > config.max_height):
            reasons.append(f"Dimensiones exceden Pallet {i+1}")
        
        # Verificar peso
        if box.weight > config.max_weight:
            reasons.append(f"Peso excede Pallet {i+1}")
    
    if reasons:
        return "; ".join(reasons)
    else:
        return "No hay posición válida disponible"

def generate_pdf_report(history, pallets):
    """Genera un reporte PDF con el historial de la simulación."""
    # Crear el PDF en memoria
    from io import BytesIO
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Título
    title = Paragraph("Reporte de Paletización DHL", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Resumen general
    summary = Paragraph(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
    elements.append(summary)
    elements.append(Spacer(1, 12))
    
    # Historial de actualizaciones
    history_title = Paragraph("Historial de Actualizaciones", styles['Heading2'])
    elements.append(history_title)
    elements.append(Spacer(1, 12))
    
    # Crear tabla de historial
    history_data = [['Tiempo', 'Caja ID', 'Dimensiones', 'Rotación', 'Peso', 'Pallet', 'Métricas']]
    for entry in history:
        rotation_text = f"{entry.get('rotation', 0)}°" if 'rotation' in entry else "0°"
        history_data.append([
            entry['timestamp'],
            str(entry['box_id']),
            f"{entry['dimensions']} cm",
            rotation_text,
            f"{entry['weight']} kg",
            entry.get('pallet_assigned', 'N/A'),
            f"Peso: {entry['metrics']['peso_utilizado']:.1f} kg ({entry['metrics']['porcentaje_peso']:.1f}%)"
        ])
    
    history_table = Table(history_data)
    history_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(history_table)
    elements.append(Spacer(1, 20))
    
    # Resumen final
    final_title = Paragraph("Resumen Final", styles['Heading2'])
    elements.append(final_title)
    elements.append(Spacer(1, 12))
    
    # Calcular estadísticas reales (excluir pallet de desechos)
    regular_pallets = [p for p in pallets if not p.is_waste_pallet]
    waste_pallet = next((p for p in pallets if p.is_waste_pallet), None)
    
    total_pallets = len(regular_pallets)
    total_boxes = sum(len(p.boxes) for p in regular_pallets)
    avg_boxes_per_pallet = total_boxes / total_pallets if total_pallets > 0 else 0
    
    # Crear tabla de resumen general
    general_data = [
        ['Total de Pallets', str(total_pallets)],
        ['Total de Cajas', str(total_boxes)],
    ]
    
    general_table = Table(general_data)
    general_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(general_table)
    elements.append(Spacer(1, 20))
    
    # Tabla detallada por pallet
    detail_title = Paragraph("Distribución por Pallet", styles['Heading2'])
    elements.append(detail_title)
    elements.append(Spacer(1, 12))
    
    # Crear tabla de distribución por pallet (solo pallets regulares)
    detail_data = [['Pallet', 'Cajas', 'Peso (kg)', 'Volumen (cm³)', 'Utilización (%)']]
    for i, pallet in enumerate(regular_pallets):
        boxes_count = len(pallet.boxes)
        weight_used = pallet.current_weight
        volume_used = sum(box.volume() for box in pallet.boxes)
        total_volume = pallet.max_width * pallet.max_length * pallet.max_height
        utilization = (volume_used / total_volume * 100) if total_volume > 0 else 0
        
        detail_data.append([
            f"Pallet {i+1}",
            str(boxes_count),
            f"{weight_used:.1f}",
            f"{volume_used:.0f}",
            f"{utilization:.1f}%"
        ])
    
    detail_table = Table(detail_data)
    detail_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(detail_table)
    
    # Información del pallet de desechos
    if waste_pallet and waste_pallet.boxes:
        elements.append(Spacer(1, 20))
        
        waste_title = Paragraph("Pallet de Desechos", styles['Heading2'])
        elements.append(waste_title)
        elements.append(Spacer(1, 12))
        
        waste_info = Paragraph(f"<b>Total de cajas en desechos:</b> {len(waste_pallet.boxes)}", styles['Normal'])
        elements.append(waste_info)
        
        waste_weight = Paragraph(f"<b>Peso total en desechos:</b> {waste_pallet.current_weight:.1f} kg", styles['Normal'])
        elements.append(waste_weight)
        
        # Mostrar detalles de las cajas en desechos
        if len(waste_pallet.boxes) <= 20:  # Mostrar todas si son pocas
            waste_details = [f"{box.id} ({box.weight:.1f} kg)" for box in waste_pallet.boxes]
            waste_details_text = Paragraph(f"<b>Cajas en desechos:</b> {', '.join(waste_details)}", styles['Normal'])
            elements.append(waste_details_text)
        else:  # Mostrar resumen si son muchas
            waste_summary = [f"{box.id} ({box.weight:.1f} kg)" for box in waste_pallet.boxes[:20]]
            waste_summary_text = Paragraph(f"<b>Primeras 20 cajas:</b> {', '.join(waste_summary)}...", styles['Normal'])
            elements.append(waste_summary_text)
    
    # Generar PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Configuración de la página
st.set_page_config(
    page_title="Sistema de Paletización DHL",
    page_icon="📦",
    layout="wide"
)

# Inicialización del publicador MQTT
# mqtt_publisher = MQTTPublisher(
#     broker=st.secrets.get("MQTT_BROKER", "localhost"),
#     port=st.secrets.get("MQTT_PORT", 1883), 
#     topic=st.secrets.get("MQTT_TOPIC", "palletization/robot")
#)

# Variables para KNN pre-procesado
if "knn_assignments" not in st.session_state:
    st.session_state["knn_assignments"] = {}

def main():
    # Configuración de la aplicación
    st.title("📦 Sistema de Paletización DHL")
    
    # Inicializar el estado de la sesión
    if "pallets" not in st.session_state:
        st.session_state["pallets"] = []
    if "boxes" not in st.session_state:
        st.session_state["boxes"] = []
    if "config" not in st.session_state:
        # Crear configuraciones por defecto
        pallet_config1 = PalletConfig(
            max_width=120.0,
            max_length=100.0,
            max_height=200.0,
            max_weight=1000.0
        )
        pallet_config2 = PalletConfig(
            max_width=100.0,
            max_length=80.0,
            max_height=150.0,
            max_weight=800.0
        )
        conveyor_config = ConveyorConfig(
            interval_seconds=0.20,
            input_file="data/cajas_entrada.csv"
        )
        st.session_state["config"] = AppConfig(
            pallets=[pallet_config1, pallet_config2],  # Lista con dos pallets por defecto
            conveyor=conveyor_config
        )
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if "simulation_running" not in st.session_state:
        st.session_state["simulation_running"] = False
    if "rotation_angle" not in st.session_state:
        st.session_state["rotation_angle"] = 45
    if "simulation_complete" not in st.session_state:
        st.session_state["simulation_complete"] = False
    if "last_update_time" not in st.session_state:
        st.session_state["last_update_time"] = time.time()
    if "algorithm" not in st.session_state:
        st.session_state["algorithm"] = "First-Fit"
    if "volume_weight" not in st.session_state:
        st.session_state["volume_weight"] = 0.34
    if "weight_distribution_weight" not in st.session_state:
        st.session_state["weight_distribution_weight"] = 0.33
    if "stability_weight" not in st.session_state:
        st.session_state["stability_weight"] = 0.33
    
    # Inicializar sistema de cola de cajas para modo tiempo real
    if "box_database" not in st.session_state:
        st.session_state["box_database"] = None
    if "box_queue" not in st.session_state:
        st.session_state["box_queue"] = None
    if "mqtt_handler" not in st.session_state:
        st.session_state["mqtt_handler"] = None
    if "queue_simulator" not in st.session_state:
        st.session_state["queue_simulator"] = None
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("Configuración")
        
        # Selector de modo
        mode = st.selectbox(
            "Modo de operación",
            options=["Simulación", "Tiempo Real (MQTT)"],
            index=0,
            help="Selecciona el modo de operación del sistema"
        )
        
        # Mostrar configuración según el modo
        if mode == "Tiempo Real (MQTT)":
            st.info("🔴 Modo Tiempo Real: El sistema procesará cajas en tiempo real via MQTT")
            # Inicializar sistema de cola de cajas
            initialize_queue_system()
        else:
            st.info("🟡 Modo Simulación: El sistema procesará todas las cajas del CSV")
        
        # Crear un formulario para la configuración
        with st.form("config_form"):
            # Selección del número de pallets
            st.subheader("Configuración de Pallets")
            num_pallets = st.selectbox(
                "Número de pallets a llenar",
                options=[1, 2],
                index=1,  # Cambiar a 1 para que 2 sea el valor por defecto
                help="Selecciona cuántos pallets quieres configurar"
            )
            
            # Configuración de pallets
            pallets_config = []
            for i in range(num_pallets):
                with st.expander(f"Pallet {i+1}", expanded=False):  # Cambiar a expanded=False
                    st.write(f"**Configuración del Pallet {i+1}**")
                    
                    # Obtener valores por defecto del pallet actual si existe
                    default_width = st.session_state["config"].pallets[i].max_width if i < len(st.session_state["config"].pallets) else 120.0
                    default_length = st.session_state["config"].pallets[i].max_length if i < len(st.session_state["config"].pallets) else 100.0
                    default_height = st.session_state["config"].pallets[i].max_height if i < len(st.session_state["config"].pallets) else 200.0
                    default_weight = st.session_state["config"].pallets[i].max_weight if i < len(st.session_state["config"].pallets) else 1000.0
                    
                    pallet_width = st.number_input(
                        f"Ancho máximo (cm) - Pallet {i+1}",
                        min_value=10.0,
                        max_value=500.0,
                        value=default_width,
                        step=5.0,
                        key=f"width_{i}"
                    )
                    
                    pallet_length = st.number_input(
                        f"Largo máximo (cm) - Pallet {i+1}",
                        min_value=10.0,
                        max_value=500.0,
                        value=default_length,
                        step=5.0,
                        key=f"length_{i}"
                    )
                    
                    pallet_height = st.number_input(
                        f"Alto máximo (cm) - Pallet {i+1}",
                        min_value=10.0,
                        max_value=500.0,
                        value=default_height,
                        step=5.0,
                        key=f"height_{i}"
                    )
                    
                    pallet_weight = st.number_input(
                        f"Peso máximo (kg) - Pallet {i+1}",
                        min_value=10.0,
                        max_value=5000.0,
                        value=default_weight,
                        step=10.0,
                        key=f"weight_{i}"
                    )
                    
                    pallets_config.append(PalletConfig(
                        max_width=pallet_width,
                        max_length=pallet_length,
                        max_height=pallet_height,
                        max_weight=pallet_weight
                    ))
            
            # Configuración del transportador
            st.subheader("Configuración del Transportador")
            interval_seconds = st.number_input(
                "Intervalo de actualización (segundos)",
                min_value=0.1,
                max_value=10.0,
                value=st.session_state["config"].conveyor.interval_seconds,
                step=0.1,
                help="Tiempo entre actualizaciones de la simulación"
            )
            
            # Selección del algoritmo
            st.subheader("Algoritmo de Paletización")
            algorithm = st.selectbox(
                "Algoritmo de Paletización",
                [
                    "First-Fit",
                    "Best-Fit Decreasing",
                    "First-Fit Decreasing",
                    "Guillotine",
                    "Best-Fit Lookahead",
                    "Weight-Based",
                    "KNN-Based"
                ],
                help="Selecciona el algoritmo para organizar las cajas en los pallets"
            )
            
            # Validación especial para Weight-Based
            if algorithm == "Weight-Based" and num_pallets != 2:
                st.error("El algoritmo Weight-Based requiere exactamente 2 pallets. Cambiando automáticamente a 2 pallets.")
                num_pallets = 2
            
            # Configuración específica para Best-Fit Lookahead
            if algorithm == "Best-Fit Lookahead":
                lookahead = st.number_input(
                    "Número de cajas a mirar adelante",
                    min_value=1,
                    max_value=10,
                    value=st.session_state.get("lookahead", 3),
                    help="Número de cajas futuras a considerar para la decisión"
                )
            
            # Configuración de límites de apilado
            st.subheader("🔧 Configuración de Apilado")
            st.write("Configura los límites para el apilado de cajas:")
            
            col1, col2 = st.columns(2)
            
            with col1:
                min_support_area = st.slider(
                    "Área de soporte mínima (%)", 
                    min_value=10, max_value=100, value=25, step=5,
                    help="Porcentaje mínimo de área de soporte requerida para apilar cajas"
                )
                
                min_support_weight = st.slider(
                    "Peso de soporte mínimo (%)", 
                    min_value=10, max_value=100, value=30, step=5,
                    help="Porcentaje mínimo de peso de soporte requerido para apilar cajas"
                )
            
            with col2:
                allow_violations = st.checkbox(
                    "Permitir violaciones de estabilidad", 
                    value=True,
                    help="Permitir colocar cajas aunque no cumplan todas las condiciones de estabilidad"
                )
                
                show_warnings = st.checkbox(
                    "Mostrar warnings de estabilidad", 
                    value=True,
                    help="Mostrar advertencias cuando se detecten violaciones de condiciones de apilado"
                )
            
            # Configuración de pesos de calidad
            st.subheader("Pesos de Calidad")
            st.write("Configura la importancia de cada factor en la evaluación de calidad del pallet:")
            
            # Opciones de distribución de pesos
            weight_distribution_option = st.selectbox(
                "Distribución de pesos",
                options=[
                    "Equitativa (33% cada uno)",
                    "Priorizar Volumen (50% volumen, 25% peso, 25% estabilidad)",
                    "Priorizar Estabilidad (25% volumen, 25% peso, 50% estabilidad)",
                    "Priorizar Distribución de Peso (25% volumen, 50% peso, 25% estabilidad)",
                    "Personalizada"
                ],
                index=0,
                help="Selecciona cómo distribuir la importancia entre los factores"
            )
            
            # Calcular pesos basados en la selección
            if weight_distribution_option == "Equitativa (33% cada uno)":
                volume_weight = 0.34
                weight_distribution_weight = 0.33
                stability_weight = 0.33
            elif weight_distribution_option == "Priorizar Volumen (50% volumen, 25% peso, 25% estabilidad)":
                volume_weight = 0.5
                weight_distribution_weight = 0.25
                stability_weight = 0.25
            elif weight_distribution_option == "Priorizar Estabilidad (25% volumen, 25% peso, 50% estabilidad)":
                volume_weight = 0.25
                weight_distribution_weight = 0.25
                stability_weight = 0.5
            elif weight_distribution_option == "Priorizar Distribución de Peso (25% volumen, 50% peso, 25% estabilidad)":
                volume_weight = 0.25
                weight_distribution_weight = 0.5
                stability_weight = 0.25
            else:  # Personalizada
                st.write("**Configuración personalizada:**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    volume_weight = st.slider(
                        "Volumen",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state["volume_weight"],
                        step=0.05,
                        help="Importancia del aprovechamiento del espacio"
                    )
                
                with col2:
                    weight_distribution_weight = st.slider(
                        "Distribución Peso",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state["weight_distribution_weight"],
                        step=0.05,
                        help="Importancia del balance del peso en el pallet"
                    )
                
                with col3:
                    stability_weight = st.slider(
                        "Estabilidad",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state["stability_weight"],
                        step=0.05,
                        help="Importancia de la estabilidad de las cajas"
                    )
                
                # Normalizar los pesos para que sumen 1.0
                total_weight = volume_weight + weight_distribution_weight + stability_weight
                if total_weight > 0:
                    volume_weight = volume_weight / total_weight
                    weight_distribution_weight = weight_distribution_weight / total_weight
                    stability_weight = stability_weight / total_weight
                else:
                    # Si todos son 0, usar valores equitativos
                    volume_weight = 0.34
                    weight_distribution_weight = 0.33
                    stability_weight = 0.33
            
            # Mostrar los pesos finales
            st.markdown("**Pesos finales:**")
            col_weights1, col_weights2, col_weights3 = st.columns(3)
            
            with col_weights1:
                st.metric(
                    "Volumen",
                    f"{volume_weight:.1%}",
                    "Utilización del espacio"
                )
            
            with col_weights2:
                st.metric(
                    "Distribución",
                    f"{weight_distribution_weight:.1%}",
                    "Balance del peso"
                )
            
            with col_weights3:
                st.metric(
                    "Estabilidad",
                    f"{stability_weight:.1%}",
                    "Soporte de cajas"
                )
            
            # Verificar que sumen 1.0
            total = volume_weight + weight_distribution_weight + stability_weight
            if abs(total - 1.0) > 0.01:
                st.warning(f"⚠️ Los pesos suman {total:.3f}, deberían sumar 1.0")
            else:
                st.success(f"✅ Los pesos suman {total:.3f} (correcto)")
            
            # Obtener lista de archivos CSV en el directorio data
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
            data_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
            input_file = st.selectbox(
                "Archivo de entrada",
                options=data_files,
                index=data_files.index(st.session_state["config"].conveyor.input_file.split('/')[-1]) if st.session_state["config"].conveyor.input_file.split('/')[-1] in data_files else 0
            )
            input_file = os.path.join(data_dir, input_file)  # Construir ruta completa
            
            # Botón para aplicar la configuración
            if st.form_submit_button("Aplicar Configuración"):
                # Limpiar asignaciones KNN si se cambia el algoritmo
                if st.session_state.get("algorithm") != algorithm:
                    st.session_state["knn_assignments"] = {}
                
                # Actualizar configuración
                conveyor_config = ConveyorConfig(
                    interval_seconds=interval_seconds,
                    input_file=input_file
                )
                st.session_state["config"] = AppConfig(
                    pallets=pallets_config,  # Usar la lista de configuraciones de pallets
                    conveyor=conveyor_config
                )
                st.session_state["algorithm"] = algorithm
                if algorithm == "Best-Fit Lookahead":
                    st.session_state["lookahead"] = lookahead
                
                # Guardar los pesos de calidad
                st.session_state["volume_weight"] = volume_weight
                st.session_state["weight_distribution_weight"] = weight_distribution_weight
                st.session_state["stability_weight"] = stability_weight
                
                # Guardar configuración de apilado
                st.session_state["min_support_area"] = min_support_area / 100.0  # Convertir a decimal
                st.session_state["min_support_weight"] = min_support_weight / 100.0  # Convertir a decimal
                st.session_state["allow_violations"] = allow_violations
                st.session_state["show_warnings"] = show_warnings
                
                st.success("Configuración actualizada correctamente")
    
    # Mostrar interfaz según el modo
    if mode == "Tiempo Real (MQTT)":
        show_realtime_interface()
    else:
        show_simulation_interface()

def show_simulation_interface():
    """Muestra la interfaz de simulación tradicional."""
    # Crear dos columnas principales
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📊 Visualización en Tiempo Real")
        
        # Crear contenedor específico para el control de rotación
        rotation_container = st.empty()
        
        # Actualizar el contenedor de rotación basado en el estado de la simulación
        if st.session_state["simulation_complete"]:
            with rotation_container.container():
                with st.form("rotation_form"):
                    rotation_angle = st.slider(
                        "Ángulo de rotación", 
                        0, 360, 
                        st.session_state["rotation_angle"],
                        key="rotation_slider"
                    )
                    if st.form_submit_button("Aplicar Rotación"):
                        st.session_state["rotation_angle"] = rotation_angle
        else:
            with rotation_container.container():
                st.info("ℹ️ El control de rotación estará disponible cuando la simulación esté completa")
        
        # Crear contenedor para la visualización 3D
        visualization_container = st.empty()
        
        # Actualizar visualización si hay pallets
        if st.session_state["pallets"]:
            fig = visualize_pallets(st.session_state["pallets"], 
                                  rotation_angle=st.session_state["rotation_angle"])
            visualization_container.pyplot(fig)
            

        
        # Crear contenedor para la tabla de historial
        history_container = st.empty()
    
    with col2:
        st.header("Controles y Estado")
        
        if not st.session_state["simulation_running"] and not st.session_state["simulation_complete"]:
            if st.button("▶️ Iniciar Simulación", type="primary"):
                st.session_state["simulation_running"] = True
                st.session_state["simulation_complete"] = False
                st.session_state["pallets"] = []
                st.session_state["history"] = []
                
                # Cargar cajas desde el archivo CSV
                try:
                    df = pd.read_csv(st.session_state["config"].conveyor.input_file)
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    current_box_info = st.empty()
                    
                    for i, (_, row) in enumerate(df.iterrows()):
                        # Actualizar barra de progreso
                        progress = (i + 1) / len(df)
                        progress_bar.progress(progress)
                        
                        # Inicializar box como None al inicio de cada iteración
                        box = None
                        
                        try:
                            # Crear la caja actual
                            print(f"Intentando crear caja para fila {i+1}")
                            box = Box(
                                id=str(row['id']),  # Usar como string para manejar IDs con guiones
                                width=float(row['width']),
                                length=float(row['length']),
                                height=float(row['height']),
                                weight=float(row['weight'])
                            )
                            print(f"Caja creada exitosamente: {box.id}")
                            
                            # Solo continuar si la caja se creó exitosamente
                            if box is not None:
                                print(f"Procesando caja {box.id}")
                                
                                # Actualizar información de la caja actual
                                current_box_info.markdown(f"""
                                ### 📦 Caja Actual
                                - **ID:** {box.id}
                                - **Dimensiones:** {box.width}x{box.length}x{box.height} cm
                                - **Peso:** {box.weight} kg
                                - **Volumen:** {box.volume():.1f} cm³
                                """)
                                
                                st.session_state["boxes"].append(box)
                                print(f"Caja {box.id} agregada a la lista de cajas")
                                
                                # Realizar paletización según el algoritmo seleccionado
                                print(f"Ejecutando algoritmo: {st.session_state['algorithm']}")
                                
                                # Obtener las configuraciones de todos los pallets
                                pallet_configs = st.session_state["config"].pallets
                                
                                # Usar el algoritmo específico según la selección
                                if st.session_state["algorithm"] == "Weight-Based":
                                    # Verificar que tengamos exactamente 2 pallets configurados
                                    if len(pallet_configs) < 2:
                                        st.error("El algoritmo Weight-Based requiere exactamente 2 pallets configurados")
                                        st.session_state["simulation_running"] = False
                                        break
                                    
                                    # Usar el algoritmo basado en peso
                                    result_pallets = weight_based_palletization(
                                        st.session_state["boxes"],
                                        pallet1_config=pallet_configs[0],
                                        pallet2_config=pallet_configs[1],
                                        weight_threshold=3.0
                                    )
                                    
                                    # Verificar si la paletización fue exitosa
                                    if not result_pallets:
                                        st.error(f"❌ ERROR: La caja {box.id} ({box.weight} kg) no pudo ser colocada en ningún pallet disponible")
                                        st.error("La simulación se ha pausado debido a restricciones de espacio o peso")
                                        st.session_state["simulation_running"] = False
                                        break
                                    else:
                                        st.session_state["pallets"] = result_pallets
                                elif st.session_state["algorithm"] == "KNN-Based":
                                    # Verificar que tengamos exactamente 2 pallets configurados
                                    if len(pallet_configs) < 2:
                                        st.error("El algoritmo KNN-Based requiere exactamente 2 pallets configurados")
                                        st.session_state["simulation_running"] = False
                                        break
                                    
                                    # Ejecutar pre-procesamiento KNN automáticamente si no se ha hecho
                                    if not st.session_state.get("knn_assignments"):
                                        with st.spinner("🔄 Ejecutando pre-procesamiento KNN automáticamente..."):
                                            from core.algorithms import preprocess_knn_clustering
                                            
                                            # Ejecutar pre-procesamiento usando el archivo de entrada actual
                                            assignments = preprocess_knn_clustering(
                                                st.session_state["config"].conveyor.input_file, 
                                                pallet_configs
                                            )
                                            
                                            if assignments:
                                                st.session_state["knn_assignments"] = assignments
                                                st.success(f"✅ KNN pre-procesado automáticamente. {len(assignments)} cajas asignadas.")
                                            else:
                                                st.error("❌ Error en el pre-procesamiento KNN automático")
                                                st.session_state["simulation_running"] = False
                                                break
                                    
                                    # Crear pallets si no existen
                                    if "pallets" not in st.session_state or len(st.session_state["pallets"]) == 0:
                                        print(f"🔧 Creando pallets...")
                                        st.session_state["pallets"] = []
                                        for i, config in enumerate(pallet_configs):
                                            pallet = Pallet(
                                                max_width=config.max_width,
                                                max_length=config.max_length,
                                                max_height=config.max_height,
                                                max_weight=config.max_weight
                                            )
                                            
                                            # Aplicar configuración de apilado
                                            pallet.configure_stacking_limits(
                                                min_support_area_ratio=st.session_state.get("min_support_area", 0.25),
                                                min_support_weight_ratio=st.session_state.get("min_support_weight", 0.30),
                                                show_warnings=st.session_state.get("show_warnings", True),
                                                allow_violations=st.session_state.get("allow_violations", True)
                                            )
                                            
                                            st.session_state["pallets"].append(pallet)
                                            print(f"   Pallet {i} creado: {config.max_width}x{config.max_length}x{config.max_height}")
                                        
                                        # Crear pallet de desechos
                                        waste_pallet = Pallet(float('inf'), float('inf'), float('inf'), float('inf'), is_waste_pallet=True)
                                        st.session_state["pallets"].append(waste_pallet)
                                        print(f"   Pallet de desechos creado")
                                        print(f"   Total pallets: {len(st.session_state['pallets'])}")
                                    else:
                                        print(f"🔧 Pallets ya existen: {len(st.session_state['pallets'])}")
                                    
                                    # Procesar solo la caja actual usando asignaciones KNN
                                    box_id = int(box.id)
                                    if box_id in st.session_state["knn_assignments"]:
                                        assigned_pallet_id = st.session_state["knn_assignments"][box_id]
                                        
                                        # Debug: mostrar información
                                        print(f"🔍 Debug: Caja {box_id} asignada a pallet {assigned_pallet_id}")
                                        print(f"🔍 Debug: Pallets disponibles: {len(st.session_state['pallets'])}")
                                        print(f"🔍 Debug: IDs de pallets: {list(range(len(st.session_state['pallets'])))}")
                                        
                                        # Validar que el pallet asignado existe
                                        if assigned_pallet_id >= len(st.session_state["pallets"]):
                                            print(f"⚠️ Error: Pallet {assigned_pallet_id} no existe. Asignando al Pallet 0")
                                            assigned_pallet_id = 0
                                        
                                        target_pallet = st.session_state["pallets"][assigned_pallet_id]
                                        
                                        print(f"📦 Caja {box.id} (Peso: {box.weight} kg) → Pallet {assigned_pallet_id + 1}")
                                        
                                        # Intentar colocar la caja en el pallet asignado
                                        placed = False
                                        if target_pallet.can_fit(box):
                                            result = target_pallet.find_best_position(box, 10.0, 10.0, 10.0)
                                            if result:
                                                oriented_box, position = result
                                                x, y, z = position
                                                oriented_box.position = (x, y, z)
                                                target_pallet.boxes.append(oriented_box)
                                                target_pallet.current_weight += oriented_box.weight
                                                print(f"✅ Caja {oriented_box.id} colocada exitosamente en Pallet {assigned_pallet_id + 1} (orientación: {oriented_box.orientation.name})")
                                                placed = True
                                        
                                        # Si no se pudo colocar en el pallet asignado, intentar en otros pallets
                                        if not placed:
                                            for i, pallet in enumerate(st.session_state["pallets"]):
                                                if not pallet.is_waste_pallet and pallet.can_fit(box):
                                                    result = pallet.find_best_position(box, 10.0, 10.0, 10.0)
                                                    if result:
                                                        oriented_box, position = result
                                                        x, y, z = position
                                                        oriented_box.position = (x, y, z)
                                                        pallet.boxes.append(oriented_box)
                                                        pallet.current_weight += oriented_box.weight
                                                        print(f"✅ Caja {oriented_box.id} colocada exitosamente en Pallet {i + 1} (orientación: {oriented_box.orientation.name})")
                                                        placed = True
                                                        break
                                        
                                        # Si no se pudo colocar en ningún pallet regular, enviar al pallet de desechos
                                        if not placed:
                                            print(f"⚠️ Caja {box.id} no pudo ser colocada en ningún pallet regular - Enviando al pallet de desechos")
                                            waste_pallet = st.session_state["pallets"][-1]  # Último pallet es el de desechos
                                            waste_pallet.place_box(box)
                                            print(f"✅ Caja {box.id} enviada al pallet de desechos")
                                    else:
                                        print(f"⚠️ Caja {box.id} no encontrada en asignaciones KNN - Enviando al pallet de desechos")
                                        waste_pallet = st.session_state["pallets"][-1]
                                        waste_pallet.place_box(box)
                                        print(f"✅ Caja {box.id} enviada al pallet de desechos")
                                else:
                                    # Usar el algoritmo multi-pallet tradicional para otros algoritmos
                                    result_pallets = multi_pallet_palletization(
                                        st.session_state["boxes"],
                                        pallet_configs=pallet_configs,
                                        algorithm=st.session_state["algorithm"]
                                    )
                                    
                                    # Verificar si la paletización fue exitosa
                                    if not result_pallets:
                                        st.error(f"❌ ERROR: La caja {box.id} ({box.weight} kg) no pudo ser colocada en ningún pallet disponible")
                                        st.error("La simulación se ha pausado debido a restricciones de espacio o peso")
                                        st.session_state["simulation_running"] = False
                                        break
                                    else:
                                        st.session_state["pallets"] = result_pallets
                                
                                # Para KNN, no sobrescribir los pallets ya que se modifican directamente
                                if st.session_state["algorithm"] != "KNN-Based":
                                    print(f"Algoritmo ejecutado exitosamente. Pallets creados: {len(st.session_state['pallets'])}")
                                else:
                                    print(f"KNN ejecutado exitosamente. Pallets actuales: {len(st.session_state['pallets'])}")
                                
                                # Actualizar visualización 3D
                                fig = visualize_pallets(st.session_state["pallets"], 
                                                      rotation_angle=st.session_state["rotation_angle"])
                                visualization_container.pyplot(fig)
                                
                                # Actualizar métricas del pallet actual y guardar en historial
                                if st.session_state["pallets"]:
                                    # Encontrar el pallet específico donde se colocó esta caja y la caja orientada
                                    target_pallet = None
                                    oriented_box = None
                                    for pallet in st.session_state["pallets"]:
                                        for box_in_pallet in pallet.boxes:
                                            if box_in_pallet.id == box.id:
                                                target_pallet = pallet
                                                oriented_box = box_in_pallet
                                                break
                                        if target_pallet:
                                            break
                                    
                                    # Si no se encuentra el pallet específico, usar el último
                                    if not target_pallet and st.session_state["pallets"]:
                                        target_pallet = st.session_state["pallets"][-1]
                                    
                                    # Calcular métricas del pallet correcto
                                    if target_pallet:
                                        metrics = calculate_pallet_metrics(target_pallet)
                                        quality_score, quality_components = calculate_pallet_quality(
                                            target_pallet,
                                            volume_weight=st.session_state["volume_weight"],
                                            weight_distribution_weight=st.session_state["weight_distribution_weight"],
                                            stability_weight=st.session_state["stability_weight"]
                                        )
                                        
                                        # Usar la caja orientada si está disponible, sino usar la original
                                        box_for_history = oriented_box if oriented_box else box
                                        
                                        # Guardar en el historial (solo si la caja se creó exitosamente)
                                        st.session_state["history"].append({
                                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                                            "box_id": box_for_history.id,
                                            "dimensions": f"{box_for_history.get_effective_width()}x{box_for_history.get_effective_length()}x{box_for_history.get_effective_height()}",
                                            "rotation": 0 if box_for_history.orientation.name == "NORMAL" else 90,
                                            "weight": box_for_history.weight,
                                            "metrics": metrics,
                                            "quality_score": quality_score,
                                            "quality_components": quality_components,
                                            "pallet_assigned": find_pallet_for_box(box_for_history.id, st.session_state["pallets"])
                                        })
                                
                                # Mostrar resumen de violaciones de apilado
                                if st.session_state.get("show_warnings", True):
                                    st.subheader("⚠️ Resumen de Violaciones de Apilado")
                                    
                                    total_violations = 0
                                    total_warnings = 0
                                    total_errors = 0
                                    total_critical = 0
                                    
                                    for i, pallet in enumerate(st.session_state["pallets"]):
                                        if not pallet.is_waste_pallet:
                                            summary = pallet.get_stacking_violations_summary()
                                            total_violations += summary["violations_detected"]
                                            total_warnings += summary["warnings"]
                                            total_errors += summary["errors"]
                                            total_critical += summary["critical"]
                                    
                                    if total_violations > 0:
                                        col1, col2, col3, col4 = st.columns(4)
                                        
                                        with col1:
                                            st.metric("Total Violaciones", total_violations)
                                        with col2:
                                            st.metric("Warnings", total_warnings, delta=None)
                                        with col3:
                                            st.metric("Errores", total_errors, delta=None)
                                        with col4:
                                            st.metric("Críticos", total_critical, delta=None)
                                        
                                        # Mostrar detalles por pallet
                                        for i, pallet in enumerate(st.session_state["pallets"]):
                                            if not pallet.is_waste_pallet:
                                                summary = pallet.get_stacking_violations_summary()
                                                if summary["violations_detected"] > 0:
                                                    with st.expander(f"📊 Detalles Pallet {i+1}"):
                                                        st.write(f"**Configuración actual:**")
                                                        st.write(f"- Área de soporte mínima: {summary['config']['min_support_area_ratio']:.1%}")
                                                        st.write(f"- Peso de soporte mínimo: {summary['config']['min_support_weight_ratio']:.1%}")
                                                        st.write(f"- Permitir violaciones: {summary['config']['allow_violations']}")
                                                        
                                                        st.write(f"**Estadísticas:**")
                                                        st.write(f"- Total verificaciones: {summary['total_checks']}")
                                                        st.write(f"- Violaciones detectadas: {summary['violations_detected']}")
                                                        st.write(f"- Tasa de violaciones: {summary['violation_rate']:.1%}")
                                    else:
                                        st.success("✅ No se detectaron violaciones de condiciones de apilado")
                                
                                # Mostrar tabla de historial actualizada
                                with history_container.container():
                                    st.subheader("Historial de Colocación")
                                    # Crear DataFrame con las columnas más relevantes
                                    history_df = pd.DataFrame(st.session_state["history"])
                                    if not history_df.empty:
                                        # Seleccionar y renombrar columnas para mejor visualización
                                        display_df = history_df[["timestamp", "box_id", "dimensions", "rotation", "weight", "pallet_assigned"]].copy()
                                        display_df.columns = ["Hora", "ID Caja", "Dimensiones (cm)", "Rotación (°)", "Peso (kg)", "Pallet"]
                                        st.dataframe(display_df, use_container_width=True)
                                        
                                        # Mostrar información del pallet de desechos debajo de la tabla de historial
                                        waste_pallet = next((p for p in st.session_state["pallets"] if p.is_waste_pallet), None)
                                        if waste_pallet and waste_pallet.boxes:
                                            st.markdown("---")
                                            st.markdown("### 🗑️ Cajas en Pallet de Desechos")
                                            
                                            # Métricas resumidas
                                            col_waste1, col_waste2 = st.columns(2)
                                            with col_waste1:
                                                st.metric("Total Cajas", f"{len(waste_pallet.boxes)}")
                                            with col_waste2:
                                                st.metric("Peso Total", f"{waste_pallet.current_weight:.1f} kg")
                                            
                                            # Tabla de cajas en desecho con razón
                                            waste_data = []
                                            for box in waste_pallet.boxes:
                                                reason = get_waste_reason(box, st.session_state["config"].pallets)
                                                waste_data.append([box.id, reason])
                                            
                                            waste_df = pd.DataFrame(waste_data, columns=["ID Caja", "Razón del Desecho"])
                                            st.dataframe(waste_df, use_container_width=True)
                                    else:
                                        st.info("No hay cajas procesadas aún")
                                
                                # Esperar el intervalo configurado
                                time.sleep(st.session_state["config"].conveyor.interval_seconds)
                            else:
                                st.warning(f"No se pudo crear la caja de la fila {i+1}")
                                
                        except Exception as e:
                            import traceback
                            print(f"Error completo en fila {i+1}:")
                            print(traceback.format_exc())
                            st.error(f"Error procesando fila {i+1}: {str(e)}")
                            st.error(f"Datos de la fila: {row.to_dict()}")
                            continue
                    
                    st.session_state["simulation_running"] = False
                    st.session_state["simulation_complete"] = True
                    st.success("Simulación completada")
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Forzar la actualización del contenedor de rotación
                    with rotation_container.container():
                        st.session_state["rotation_angle"] = st.slider(
                            "🔄 Ángulo de rotación", 
                            0, 360, 
                            st.session_state["rotation_angle"],
                            key="rotation_slider"
                        )
                    

                    
                    # Mostrar métricas de calidad al final de la simulación
                    if st.session_state["pallets"]:
                        with st.expander("Métricas de Calidad por Pallet", expanded=False):
                            # Mostrar métricas para cada pallet (excluir el pallet de desechos)
                            regular_pallets = [p for p in st.session_state["pallets"] if not p.is_waste_pallet]
                            for i, pallet in enumerate(regular_pallets):
                                quality_score, quality_components = calculate_pallet_quality(
                                    pallet,
                                    volume_weight=st.session_state["volume_weight"],
                                    weight_distribution_weight=st.session_state["weight_distribution_weight"],
                                    stability_weight=st.session_state["stability_weight"]
                                )
                                
                                # Crear una sección para cada pallet usando header en lugar de expander
                                st.markdown(f"### Pallet {i+1} - Puntuación: {quality_score:.2f}")
                                
                                # Puntuación general del pallet
                                st.metric(
                                    "Puntuación General",
                                    f"{quality_score:.2f}",
                                    "de 1.0"
                                )
                                
                                # Componentes individuales
                                col_quality1, col_quality2 = st.columns(2)
                                
                                with col_quality1:
                                    st.markdown("#### Componentes")
                                    st.metric(
                                        "Utilización del Volumen",
                                        f"{quality_components['volume_utilization']:.2f}",
                                        f"({quality_components['weights']['volume']*100:.0f}% del total)"
                                    )
                                    st.metric(
                                        "Distribución del Peso",
                                        f"{quality_components['weight_distribution']:.2f}",
                                        f"({quality_components['weights']['weight']*100:.0f}% del total)"
                                    )
                                
                                with col_quality2:
                                    st.markdown("#### Componentes")
                                    st.metric(
                                        "Estabilidad de la Carga",
                                        f"{quality_components['stability_score']:.2f}",
                                        f"({quality_components['weights']['stability']*100:.0f}% del total)"
                                    )
                                
                                # Información adicional del pallet
                                st.markdown(f"""
                                **Información del Pallet {i+1}:**
                                - Cajas colocadas: {len(pallet.boxes)}
                                - Peso utilizado: {pallet.current_weight:.1f} kg / {pallet.max_weight:.1f} kg
                                - Dimensiones: {pallet.max_width}×{pallet.max_length}×{pallet.max_height} cm
                                """)
                                
                                # Separador entre pallets
                                if i < len(st.session_state["pallets"]) - 1:
                                    st.markdown("---")
                        
                        # Mostrar resumen general
                        st.markdown("---")
                        st.markdown("#### 📊 Resumen de Calidad")
                        
                        # Calcular promedio de calidad (excluir el pallet de desechos)
                        total_quality = 0
                        quality_scores = []
                        for pallet in st.session_state["pallets"]:
                            if not pallet.is_waste_pallet:  # Excluir pallet de desechos
                                quality_score, _ = calculate_pallet_quality(
                                    pallet,
                                    volume_weight=st.session_state["volume_weight"],
                                    weight_distribution_weight=st.session_state["weight_distribution_weight"],
                                    stability_weight=st.session_state["stability_weight"]
                                )
                                quality_scores.append(quality_score)
                                total_quality += quality_score
                        
                        if quality_scores:  # Solo calcular promedio si hay pallets regulares
                            avg_quality = total_quality / len(quality_scores)
                        else:
                            avg_quality = 0.0
                        
                        col_summary1, col_summary2, col_summary3 = st.columns(3)
                        
                        with col_summary1:
                            st.metric(
                                "Calidad Promedio",
                                f"{avg_quality:.2f}",
                                "de 1.0"
                            )
                        
                        with col_summary2:
                            st.metric(
                                "Mejor Pallet",
                                f"{max(quality_scores):.2f}",
                                f"Pallet {quality_scores.index(max(quality_scores))+1}"
                            )
                        
                        with col_summary3:
                            st.metric(
                                "Peor Pallet",
                                f"{min(quality_scores):.2f}",
                                f"Pallet {quality_scores.index(min(quality_scores))+1}"
                            )
                        
                        # Explicación de la métrica
                        st.markdown("""
                        #### 📝 Explicación de la Métrica
                        
                        La calidad del pallet se calcula considerando tres factores con ponderación equitativa:
                        
                        1. **Utilización del Volumen** (33%):
                           - Calcula la proporción del volumen total del pallet que está siendo utilizado
                           - Se obtiene dividiendo el volumen total de las cajas entre el volumen máximo del pallet
                           - Valores altos indican mejor aprovechamiento del espacio
                        
                        2. **Distribución del Peso** (33%):
                           - Calcula el centro de masa del pallet
                           - Compara la posición del centro de masa con el centro ideal del pallet
                           - La puntuación es mejor cuanto más cerca esté el centro de masa del centro del pallet
                           - Valores altos indican mejor balance del peso
                        
                        3. **Estabilidad de la Carga** (33%):
                           - Verifica que cada caja tenga soporte adecuado
                           - Una caja tiene soporte si:
                             - Está en el suelo (posición z = 0)
                             - O hay otra caja debajo que la soporte completamente
                           - Calcula el área de soporte para cada caja y asigna puntuaciones:
                             - Soporte completo (≥75%): 1.0
                             - Soporte parcial (≥50%): 0.7
                             - Soporte mínimo (≥25%): 0.3
                             - Soporte insuficiente (<25%): 0.0
                           - Valores altos indican mejor estabilidad
                        
                        **Puntuación Final:** Se calcula como la suma ponderada de los tres factores, donde cada uno contribuye equitativamente al resultado final.
                        """)
                    
                except Exception as e:
                    st.error(f"Error al cargar el archivo: {str(e)}")
                    st.session_state["simulation_running"] = False
                    st.session_state["simulation_complete"] = False
        
        # Botón de descarga del PDF (fuera del bloque de simulación)
        if st.session_state["simulation_complete"] and st.session_state["history"]:
            st.markdown("---")
            st.markdown("### 📄 Generar Reporte")
            if st.button("Generar Reporte PDF", type="primary"):
                with st.spinner("Generando reporte PDF..."):
                    pdf_buffer = generate_pdf_report(st.session_state["history"], st.session_state["pallets"])
                    st.download_button(
                        label="📥 Descargar Reporte PDF",
                        data=pdf_buffer,
                        file_name=f"palletization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )
            
            # Botón para generar mensajes MQTT
            st.markdown("### 📡 Generar Mensajes MQTT")
            if st.button("Generar Mensajes MQTT", type="primary"):
                with st.spinner("Generando mensajes MQTT..."):
                    try:
                        from core.mqtt_messages import create_mqtt_messages
                        
                        # Calcular puntuaciones de calidad para cada pallet
                        quality_scores = []
                        regular_pallets = [p for p in st.session_state["pallets"] if not p.is_waste_pallet]
                        
                        for pallet in regular_pallets:
                            quality_score, _ = calculate_pallet_quality(
                                pallet,
                                volume_weight=st.session_state["volume_weight"],
                                weight_distribution_weight=st.session_state["weight_distribution_weight"],
                                stability_weight=st.session_state["stability_weight"]
                            )
                            quality_scores.append(quality_score)
                        
                        # Generar mensajes MQTT
                        mqtt_messages = create_mqtt_messages(
                            st.session_state["pallets"],
                            st.session_state["algorithm"],
                            quality_scores
                        )
                        
                        # Mostrar mensajes en un expander
                        with st.expander("📡 Mensajes MQTT Generados", expanded=True):
                            st.success(f"✅ Se generaron {len(mqtt_messages)} mensajes MQTT")
                            
                            # Mostrar cada mensaje con formato
                            for i, message in enumerate(mqtt_messages):
                                st.markdown(f"#### Mensaje {i+1}: {message['instruction_type']}")
                                st.json(message)
                                st.markdown("---")
                            
                            # Botón para descargar todos los mensajes como JSON
                            import json
                            mqtt_json = json.dumps(mqtt_messages, indent=2, ensure_ascii=False)
                            st.download_button(
                                label="📥 Descargar Mensajes MQTT (JSON)",
                                data=mqtt_json,
                                file_name=f"mqtt_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                    
                    except Exception as e:
                        st.error(f"Error generando mensajes MQTT: {str(e)}")
                        st.error("Asegúrate de que la simulación se haya completado correctamente")

def show_realtime_interface():
    """Muestra la interfaz de tiempo real con sistema de cola de cajas."""
    st.header("🔴 Sistema de Cola de Cajas en Tiempo Real")
    
    # Crear columnas para el layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Estado de la Cola")
        
        # Mostrar estado de la cola
        if st.session_state["box_queue"]:
            # Mostrar estado actual de la cola
            status = st.session_state["box_queue"].get_queue_status()
            
            # Crear métricas
            col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
            
            with col_metric1:
                st.metric("📦 Pendientes", status["queue_length"])
            with col_metric2:
                st.metric("🔄 Procesando", status["processing_length"])
            with col_metric3:
                st.metric("✅ Completadas", status["completed_count"])
            with col_metric4:
                st.metric("❌ Fallidas", status["stats"]["total_failed"])
            
            # Mostrar resumen detallado
            st.markdown("#### 📊 Resumen Detallado")
            st.text(st.session_state["box_queue"].get_queue_summary())
            
            # Botón para actualizar estado
            if st.button("🔄 Actualizar Estado", type="primary"):
                st.rerun()  # Recargar la página para mostrar el estado actualizado
        
        st.subheader("📦 Simulación de Mensajes MQTT")
        
        # Simulador de lector de barras
        st.markdown("#### 📱 Simulador de Lector de Barras")
        col_scanner1, col_scanner2 = st.columns(2)
        
        with col_scanner1:
            box_id = st.text_input("ID de Caja", value="1", help="Ingresa el ID de la caja a escanear")
            barcode = st.text_input("Código de Barras", value="BC000001", help="Código de barras simulado")
        
        with col_scanner2:
            scanner_id = st.selectbox("Scanner ID", options=["SCANNER_001", "SCANNER_002", "SCANNER_003"])
            if st.button("📱 Simular Escaneo", type="primary"):
                if st.session_state["box_queue"]:
                    # Crear mensaje simulado
                    message = st.session_state["mqtt_handler"].create_barcode_message(
                        package_id=box_id,
                        barcode=barcode,
                        scanner_id=scanner_id
                    )
                    
                    # Procesar mensaje
                    with st.spinner("Procesando escaneo..."):
                        success = st.session_state["box_queue"].add_scanned_box(message)
                        if success:
                            st.success(f"Caja {box_id} escaneada y añadida a la cola exitosamente")
                            st.json(message)
                        else:
                            st.error(f"Error procesando caja {box_id}")
                else:
                    st.error("Sistema de cola no inicializado")
        
        # Simulador de confirmación del robot
        st.markdown("#### 🤖 Simulador de Confirmación del Robot")
        col_robot1, col_robot2 = st.columns(2)
        
        with col_robot1:
            robot_package_id = st.text_input("Package ID", value="1", help="ID de la caja a confirmar")
            pallet_id = st.selectbox("Pallet ID", options=["P001", "P002", "P003"])
        
        with col_robot2:
            status = st.selectbox("Status", options=["SUCCESS", "FAILED"])
            if st.button("🤖 Simular Confirmación", type="primary"):
                if st.session_state["box_queue"]:
                    # Crear mensaje de confirmación simulado
                    confirmation = st.session_state["mqtt_handler"].create_robot_confirmation(
                        package_id=robot_package_id,
                        pallet_id=pallet_id,
                        status=status
                    )
                    
                    # Procesar confirmación
                    with st.spinner("Procesando confirmación..."):
                        success = st.session_state["box_queue"].handle_robot_confirmation(confirmation)
                        if success:
                            if status == "SUCCESS":
                                st.success(f"Caja {robot_package_id} confirmada exitosamente")
                            else:
                                st.error(f"Caja {robot_package_id} falló en la colocación")
                        else:
                            st.error(f"Error procesando confirmación de caja {robot_package_id}")
                        st.json(confirmation)
                else:
                    st.error("Sistema de cola no inicializado")
    
    with col2:
        st.subheader("📈 Estadísticas en Tiempo Real")
        
        if st.session_state["box_queue"]:
            # Mostrar estadísticas de la cola
            status = st.session_state["box_queue"].get_queue_status()
            stats = status["stats"]
            
            st.metric("📦 Total Escaneadas", stats["total_scanned"])
            st.metric("✅ Total Validadas", stats["total_validated"])
            st.metric("📋 Total Encoladas", stats["total_queued"])
            st.metric("🔄 Total Procesadas", stats["total_processed"])
            st.metric("✅ Total Completadas", stats["total_completed"])
            st.metric("❌ Total Fallidas", stats["total_failed"])
            
            # Botón para limpiar estadísticas
            if st.button("🧹 Limpiar Estadísticas"):
                st.session_state["box_queue"].clear_completed_boxes()
                st.success("Estadísticas limpiadas")
                st.rerun()
        
        st.subheader("🎮 Controles del Sistema")
        
        # Botón para iniciar simulación automática
        if st.button("🚀 Iniciar Simulación Automática", type="primary"):
            if st.session_state["queue_simulator"]:
                with st.spinner("Iniciando simulación automática..."):
                    # Aquí se iniciaría la simulación automática
                    st.success("Simulación automática iniciada")
            else:
                st.error("Simulador no inicializado")
        
        # Botón para detener simulación
        if st.button("⏹️ Detener Simulación"):
            st.success("Simulación detenida")
        
        # Botón para exportar datos
        if st.button("📥 Exportar Datos"):
            st.success("Datos exportados exitosamente")

if __name__ == "__main__":
    main() 