import streamlit as st
import pandas as pd
import time
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
    best_fit_lookahead_palletization
)
from visualization.plotter import visualize_pallets, print_palletization_summary
from config.config import AppConfig, PalletConfig, ConveyorConfig
import os

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

def calculate_pallet_quality(pallet: Pallet) -> tuple:
    """Calcula la calidad del pallet basada en varios factores."""
    # 1. Utilización del Volumen (40%)
    total_volume = pallet.max_width * pallet.max_length * pallet.max_height
    used_volume = sum(box.volume() for box in pallet.boxes)
    volume_utilization = used_volume / total_volume if total_volume > 0 else 0
    
    # 2. Distribución del Peso (30%)
    # Calculamos el centro de masa del pallet
    total_weight = sum(box.weight for box in pallet.boxes)
    if total_weight > 0:
        center_x = sum(box.weight * (box.position[0] + box.width/2) for box in pallet.boxes) / total_weight
        center_y = sum(box.weight * (box.position[1] + box.length/2) for box in pallet.boxes) / total_weight
        
        # La distribución ideal sería en el centro del pallet
        ideal_center_x = pallet.max_width / 2
        ideal_center_y = pallet.max_length / 2
        
        # Calculamos la desviación del centro de masa respecto al centro ideal
        deviation_x = abs(center_x - ideal_center_x) / (pallet.max_width / 2)
        deviation_y = abs(center_y - ideal_center_y) / (pallet.max_length / 2)
        
        # La distribución del peso es mejor cuanto más cerca esté del centro
        weight_distribution = 1 - (deviation_x + deviation_y) / 2
    else:
        weight_distribution = 0
    
    # 3. Estabilidad de la Carga (20%)
    stability_score = 1.0
    for box in pallet.boxes:
        # Verificamos si la caja tiene soporte debajo
        has_support = False
        for other_box in pallet.boxes:
            if other_box != box:
                # La caja tiene soporte si hay otra caja debajo que la soporte
                if (other_box.position[2] + other_box.height == box.position[2] and
                    other_box.position[0] <= box.position[0] + box.width and
                    other_box.position[0] + other_box.width >= box.position[0] and
                    other_box.position[1] <= box.position[1] + box.length and
                    other_box.position[1] + other_box.length >= box.position[1]):
                    has_support = True
                    break
        
        # Si la caja está en el suelo, tiene soporte
        if box.position[2] == 0:
            has_support = True
        
        if not has_support:
            stability_score -= 0.1  # Penalizamos por cada caja sin soporte
    
    # 4. Utilización de la Altura (10%)
    max_height = max((box.position[2] + box.height for box in pallet.boxes), default=0)
    height_utilization = max_height / pallet.max_height if pallet.max_height > 0 else 0
    
    # Pesos de cada componente
    weights = {
        'volume': 0.40,
        'weight': 0.30,
        'stability': 0.20,
        'height': 0.10
    }
    
    # Cálculo de la puntuación total
    quality_score = (
        volume_utilization * weights['volume'] +
        weight_distribution * weights['weight'] +
        stability_score * weights['stability'] +
        height_utilization * weights['height']
    )
    
    # Aseguramos que los valores estén entre 0 y 1
    quality_score = max(0, min(1, quality_score))
    volume_utilization = max(0, min(1, volume_utilization))
    weight_distribution = max(0, min(1, weight_distribution))
    stability_score = max(0, min(1, stability_score))
    height_utilization = max(0, min(1, height_utilization))
    
    quality_components = {
        'volume_utilization': volume_utilization,
        'weight_distribution': weight_distribution,
        'stability_score': stability_score,
        'height_utilization': height_utilization,
        'weights': weights
    }
    
    return quality_score, quality_components

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
    history_data = [['Tiempo', 'Caja ID', 'Dimensiones', 'Peso', 'Métricas']]
    for entry in history:
        history_data.append([
            entry['timestamp'],
            str(entry['box_id']),
            f"{entry['dimensions']} cm",
            f"{entry['weight']} kg",
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
    
    final_data = [
        ['Total de Pallets', str(len(pallets))],
        ['Total de Cajas', str(sum(len(p.boxes) for p in pallets))],
        ['Cajas por Pallet', f"{sum(len(p.boxes) for p in pallets) / len(pallets):.1f}"],
    ]
    
    final_table = Table(final_data)
    final_table.setStyle(TableStyle([
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
    elements.append(final_table)
    
    # Generar PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def main():
    # Configuración de la aplicación
    st.set_page_config(
        page_title="Sistema de Paletización DHL",
        page_icon="📦",
        layout="wide"
    )
    
    st.title("📦 Sistema de Paletización DHL")
    
    # Inicializar el estado de la sesión
    if "pallets" not in st.session_state:
        st.session_state["pallets"] = []
    if "boxes" not in st.session_state:
        st.session_state["boxes"] = []
    if "config" not in st.session_state:
        # Crear configuraciones por defecto
        pallet_config = PalletConfig(
            max_width=120.0,
            max_length=100.0,
            max_height=200.0,
            max_weight=1000.0
        )
        conveyor_config = ConveyorConfig(
            interval_seconds=2.0,
            input_file="data/cajas_entrada.csv"
        )
        st.session_state["config"] = AppConfig(
            pallet=pallet_config,
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
    
    # Sidebar para configuración
    with st.sidebar:
        st.header("Configuración")
        
        # Crear un formulario para la configuración
        with st.form("config_form"):
            # Configuración del pallet
            st.subheader("Dimensiones del Pallet")
            max_width = st.number_input(
                "Ancho máximo (cm)", 
                value=st.session_state["config"].pallet.max_width, 
                min_value=1.0,
                step=5.0
            )
            max_length = st.number_input(
                "Largo máximo (cm)", 
                value=st.session_state["config"].pallet.max_length, 
                min_value=1.0,
                step=5.0
            )
            max_height = st.number_input(
                "Alto máximo (cm)", 
                value=st.session_state["config"].pallet.max_height, 
                min_value=1.0,
                step=5.0
            )
            max_weight = st.number_input(
                "Peso máximo (kg)", 
                value=st.session_state["config"].pallet.max_weight, 
                min_value=1.0,
                step=5.0
            )
            
            # Configuración de la cinta transportadora
            st.subheader("Cinta Transportadora")
            interval_seconds = st.number_input(
                "Intervalo entre cajas (segundos)", 
                value=st.session_state["config"].conveyor.interval_seconds, 
                min_value=0.1,
                step=0.5
            )
            
            # Selección del algoritmo de palletización
            st.subheader("Algoritmo de Palletización")
            algorithm = st.selectbox(
                "Seleccionar algoritmo",
                options=[
                    "First-Fit",
                    "Best-Fit Decreasing",
                    "First-Fit Decreasing",
                    "Guillotine",
                    "Best-Fit Lookahead"
                ],
                index=0
            )
            
            # Configuración específica para Best-Fit Lookahead
            if algorithm == "Best-Fit Lookahead":
                lookahead = st.number_input(
                    "Número de cajas a mirar adelante",
                    min_value=1,
                    max_value=10,
                    value=3,
                    step=1
                )
            
            # Obtener lista de archivos CSV en el directorio data
            data_files = [f for f in os.listdir("data") if f.endswith('.csv')]
            input_file = st.selectbox(
                "Archivo de entrada",
                options=data_files,
                index=data_files.index(st.session_state["config"].conveyor.input_file.split('/')[-1]) if st.session_state["config"].conveyor.input_file.split('/')[-1] in data_files else 0
            )
            input_file = f"data/{input_file}"  # Añadir el prefijo data/
            
            # Botón para aplicar la configuración
            if st.form_submit_button("Aplicar Configuración"):
                # Actualizar configuración
                pallet_config = PalletConfig(
                    max_width=max_width,
                    max_length=max_length,
                    max_height=max_height,
                    max_weight=max_weight
                )
                conveyor_config = ConveyorConfig(
                    interval_seconds=interval_seconds,
                    input_file=input_file
                )
                st.session_state["config"] = AppConfig(
                    pallet=pallet_config,
                    conveyor=conveyor_config
                )
                st.session_state["algorithm"] = algorithm
                if algorithm == "Best-Fit Lookahead":
                    st.session_state["lookahead"] = lookahead
                st.success("Configuración actualizada correctamente")
    
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
                        "🔄 Ángulo de rotación", 
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
        
        # Crear contenedor para las métricas del pallet actual
        metrics_container = st.empty()
        
        # Crear contenedor para la tabla de historial
        history_container = st.empty()
    
    with col2:
        st.header("🎮 Controles y Estado")
        
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
                        
                        # Crear y mostrar la caja actual
                        box = Box(
                            id=int(row['id']),
                            width=float(row['width']),
                            length=float(row['length']),
                            height=float(row['height']),
                            weight=float(row['weight'])
                        )
                        
                        # Actualizar información de la caja actual
                        current_box_info.markdown(f"""
                        ### 📦 Caja Actual
                        - **ID:** {box.id}
                        - **Dimensiones:** {box.width}x{box.length}x{box.height} cm
                        - **Peso:** {box.weight} kg
                        - **Volumen:** {box.volume():.1f} cm³
                        """)
                        
                        st.session_state["boxes"].append(box)
                        
                        # Realizar paletización según el algoritmo seleccionado
                        if st.session_state["algorithm"] == "First-Fit":
                            st.session_state["pallets"] = first_fit_palletization(
                                st.session_state["boxes"],
                                max_width=st.session_state["config"].pallet.max_width,
                                max_length=st.session_state["config"].pallet.max_length,
                                max_height=st.session_state["config"].pallet.max_height,
                                max_weight=st.session_state["config"].pallet.max_weight
                            )
                        elif st.session_state["algorithm"] == "Best-Fit Decreasing":
                            st.session_state["pallets"] = best_fit_decreasing_palletization(
                                st.session_state["boxes"],
                                max_width=st.session_state["config"].pallet.max_width,
                                max_length=st.session_state["config"].pallet.max_length,
                                max_height=st.session_state["config"].pallet.max_height,
                                max_weight=st.session_state["config"].pallet.max_weight
                            )
                        elif st.session_state["algorithm"] == "First-Fit Decreasing":
                            st.session_state["pallets"] = first_fit_decreasing_palletization(
                                st.session_state["boxes"],
                                max_width=st.session_state["config"].pallet.max_width,
                                max_length=st.session_state["config"].pallet.max_length,
                                max_height=st.session_state["config"].pallet.max_height,
                                max_weight=st.session_state["config"].pallet.max_weight
                            )
                        elif st.session_state["algorithm"] == "Guillotine":
                            st.session_state["pallets"] = guillotine_palletization(
                                st.session_state["boxes"],
                                max_width=st.session_state["config"].pallet.max_width,
                                max_length=st.session_state["config"].pallet.max_length,
                                max_height=st.session_state["config"].pallet.max_height,
                                max_weight=st.session_state["config"].pallet.max_weight
                            )
                        elif st.session_state["algorithm"] == "Best-Fit Lookahead":
                            st.session_state["pallets"] = best_fit_lookahead_palletization(
                                st.session_state["boxes"],
                                max_width=st.session_state["config"].pallet.max_width,
                                max_length=st.session_state["config"].pallet.max_length,
                                max_height=st.session_state["config"].pallet.max_height,
                                max_weight=st.session_state["config"].pallet.max_weight,
                                lookahead=st.session_state.get("lookahead", 3)
                            )
                        
                        # Actualizar visualización 3D
                        fig = visualize_pallets(st.session_state["pallets"], 
                                              rotation_angle=st.session_state["rotation_angle"])
                        visualization_container.pyplot(fig)
                        
                        # Actualizar métricas del pallet actual
                        if st.session_state["pallets"]:
                            metrics = calculate_pallet_metrics(st.session_state["pallets"][-1])
                            quality_score, quality_components = calculate_pallet_quality(st.session_state["pallets"][-1])
                            
                            # Crear tres columnas para las métricas
                            with metrics_container.container():
                                col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
                                
                                with col_metrics1:
                                    st.metric(
                                        "Peso del Pallet",
                                        f"{metrics['peso_utilizado']:.1f} kg",
                                        f"{metrics['porcentaje_peso']:.1f}% del máximo"
                                    )
                                
                                with col_metrics2:
                                    st.metric(
                                        "Volumen Utilizado",
                                        f"{metrics['volumen_utilizado']:.1f} cm³",
                                        f"{metrics['porcentaje_volumen']:.1f}% del total"
                                    )
                                
                                with col_metrics3:
                                    st.metric(
                                        "Altura Utilizada",
                                        f"{metrics['altura_utilizada']:.1f} cm",
                                        f"{metrics['porcentaje_altura']:.1f}% del máximo"
                                    )
                            
                            # Guardar en el historial
                            st.session_state["history"].append({
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "box_id": box.id,
                                "dimensions": f"{box.width}x{box.length}x{box.height}",
                                "weight": box.weight,
                                "metrics": metrics,
                                "quality_score": quality_score,
                                "quality_components": quality_components
                            })
                        
                        # Mostrar tabla de historial actualizada
                        with history_container.container():
                            st.subheader("Historial de Colocación")
                            st.dataframe(pd.DataFrame(st.session_state["history"]))
                            
                        # Esperar el intervalo configurado
                        time.sleep(st.session_state["config"].conveyor.interval_seconds)
                    
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
                    
                    # Mostrar resumen final con tarjetas
                    with st.container():
                        st.markdown("### 📊 Resumen Final")
                        col_summary1, col_summary2, col_summary3 = st.columns(3)
                        
                        with col_summary1:
                            st.metric(
                                "Pallets Utilizados",
                                len(st.session_state['pallets']),
                                "Total"
                            )
                        
                        with col_summary2:
                            st.metric(
                                "Cajas Totales",
                                len(st.session_state['boxes']),
                                "Procesadas"
                            )
                        
                        with col_summary3:
                            st.metric(
                                "Cajas por Pallet",
                                f"{len(st.session_state['boxes']) / len(st.session_state['pallets']):.1f}",
                                "Promedio"
                            )
                    
                    # Mostrar métricas de calidad al final de la simulación
                    if st.session_state["pallets"]:
                        quality_score, quality_components = calculate_pallet_quality(st.session_state["pallets"][-1])
                        with st.expander("📊 Métricas de Calidad del Pallet", expanded=False):
                            # Puntuación general
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
                                st.metric(
                                    "Utilización de la Altura",
                                    f"{quality_components['height_utilization']:.2f}",
                                    f"({quality_components['weights']['height']*100:.0f}% del total)"
                                )
                            
                            # Explicación actualizada de la métrica
                            st.markdown("""
                            #### 📝 Explicación de la Métrica
                            
                            La calidad del pallet se calcula considerando cuatro factores:
                            
                            1. **Utilización del Volumen** (40%):
                               - Calcula la proporción del volumen total del pallet que está siendo utilizado
                               - Se obtiene dividiendo el volumen total de las cajas entre el volumen máximo del pallet
                               - Valores altos indican mejor aprovechamiento del espacio
                            
                            2. **Distribución del Peso** (30%):
                               - Calcula el centro de masa del pallet
                               - Compara la posición del centro de masa con el centro ideal del pallet
                               - La puntuación es mejor cuanto más cerca esté el centro de masa del centro del pallet
                               - Valores altos indican mejor balance del peso
                            
                            3. **Estabilidad de la Carga** (20%):
                               - Verifica que cada caja tenga soporte adecuado
                               - Una caja tiene soporte si:
                                 - Está en el suelo (posición z = 0)
                                 - O hay otra caja debajo que la soporte completamente
                               - Penaliza con -0.1 por cada caja que no tenga soporte adecuado
                               - Valores altos indican mejor estabilidad
                            
                            4. **Utilización de la Altura** (10%):
                               - Calcula la proporción de la altura máxima del pallet que está siendo utilizada
                               - Se obtiene dividiendo la altura máxima alcanzada entre la altura máxima permitida
                               - Valores altos indican mejor aprovechamiento vertical
                            """)
                    
                except Exception as e:
                    st.error(f"Error al cargar el archivo: {str(e)}")
                    st.session_state["simulation_running"] = False
                    st.session_state["simulation_complete"] = False
        
        # Botón de descarga del PDF (fuera del bloque de simulación)
        if st.session_state["simulation_complete"] and st.session_state["history"]:
            st.markdown("---")
            st.markdown("### 📄 Generar Reporte")
            if st.button("📥 Generar Reporte PDF", type="primary"):
                with st.spinner("🔄 Generando reporte PDF..."):
                    pdf_buffer = generate_pdf_report(st.session_state["history"], st.session_state["pallets"])
                    st.download_button(
                        label="📥 Descargar Reporte PDF",
                        data=pdf_buffer,
                        file_name=f"palletization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf"
                    )

if __name__ == "__main__":
    main() 