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
from core.algorithms import first_fit_palletization
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
                st.success("Configuración actualizada correctamente")
    
    # Crear dos columnas principales
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Visualización en Tiempo Real")
        
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
                st.info("El control de rotación estará disponible cuando la simulación esté completa")
        
        # Crear contenedor para la visualización 3D
        visualization_container = st.empty()
        
        # Actualizar visualización si hay pallets
        if st.session_state["pallets"]:
            fig = visualize_pallets(st.session_state["pallets"], 
                                  rotation_angle=st.session_state["rotation_angle"])
            visualization_container.pyplot(fig)
        
        # Crear contenedor para las métricas del pallet actual
        metrics_container = st.empty()
    
    with col2:
        st.header("Controles y Estado")
        
        if not st.session_state["simulation_running"] and not st.session_state["simulation_complete"]:
            if st.button("Iniciar Simulación"):
                st.session_state["simulation_running"] = True
                st.session_state["pallets"] = []
                st.session_state["boxes"] = []
                st.session_state["history"] = []
                st.session_state["last_update_time"] = time.time()
                
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
                        ### Caja Actual
                        - **ID:** {box.id}
                        - **Dimensiones:** {box.width}x{box.length}x{box.height} cm
                        - **Peso:** {box.weight} kg
                        - **Volumen:** {box.volume():.1f} cm³
                        """)
                        
                        st.session_state["boxes"].append(box)
                        
                        # Realizar paletización
                        st.session_state["pallets"] = first_fit_palletization(
                            st.session_state["boxes"],
                            max_width=st.session_state["config"].pallet.max_width,
                            max_length=st.session_state["config"].pallet.max_length,
                            max_height=st.session_state["config"].pallet.max_height,
                            max_weight=st.session_state["config"].pallet.max_weight
                        )
                        
                        # Actualizar visualización 3D
                        fig = visualize_pallets(st.session_state["pallets"], 
                                              rotation_angle=st.session_state["rotation_angle"])
                        visualization_container.pyplot(fig)
                        
                        # Actualizar métricas del pallet actual
                        if st.session_state["pallets"]:
                            metrics = calculate_pallet_metrics(st.session_state["pallets"][-1])
                            metrics_container.markdown(f"""
                            ### Métricas del Pallet Actual
                            | Métrica | Valor | Porcentaje |
                            |---------|--------|------------|
                            | Peso | {metrics['peso_utilizado']:.1f} kg | {metrics['porcentaje_peso']:.1f}% |
                            | Volumen | {metrics['volumen_utilizado']:.1f} cm³ | {metrics['porcentaje_volumen']:.1f}% |
                            | Altura | {metrics['altura_utilizada']:.1f} cm | {metrics['porcentaje_altura']:.1f}% |
                            """)
                            
                            # Guardar en el historial
                            st.session_state["history"].append({
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "box_id": box.id,
                                "dimensions": f"{box.width}x{box.length}x{box.height}",
                                "weight": box.weight,
                                "metrics": metrics
                            })
                        
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
                            "Ángulo de rotación", 
                            0, 360, 
                            st.session_state["rotation_angle"],
                            key="rotation_slider"
                        )
                    
                    # Mostrar resumen final
                    st.markdown("### Resumen Final")
                    st.write(f"**Pallets utilizados:** {len(st.session_state['pallets'])}")
                    st.write(f"**Cajas totales:** {len(st.session_state['boxes'])}")
                    st.write(f"**Cajas por pallet:** {len(st.session_state['boxes']) / len(st.session_state['pallets']):.1f}")
                    
                    # Mostrar historial
                    st.markdown("### Historial de Actualizaciones")
                    history_df = pd.DataFrame(st.session_state["history"])
                    st.dataframe(history_df)
                    
                except Exception as e:
                    st.error(f"Error al cargar el archivo: {str(e)}")
                    st.session_state["simulation_running"] = False
                    st.session_state["simulation_complete"] = False
        
        # Mostrar resumen e historial si la simulación está completa
        if st.session_state["simulation_complete"]:
            st.markdown("### Resumen Final")
            st.write(f"**Pallets utilizados:** {len(st.session_state['pallets'])}")
            st.write(f"**Cajas totales:** {len(st.session_state['boxes'])}")
            st.write(f"**Cajas por pallet:** {len(st.session_state['boxes']) / len(st.session_state['pallets']):.1f}")
            
            st.markdown("### Historial de Actualizaciones")
            history_df = pd.DataFrame(st.session_state["history"])
            st.dataframe(history_df)
    
    # Botón de descarga del PDF (fuera del bloque de simulación)
    if st.session_state["simulation_complete"] and st.session_state["history"]:
        st.markdown("---")
        st.markdown("### Generar Reporte")
        if st.button("Generar Reporte PDF"):
            with st.spinner("Generando reporte PDF..."):
                pdf_buffer = generate_pdf_report(st.session_state["history"], st.session_state["pallets"])
                st.download_button(
                    label="Descargar Reporte PDF",
                    data=pdf_buffer,
                    file_name=f"palletization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf"
                )

if __name__ == "__main__":
    main() 