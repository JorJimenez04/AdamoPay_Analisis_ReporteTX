"""
Aplicación web para el sistema de análisis y reporte transaccional de AdamoPay
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import *
from src.characterization.base_characterization import caracterizar_cliente_gafi
from src.risk_analysis import analizar_riesgo_cliente

# Función para clasificar tipo de persona según tipo de identificación
def clasificar_tipo_persona(tipo_id):
    """Clasifica si es Persona Natural o Jurídica según el tipo de identificación"""
    if pd.isna(tipo_id):
        return 'Desconocido'
    
    tipo_str = str(tipo_id).strip().upper()
    
    # Personas Naturales: C, PA, CE (Cédula, Pasaporte, Cédula Extranjería)
    if tipo_str in ['C', 'PA', 'CE', 'CC', 'CEDULA']:
        return 'Natural'
    # Personas Jurídicas: N, NIT
    elif tipo_str in ['N', 'NIT']:
        return 'Jurídica'
    else:
        return 'Desconocido'

# Función para cargar datos desde Excel
@st.cache_data(ttl=60)  # Cache se invalida cada 60 segundos
def cargar_datos_clientes():
    """Carga todos los datos de clientes desde el archivo Excel"""
    try:
        ruta_excel = Path(__file__).parent / "data" / "Data_Clients&TX.xlsx"
        excel_file = pd.ExcelFile(ruta_excel)
        
        todos_datos = []
        clientes_info = {}
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(ruta_excel, sheet_name=sheet_name)
            df['CLIENTE'] = sheet_name
            todos_datos.append(df)
            clientes_info[sheet_name] = len(df)
        
        df_completo = pd.concat(todos_datos, ignore_index=True)
        
        # Convertir todas las columnas a string primero para evitar conflictos de tipo
        for col in df_completo.columns:
            if col not in ['FECHA', 'MONTO (COP)', 'COMISION ((MONTO TOT', 'SALDO (COP)']:
                df_completo[col] = df_completo[col].astype(str)
        
        # Limpiar y convertir columnas de fecha
        if 'FECHA' in df_completo.columns:
            df_completo['FECHA'] = pd.to_datetime(df_completo['FECHA'], errors='coerce')
        
        # Limpiar columnas de montos
        for col in ['MONTO (COP)', 'COMISION ((MONTO TOT', 'SALDO (COP)']:
            if col in df_completo.columns:
                df_completo[col] = pd.to_numeric(
                    df_completo[col].astype(str).str.replace(',', '').str.replace('$', '').str.strip(), 
                    errors='coerce'
                )
                df_completo[col] = df_completo[col].fillna(0)
        
        # Clasificar tipo de persona (Natural vs Jurídica)
        if 'TIPO DE IDENTIFICACION' in df_completo.columns:
            df_completo['TIPO_PERSONA'] = df_completo['TIPO DE IDENTIFICACION'].apply(clasificar_tipo_persona)
        else:
            df_completo['TIPO_PERSONA'] = 'Desconocido'
        
        return df_completo, clientes_info, excel_file.sheet_names
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return None, None, None

# Configuración de la página
st.set_page_config(
    page_title="AdamoPay - Análisis Transaccional",
    page_icon="💳",
    layout="wide"
)

# Título principal con logos
col1, col2, col3 = st.columns([2, 6, 2])

with col1:
    # Logo AdamoServices a la izquierda
    logo_path1 = Path(__file__).parent / "assets" / "LogoAdamoServices.png"
    st.image(str(logo_path1), width=120)

with col2:
    # Título centrado
    st.markdown("<h1 style='text-align: center;'>AdamoPay – Plataforma de Inteligencia Transaccional</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; font-size: 16px;'>Monitoreo, análisis y generación de reportes transaccionales</p>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: lightgray; font-size: 14px;'>Sistema de Análisis y Reporte Transaccional</p>", unsafe_allow_html=True)

with col3:
    # Logo AdamoPay a la derecha
    logo_path2 = Path(__file__).parent / "assets" / "Adamopay.png"
    st.image(str(logo_path2), width=180)

st.markdown("---")

# === CARGAR DATOS PRIMERO ===
df_completo, clientes_info, lista_clientes = cargar_datos_clientes()

# === SECCIÓN DE INFORMACIÓN GENERAL (Siempre visible) ===
if df_completo is not None and not df_completo.empty:
    st.markdown("## 🟦 Capa 1: Métricas del Negocio")
    st.caption("Indicadores objetivos de operación y comportamiento transaccional")
    
    st.markdown("### 📊 Vista General del Negocio")
    st.markdown("<p style='color: gray; margin-top: -10px;'>Resumen ejecutivo de clientes activos y métricas clave</p>", unsafe_allow_html=True)
    
    # Métricas generales del negocio
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    # Filtrar solo transacciones PAGADAS y VALIDADAS
    if 'ESTADO' in df_completo.columns:
        df_relevantes = df_completo[df_completo['ESTADO'].str.lower().str.contains('pagado|validado', na=False)].copy()
    else:
        df_relevantes = df_completo.copy()
    
    total_transacciones_global = len(df_completo)
    tx_relevantes_global = len(df_relevantes)
    monto_total_global = df_relevantes['MONTO (COP)'].sum() if 'MONTO (COP)' in df_relevantes.columns else 0
    
    tasa_exito_global = (tx_relevantes_global / total_transacciones_global * 100) if total_transacciones_global > 0 else 0
    
    promedio_tx_global = df_relevantes['MONTO (COP)'].mean() if 'MONTO (COP)' in df_relevantes.columns else 0
    
    # Calcular métricas por tipo de persona
    tx_pn = 0
    tx_pj = 0
    monto_pn = 0
    monto_pj = 0
    
    if 'TIPO_PERSONA' in df_relevantes.columns:
        df_pn = df_relevantes[df_relevantes['TIPO_PERSONA'] == 'Natural']
        df_pj = df_relevantes[df_relevantes['TIPO_PERSONA'] == 'Jurídica']
        
        tx_pn = len(df_pn)
        tx_pj = len(df_pj)
        monto_pn = df_pn['MONTO (COP)'].sum() if len(df_pn) > 0 and 'MONTO (COP)' in df_pn.columns else 0
        monto_pj = df_pj['MONTO (COP)'].sum() if len(df_pj) > 0 and 'MONTO (COP)' in df_pj.columns else 0
    
    with col1:
        st.metric("👥 Clientes Activos", f"{len(lista_clientes)}", delta="Operando")
    with col2:
        st.metric("💳 TX Pagadas/Validadas", f"{tx_relevantes_global:,}", delta=f"De {total_transacciones_global:,} totales")
    with col3:
        st.metric("💰 Volumen Efectivo", f"$ {monto_total_global:,.0f} COP", delta=f"Promedio: $ {promedio_tx_global:,.0f} COP")
    with col4:
        st.metric("✅ Tasa Efectividad", f"{tasa_exito_global:.1f}%", delta="Pagadas/Validadas")
    with col5:
        st.metric("👤 Personas Naturales", f"{tx_pn:,} TX", delta=f"$ {monto_pn:,.0f} COP")
    with col6:
        st.metric("🏢 Personas Jurídicas", f"{tx_pj:,} TX", delta=f"$ {monto_pj:,.0f} COP")
    
    st.markdown("---")
    
    # === TARJETAS SIMPLES POR CLIENTE ===
    st.markdown("### 👥 Resumen por Cliente")
    st.markdown("<p style='color: gray; margin-top: -10px;'>Vista rápida de volúmenes y estados por cliente</p>", unsafe_allow_html=True)
    
    # Crear tarjetas en filas de 2 columnas con espacio entre ellas
    for i in range(0, len(lista_clientes), 2):
        cols = st.columns(2, gap="large")  # Espacio grande entre columnas
        
        for idx, col in enumerate(cols):
            if i + idx < len(lista_clientes):
                cliente = lista_clientes[i + idx]
                df_cliente = df_completo[df_completo['CLIENTE'] == cliente]
                
                with col:
                    # Usar un container para agrupar todo el contenido
                    container = st.container(border=True)
                    
                    with container:
                        # Filtrar solo transacciones PAGADAS y VALIDADAS para métricas principales
                        if 'ESTADO' in df_cliente.columns:
                            df_cliente_efectivo = df_cliente[df_cliente['ESTADO'].str.lower().str.contains('pagado|validado', na=False)].copy()
                        else:
                            df_cliente_efectivo = df_cliente.copy()
                        
                        # Calcular métricas simples (solo TX efectivas)
                        total_tx = len(df_cliente_efectivo)
                        total_monto = df_cliente_efectivo['MONTO (COP)'].sum() if 'MONTO (COP)' in df_cliente_efectivo.columns else 0
                        
                        # Calcular tipos de transacción para mostrar
                        tipos_dict = {}
                        if 'TIPO DE TRA' in df_cliente.columns:
                            tipos_unicos = df_cliente['TIPO DE TRA'].unique()
                            for tipo in tipos_unicos:
                                tipo_norm = str(tipo).lower()
                                count = len(df_cliente[df_cliente['TIPO DE TRA'] == tipo])
                                if 'fondo' in tipo_norm or 'fondeo' in tipo_norm:
                                    tipos_dict['Fondeo'] = tipos_dict.get('Fondeo', 0) + count
                                elif 'credito' in tipo_norm or 'crédito' in tipo_norm:
                                    tipos_dict['Crédito'] = tipos_dict.get('Crédito', 0) + count
                                elif 'debito' in tipo_norm or 'débito' in tipo_norm:
                                    tipos_dict['Débito'] = tipos_dict.get('Débito', 0) + count
                                else:
                                    tipos_dict['Otro'] = tipos_dict.get('Otro', 0) + count
                        
                        # Calcular beneficiarios (PN vs PJ)
                        pn_count = 0
                        pj_count = 0
                        if 'TIPO_PERSONA' in df_cliente.columns:
                            pn_count = len(df_cliente[df_cliente['TIPO_PERSONA'] == 'Natural'])
                            pj_count = len(df_cliente[df_cliente['TIPO_PERSONA'] == 'Jurídica'])
                        
                        # Métricas por estado
                        metricas_estado = {}
                        if 'ESTADO' in df_cliente.columns:
                            for estado in ['Pagado', 'Validado', 'Retornado', 'Rechazado', 'Aprobado']:
                                df_estado = df_cliente[df_cliente['ESTADO'].str.lower() == estado.lower()]
                                if len(df_estado) > 0:
                                    metricas_estado[estado] = {
                                        'tx': len(df_estado),
                                        'monto': df_estado['MONTO (COP)'].sum() if 'MONTO (COP)' in df_estado.columns else 0
                                    }
                        
                        # Card del cliente (HEADER)
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                    padding: 18px; 
                                    border-radius: 10px; 
                                    margin-bottom: 20px;
                                    box-shadow: 0 3px 10px rgba(102,126,234,0.3);'>
                            <h3 style='margin: 0; color: white; font-size: 22px; font-weight: 600;'>🏢 {cliente}</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # MÉTRICAS PRINCIPALES (máximo 3)
                        promedio_tx = total_monto / total_tx if total_tx > 0 else 0
                        metric_cols = st.columns(3)
                        with metric_cols[0]:
                            st.metric("📊 Transacciones", f"{total_tx:,}")
                        with metric_cols[1]:
                            st.metric("💰 Volumen Total", f"$ {total_monto:,.0f} COP")
                        with metric_cols[2]:
                            st.metric("📈 Promedio TX", f"$ {promedio_tx:,.0f} COP")
                        
                        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
                        
                        # EXPANDER PARA DETALLES OPERATIVOS
                        with st.expander("📊 Ver detalle operativo"):
                            
                            # SECCIÓN: TIPOS DE TRANSACCIÓN
                            if tipos_dict:
                                st.markdown("**📋 Tipos de Transacción**")
                                tipos_cols = st.columns(len(tipos_dict))
                                iconos_mini = {'Fondeo': '💰', 'Crédito': '💳', 'Débito': '🏧', 'Otro': '📊'}
                                for idx_tipo, (tipo, count) in enumerate(tipos_dict.items()):
                                    with tipos_cols[idx_tipo]:
                                        st.metric(
                                            label=f"{iconos_mini.get(tipo, '📊')} {tipo}",
                                            value=f"{count:,}"
                                        )
                                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
                            
                            # SECCIÓN: BENEFICIARIOS
                            if pn_count > 0 or pj_count > 0:
                                st.markdown("**👥 Beneficiarios**")
                                benef_cols = st.columns(2)
                                
                                if pn_count > 0:
                                    with benef_cols[0]:
                                        pn_pct = (pn_count / total_tx * 100) if total_tx > 0 else 0
                                        st.metric(
                                            label="👤 Personas Naturales",
                                            value=f"{pn_count:,}",
                                            delta=f"{pn_pct:.1f}%"
                                        )
                                
                                if pj_count > 0:
                                    with benef_cols[1]:
                                        pj_pct = (pj_count / total_tx * 100) if total_tx > 0 else 0
                                        st.metric(
                                            label="🏢 Personas Jurídicas",
                                            value=f"{pj_count:,}",
                                            delta=f"{pj_pct:.1f}%"
                                        )
                                st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
                            
                            # SECCIÓN: ESTADOS
                            if metricas_estado:
                                st.markdown("**📋 Estados de Transacciones**")
                                # Colores con enfoque en compliance: estados críticos más visibles
                                colores_estado = {
                                    'Pagado': '#9E9E9E',      # Gris - menos relevante para compliance
                                    'Validado': '#FF6B35',    # Naranja fuerte - requiere atención
                                    'Retornado': '#FF1744',   # Rojo intenso - crítico
                                    'Rechazado': '#D50000',   # Rojo oscuro - muy crítico
                                    'Aprobado': '#757575'     # Gris oscuro - neutral
                                }
                                
                                emojis_estado = {
                                    'Pagado': '✅',
                                    'Validado': '⚠️',         # Cambio a advertencia
                                    'Retornado': '🔴',        # Más crítico
                                    'Rechazado': '❌',
                                    'Aprobado': '👍'
                                }
                                
                                for estado, datos in metricas_estado.items():
                                    color = colores_estado.get(estado, '#757575')
                                    emoji = emojis_estado.get(estado, '📊')
                                    porcentaje_tx = (datos['tx'] / total_tx * 100) if total_tx > 0 else 0
                                    
                                    col1, col2, col3 = st.columns([2, 2, 3])
                                    with col1:
                                        st.markdown(f"**{emoji} {estado}**")
                                    with col2:
                                        st.caption(f"{datos['tx']:,} TX ({porcentaje_tx:.1f}%)")
                                    with col3:
                                        st.caption(f"$ {datos['monto']:,.0f} COP")
                    
                    # Cerrar contenedor visual de la tarjeta
                    st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)
        
        # Separador visual entre filas de tarjetas
        if i + 2 < len(lista_clientes):  # Si no es la última fila
            st.markdown("""
            <div style='border-bottom: 2px dashed #ccc; 
                        margin: 30px 0 40px 0; 
                        opacity: 0.5;'>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")

else:
    st.warning("⚠️ No se pudieron cargar los datos. Verifica que el archivo 'Data_Clients&TX.xlsx' esté en la carpeta 'data/'")

# === CONTENIDO PRINCIPAL - DASHBOARD DETALLADO ===
st.header("📊 Dashboard Detallado - Análisis Completo")

if df_completo is not None and not df_completo.empty:
    
    # === BOTONES DE EXPORTACIÓN ===
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Exportar a Excel
        @st.cache_data
        def convertir_a_excel(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Datos_Completos', index=False)
                # Agregar hoja de resumen
                resumen = pd.DataFrame({
                    'Métrica': ['Total Transacciones', 'TX Efectivas', 'Volumen Total', 'Comisiones'],
                    'Valor': [
                        len(df),
                        len(df[df['ESTADO'].str.lower().str.contains('pagado|validado', na=False)]) if 'ESTADO' in df.columns else 0,
                        df['MONTO (COP)'].sum() if 'MONTO (COP)' in df.columns else 0,
                        df['COMISION ((MONTO TOT'].sum() if 'COMISION ((MONTO TOT' in df.columns else 0
                    ]
                })
                resumen.to_excel(writer, sheet_name='Resumen', index=False)
            return output.getvalue()
        
        excel_data = convertir_a_excel(df_completo)
        st.download_button(
            label="📊 Excel",
            data=excel_data,
            file_name=f"AdamoPay_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        # Exportar a CSV
        @st.cache_data
        def convertir_a_csv(df):
            return df.to_csv(index=False).encode('utf-8')
        
        csv_data = convertir_a_csv(df_completo)
        st.download_button(
            label="📄 CSV",
            data=csv_data,
            file_name=f"AdamoPay_Data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col3:
        # Exportar solo TX efectivas
        if 'ESTADO' in df_completo.columns:
            df_efectivas_export = df_completo[df_completo['ESTADO'].str.lower().str.contains('pagado|validado', na=False)]
            csv_efectivas = convertir_a_csv(df_efectivas_export)
            st.download_button(
                label="✅ TX Efectivas",
                data=csv_efectivas,
                file_name=f"AdamoPay_Efectivas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    with col4:
        # Botón de info sobre exportación
        with st.popover("ℹ️ Info"):
            st.markdown("""
            **Opciones de Exportación:**
            - 📊 **Excel**: Datos completos + resumen
            - 📄 **CSV**: Todos los registros
            - ✅ **TX Efectivas**: Solo pagadas/validadas
            """)
    
    st.markdown("---")
    
    # === INFORMACIÓN GENERAL DE CLIENTES ===
    st.markdown("### 👥 Información General de Clientes")
    st.markdown("#### 🟦 Capa 1: Datos Transaccionales")
    st.caption("Métricas operativas y comportamiento del cliente")
    
    # Crear tabs para cada cliente
    tabs = st.tabs([f"📋 {cliente}" for cliente in lista_clientes])
    
    for idx, cliente in enumerate(lista_clientes):
        with tabs[idx]:
            df_cliente = df_completo[df_completo['CLIENTE'] == cliente]
            
            # Filtrar TX pagadas y validadas para este cliente
            if 'ESTADO' in df_cliente.columns:
                df_cliente_efectivo = df_cliente[df_cliente['ESTADO'].str.lower().str.contains('pagado|validado', na=False)].copy()
            else:
                df_cliente_efectivo = df_cliente.copy()
            
            # Calcular métricas del cliente
            total_tx_cliente = len(df_cliente)
            tx_efectivas_cliente = len(df_cliente_efectivo)
            monto_total_cliente = df_cliente_efectivo['MONTO (COP)'].sum() if 'MONTO (COP)' in df_cliente_efectivo.columns else 0
            monto_promedio_cliente = df_cliente_efectivo['MONTO (COP)'].mean() if 'MONTO (COP)' in df_cliente_efectivo.columns else 0
            
            tasa_exito_cliente = (tx_efectivas_cliente / total_tx_cliente * 100) if total_tx_cliente > 0 else 0
            
            if 'FECHA' in df_cliente.columns:
                primera_tx = df_cliente['FECHA'].min()
                ultima_tx = df_cliente['FECHA'].max()
                dias_activo = (ultima_tx - primera_tx).days if pd.notna(primera_tx) and pd.notna(ultima_tx) else 0
            else:
                primera_tx = None
                ultima_tx = None
                dias_activo = 0
            
            # CARD DE INFORMACIÓN PRINCIPAL
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                <h2 style='margin: 0; font-size: 28px;'>🏢 {cliente}</h2>
                <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;'>
                    Cliente Activo desde {primera_tx.strftime('%d/%m/%Y') if pd.notna(primera_tx) else 'N/A'}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # MÉTRICAS EN CARDS
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 15px; border-radius: 10px; 
                            border-left: 4px solid #4CAF50; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <p style='margin: 0; color: #666; font-size: 12px;'>📊 TX Efectivas</p>
                    <h3 style='margin: 5px 0; color: #2c3e50; font-size: 24px;'>{tx_efectivas_cliente:,}</h3>
                    <p style='margin: 0; color: #4CAF50; font-size: 11px;'>De {total_tx_cliente:,} totales</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 15px; border-radius: 10px; 
                            border-left: 4px solid #2196F3; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <p style='margin: 0; color: #666; font-size: 12px;'>💰 Monto Total</p>
                    <h3 style='margin: 5px 0; color: #2c3e50; font-size: 24px;'>$ {monto_total_cliente:,.0f} COP</h3>
                    <p style='margin: 0; color: #2196F3; font-size: 11px;'>Transaccionado</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 15px; border-radius: 10px; 
                            border-left: 4px solid #FF9800; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <p style='margin: 0; color: #666; font-size: 12px;'>📈 Promedio TX</p>
                    <h3 style='margin: 5px 0; color: #2c3e50; font-size: 24px;'>$ {monto_promedio_cliente:,.0f} COP</h3>
                    <p style='margin: 0; color: #FF9800; font-size: 11px;'>Por transacción</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                color_exito = '#4CAF50' if tasa_exito_cliente >= 90 else '#FF9800' if tasa_exito_cliente >= 70 else '#f44336'
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 15px; border-radius: 10px; 
                            border-left: 4px solid {color_exito}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <p style='margin: 0; color: #666; font-size: 12px;'>✅ Efectividad</p>
                    <h3 style='margin: 5px 0; color: #2c3e50; font-size: 24px;'>{tasa_exito_cliente:.1f}%</h3>
                    <p style='margin: 0; color: {color_exito}; font-size: 11px;'>
                        Pagadas+Validadas
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col5:
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 15px; border-radius: 10px; 
                            border-left: 4px solid #9C27B0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <p style='margin: 0; color: #666; font-size: 12px;'>📅 Días Activo</p>
                    <h3 style='margin: 5px 0; color: #2c3e50; font-size: 24px;'>{dias_activo}</h3>
                    <p style='margin: 0; color: #9C27B0; font-size: 11px;'>
                        Última: {ultima_tx.strftime('%d/%m/%Y') if pd.notna(ultima_tx) else 'N/A'}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # INFORMACIÓN DETALLADA EN COLUMNAS
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Resumen de Actividad")
                
                if 'TIPO DE TRA' in df_cliente_efectivo.columns:
                    tipos_tx = df_cliente_efectivo['TIPO DE TRA'].value_counts()
                    st.markdown("**Tipos de Transacciones (Efectivas):**")
                    for tipo, cantidad in tipos_tx.items():
                        st.write(f"• {tipo}: {cantidad:,}")
                
                st.markdown("---")
                
                if 'ESTADO' in df_cliente.columns:
                    estados = df_cliente['ESTADO'].value_counts()
                    st.markdown("**Estados de Transacciones:**")
                    for estado, cantidad in estados.items():
                        st.write(f"• {estado}: {cantidad:,}")
            
            with col2:
                st.markdown("#### 💳 Análisis Financiero")
                
                if 'MONTO (COP)' in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                    monto_min = df_cliente_efectivo['MONTO (COP)'].min()
                    monto_max = df_cliente_efectivo['MONTO (COP)'].max()
                    monto_mediana = df_cliente_efectivo['MONTO (COP)'].median()
                    
                    st.write(f"**Monto Mínimo:** $ {monto_min:,.0f} COP")
                    st.write(f"**Monto Mediana:** $ {monto_mediana:,.0f} COP")
                    st.write(f"**Monto Máximo:** $ {monto_max:,.0f} COP")
                
                st.markdown("---")
                
                if 'COMISION ((MONTO TOT' in df_cliente_efectivo.columns:
                    comision_total = df_cliente_efectivo['COMISION ((MONTO TOT'].sum()
                    comision_promedio = df_cliente_efectivo['COMISION ((MONTO TOT'].mean()
                    
                    st.write(f"**Comisión Total:** $ {comision_total:,.0f} COP")
                    st.write(f"**Comisión Promedio:** $ {comision_promedio:,.0f} COP")
            
            # Tabla de transacciones recientes
            st.markdown("---")
            st.markdown("#### 📋 Últimas 50 Transacciones")
            st.dataframe(df_cliente.head(50), use_container_width=True, height=300)
            
            # === TOP BENEFICIARIOS Y BANCOS (GRÁFICOS INTERACTIVOS) ===
            st.markdown("---")
            st.markdown("#### 🎯 Análisis de Participación")
            st.markdown("<p style='color: gray; margin-top: -10px;'>Beneficiarios y entidades bancarias con mayor actividad</p>", unsafe_allow_html=True)
            
            # Buscar columnas de beneficiario
            columnas_beneficiario = [col for col in df_cliente_efectivo.columns if 'BENEFICIARIO' in col.upper() or 'NOMBRE' in col.upper()]
            columna_beneficiario = None
            
            # Priorizar columnas que contengan BENEFICIARIO
            for col in columnas_beneficiario:
                if 'BENEFICIARIO' in col.upper() and 'NOMBRE' in col.upper():
                    columna_beneficiario = col
                    break
            
            if not columna_beneficiario and columnas_beneficiario:
                columna_beneficiario = columnas_beneficiario[0]
            
            if columna_beneficiario and columna_beneficiario in df_cliente_efectivo.columns:
                # Preparar datos de beneficiarios
                df_beneficiarios_full = df_cliente_efectivo.groupby(columna_beneficiario).agg({
                    'MONTO (COP)': ['count', 'sum', 'mean']
                }).reset_index()
                
                df_beneficiarios_full.columns = ['Beneficiario', 'TX', 'Monto Total', 'Monto Promedio']
                df_beneficiarios_full['% Participación'] = (df_beneficiarios_full['Monto Total'] / monto_total_cliente * 100).round(2)
                
                # Agregar tipo de persona
                if 'TIPO_PERSONA' in df_cliente_efectivo.columns:
                    tipo_persona_map = df_cliente_efectivo.groupby(columna_beneficiario)['TIPO_PERSONA'].first()
                    df_beneficiarios_full['Tipo'] = df_beneficiarios_full['Beneficiario'].map(tipo_persona_map)
                else:
                    df_beneficiarios_full['Tipo'] = 'Desconocido'
                
                # Separar por tipo
                df_pn = df_beneficiarios_full[df_beneficiarios_full['Tipo'] == 'Natural'].copy()
                df_pj = df_beneficiarios_full[df_beneficiarios_full['Tipo'] == 'Jurídica'].copy()
                
                # === PERSONAS NATURALES ===
                st.markdown("##### 👤 Personas Naturales")
                
                if len(df_pn) > 0:
                    df_pn_top = df_pn.sort_values('Monto Total', ascending=True).tail(10)
                    df_pn_top['Beneficiario Display'] = df_pn_top['Beneficiario'].apply(
                        lambda x: f"👤 {str(x)[:40]}{'...' if len(str(x)) > 40 else ''}"
                    )
                    
                    # Gráfico PN con colores profesionales azul/cyan
                    fig_pn = px.bar(
                        df_pn_top,
                        y='Beneficiario Display',
                        x='Monto Total',
                        orientation='h',
                        text='TX',
                        color='Monto Total',
                        color_continuous_scale=[[0, '#E3F2FD'], [0.3, '#90CAF9'], [0.6, '#42A5F5'], [1, '#1565C0']],
                        labels={
                            'Monto Total': 'Volumen Total (COP)',
                            'Beneficiario Display': ''
                        },
                        hover_data={
                            'TX': True,
                            'Monto Promedio': ':,.0f',
                            '% Participación': ':.2f',
                            'Monto Total': ':,.0f',
                            'Beneficiario Display': False
                        }
                    )
                    
                    fig_pn.update_traces(
                        texttemplate='<b>%{text} TX</b>',
                        textposition='outside',
                        textfont_size=10,
                        textfont_color='#1565C0',
                        marker_line_color='#0D47A1',
                        marker_line_width=1
                    )
                    
                    fig_pn.update_layout(
                        height=400,
                        showlegend=False,
                        xaxis_title="Volumen Total (COP)",
                        yaxis_title="",
                        margin=dict(l=10, r=10, t=10, b=10),
                        font=dict(size=11, color='#37474F'),
                        xaxis=dict(
                            tickformat='$ ,.0f COP',
                            gridcolor='rgba(66,165,245,0.15)',
                            showgrid=True
                        ),
                        yaxis=dict(
                            showgrid=False
                        ),
                        plot_bgcolor='rgba(227,242,253,0.15)',
                        paper_bgcolor='white',
                        coloraxis_showscale=False
                    )
                    
                    st.plotly_chart(fig_pn, use_container_width=True)
                    
                    # Métricas PN
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("👥 Total PN", f"{len(df_pn):,}", "beneficiarios")
                    with col_b:
                        volumen_pn = df_pn['Monto Total'].sum()
                        st.metric("💰 Volumen PN", f"$ {volumen_pn:,.0f} COP")
                    with col_c:
                        top3_pn = df_pn_top.tail(3)['Monto Total'].sum()
                        concentracion_pn = (top3_pn / volumen_pn * 100) if volumen_pn > 0 else 0
                        st.metric("🥇 Top 3", f"{concentracion_pn:.1f}%", "concentración")
                    with col_d:
                        if concentracion_pn > 70:
                            st.error("⚠️ Alta")
                        elif concentracion_pn > 50:
                            st.warning("⚡ Moderada")
                        else:
                            st.success("✅ Diversificado")
                else:
                    st.info("📊 No hay personas naturales en los datos")
                
                st.markdown("<div style='margin: 30px 0;'></div>", unsafe_allow_html=True)
                
                # === PERSONAS JURÍDICAS ===
                st.markdown("##### 🏢 Personas Jurídicas")
                
                if len(df_pj) > 0:
                    df_pj_top = df_pj.sort_values('Monto Total', ascending=True).tail(10)
                    df_pj_top['Beneficiario Display'] = df_pj_top['Beneficiario'].apply(
                        lambda x: f"🏢 {str(x)[:40]}{'...' if len(str(x)) > 40 else ''}"
                    )
                    
                    # Gráfico PJ con colores profesionales naranja/ámbar
                    fig_pj = px.bar(
                        df_pj_top,
                        y='Beneficiario Display',
                        x='Monto Total',
                        orientation='h',
                        text='TX',
                        color='Monto Total',
                        color_continuous_scale=[[0, '#FFF3E0'], [0.3, '#FFB74D'], [0.6, '#FF9800'], [1, '#E65100']],
                        labels={
                            'Monto Total': 'Volumen Total (COP)',
                            'Beneficiario Display': ''
                        },
                        hover_data={
                            'TX': True,
                            'Monto Promedio': ':,.0f',
                            '% Participación': ':.2f',
                            'Monto Total': ':,.0f',
                            'Beneficiario Display': False
                        }
                    )
                    
                    fig_pj.update_traces(
                        texttemplate='<b>%{text} TX</b>',
                        textposition='outside',
                        textfont_size=10,
                        textfont_color='#E65100',
                        marker_line_color='#BF360C',
                        marker_line_width=1
                    )
                    
                    fig_pj.update_layout(
                        height=400,
                        showlegend=False,
                        xaxis_title="Volumen Total (COP)",
                        yaxis_title="",
                        margin=dict(l=10, r=10, t=10, b=10),
                        font=dict(size=11, color='#37474F'),
                        xaxis=dict(
                            tickformat='$ ,.0f COP',
                            gridcolor='rgba(255,152,0,0.15)',
                            showgrid=True
                        ),
                        yaxis=dict(
                            showgrid=False
                        ),
                        plot_bgcolor='rgba(255,243,224,0.15)',
                        paper_bgcolor='white',
                        coloraxis_showscale=False
                    )
                    
                    st.plotly_chart(fig_pj, use_container_width=True)
                    
                    # Métricas PJ
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.metric("🏢 Total PJ", f"{len(df_pj):,}", "beneficiarios")
                    with col_b:
                        volumen_pj = df_pj['Monto Total'].sum()
                        st.metric("💰 Volumen PJ", f"$ {volumen_pj:,.0f} COP")
                    with col_c:
                        top3_pj = df_pj_top.tail(3)['Monto Total'].sum()
                        concentracion_pj = (top3_pj / volumen_pj * 100) if volumen_pj > 0 else 0
                        st.metric("🥇 Top 3", f"{concentracion_pj:.1f}%", "concentración")
                    with col_d:
                        if concentracion_pj > 70:
                            st.error("⚠️ Alta")
                        elif concentracion_pj > 50:
                            st.warning("⚡ Moderada")
                        else:
                            st.success("✅ Diversificado")
                else:
                    st.info("📊 No hay personas jurídicas en los datos")
            else:
                st.info("📊 No se encontró información de beneficiarios en los datos")
            
            st.markdown("<div style='margin: 40px 0;'></div>", unsafe_allow_html=True)
            st.markdown("<div style='margin: 40px 0;'></div>", unsafe_allow_html=True)
            
            # === TOP BANCOS ===
            st.markdown("##### 🏦 Top Bancos por Volumen")
            
            # Buscar columnas de banco
            columnas_banco = [col for col in df_cliente_efectivo.columns if 'BANCO' in col.upper()]
            columna_banco = None
            
            # Priorizar columnas que contengan BANCO BENEFICIARIO o similar
            for col in columnas_banco:
                if 'BENEFICIARIO' in col.upper() or 'DESTINO' in col.upper():
                    columna_banco = col
                    break
            
            if not columna_banco and columnas_banco:
                columna_banco = columnas_banco[0]
            
            if columna_banco and columna_banco in df_cliente_efectivo.columns:
                # Agrupar por banco
                df_bancos = df_cliente_efectivo.groupby(columna_banco).agg({
                    'MONTO (COP)': ['count', 'sum', 'mean']
                }).reset_index()
                
                df_bancos.columns = ['Banco', 'TX', 'Monto Total', 'Monto Promedio']
                df_bancos['% Participación'] = (df_bancos['Monto Total'] / monto_total_cliente * 100).round(2)
                
                # Formatear nombre del banco
                df_bancos['Banco Display'] = df_bancos['Banco'].apply(
                    lambda x: f"🏦 {str(x)[:40]}{'...' if len(str(x)) > 40 else ''}"
                )
                
                # Ordenar y tomar top 10
                df_bancos = df_bancos.sort_values('Monto Total', ascending=True).tail(10)
                
                # Crear gráfico de barras horizontales con colores profesionales verde/teal
                fig_bancos = px.bar(
                    df_bancos,
                    y='Banco Display',
                    x='Monto Total',
                    orientation='h',
                    text='TX',
                    color='Monto Total',
                    color_continuous_scale=[[0, '#E0F2F1'], [0.3, '#4DB6AC'], [0.6, '#00897B'], [1, '#004D40']],
                    labels={
                        'Monto Total': 'Volumen Total (COP)',
                        'Banco Display': ''
                    },
                    hover_data={
                        'TX': True,
                        'Monto Promedio': ':,.0f',
                        '% Participación': ':.2f',
                        'Monto Total': ':,.0f',
                        'Banco Display': False
                    }
                )
                
                fig_bancos.update_traces(
                    texttemplate='<b>%{text} TX</b>',
                    textposition='outside',
                    textfont_size=10,
                    textfont_color='#004D40',
                    marker_line_color='#00251A',
                    marker_line_width=1
                )
                
                fig_bancos.update_layout(
                    height=450,
                    showlegend=False,
                    xaxis_title="Volumen Total (COP)",
                    yaxis_title="",
                    margin=dict(l=10, r=10, t=10, b=10),
                    font=dict(size=11, color='#37474F'),
                    xaxis=dict(
                        tickformat='$ ,.0f COP',
                        gridcolor='rgba(0,137,123,0.15)',
                        showgrid=True
                    ),
                    yaxis=dict(
                        showgrid=False
                    ),
                    plot_bgcolor='rgba(224,242,241,0.15)',
                    paper_bgcolor='white',
                    coloraxis_showscale=False
                )
                
                st.plotly_chart(fig_bancos, use_container_width=True)
                
                # Métricas resumen bancos
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.metric("🏦 Total Bancos", f"{len(df_bancos):,}", "entidades")
                with col_b:
                    volumen_bancos = df_bancos['Monto Total'].sum()
                    st.metric("💰 Volumen", f"$ {volumen_bancos:,.0f} COP")
                with col_c:
                    top3_bancos = df_bancos.tail(3)['Monto Total'].sum()
                    concentracion_bancos = (top3_bancos / volumen_bancos * 100) if volumen_bancos > 0 else 0
                    st.metric("🥇 Top 3", f"{concentracion_bancos:.1f}%", "concentración")
                with col_d:
                    if concentracion_bancos > 70:
                        st.error("⚠️ Alta")
                    elif concentracion_bancos > 50:
                        st.warning("⚡ Moderada")
                    else:
                        st.success("✅ Diversificado")
            else:
                st.info("🏦 No se encontró información de bancos en los datos")
            
            # 🆕 ANÁLISIS DE RIESGO INTEGRAL
            st.markdown("---")
            st.markdown("## 🟥 Capa 2: Evaluación de Riesgo y Cumplimiento")
            st.caption("Interpretación regulatoria y señales de riesgo derivadas del comportamiento")
            
            st.markdown("### 🎯 Análisis de Riesgo Integral")
            st.markdown("<p style='color: gray; margin-top: -10px;'>Sistema completo de evaluación multicapa (GAFI + UIAF + Operativo)</p>", unsafe_allow_html=True)
            
            # Obtener perfil GAFI para pasar al análisis de riesgo
            perfil_gafi = caracterizar_cliente_gafi(df_cliente)
            
            # Ejecutar análisis de riesgo integral
            analisis_riesgo = analizar_riesgo_cliente(df_cliente, perfil_gafi, cliente)
            
            # === SCORING INTEGRAL ===
            st.markdown("### 📊 Scoring de Riesgo")
            
            col1, col2, col3, col4 = st.columns(4)
            
            scoring = analisis_riesgo['scoring']
            
            with col1:
                st.metric(
                    "Score Total",
                    f"{scoring['score_total']}/100",
                    delta=None
                )
            with col2:
                st.metric(
                    "Score GAFI",
                    f"{scoring['score_gafi']}/100",
                    delta="40% peso"
                )
            with col3:
                st.metric(
                    "Score UIAF",
                    f"{scoring['score_uiaf']}/100",
                    delta="35% peso"
                )
            with col4:
                st.metric(
                    "Score Operativo",
                    f"{scoring['score_operativo']}/100",
                    delta="25% peso"
                )
            
            # Badge de nivel de riesgo
            nivel = scoring['nivel_riesgo']
            colores_nivel = {
                'Bajo': '#4CAF50',
                'Medio': '#FF9800',
                'Alto': '#f44336',
                'Crítico': '#9C27B0',
                'No Evaluado': '#757575'
            }
            emojis_nivel = {
                'Bajo': '✅',
                'Medio': '⚠️',
                'Alto': '🚨',
                'Crítico': '🔥',
                'No Evaluado': '❓'
            }
            
            st.markdown(f"""
            <div style='background: {colores_nivel.get(nivel, "#757575")}; 
                        padding: 20px; 
                        border-radius: 10px; 
                        text-align: center;
                        margin: 20px 0;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);'>
                <h2 style='margin: 0; color: white; font-size: 28px;'>{emojis_nivel.get(nivel, "❓")} Nivel de Riesgo: {nivel}</h2>
            </div>
            """, unsafe_allow_html=True)
            
            # Factores críticos
            if scoring['factores_criticos']:
                st.markdown("#### ⚠️ Factores Críticos Detectados")
                for factor in scoring['factores_criticos']:
                    st.warning(f"🔴 {factor}")
            
            st.markdown("---")
            
            # === ALERTAS AUTOMÁTICAS ===
            st.markdown("### 🚨 Alertas de Riesgo")
            
            alertas = analisis_riesgo['alertas']
            
            if alertas:
                # Filtrar por prioridad
                alertas_criticas = [a for a in alertas if a['prioridad'] == 'Crítica']
                alertas_altas = [a for a in alertas if a['prioridad'] == 'Alta']
                alertas_medias = [a for a in alertas if a['prioridad'] == 'Media']
                alertas_bajas = [a for a in alertas if a['prioridad'] == 'Baja']
                
                # Resumen de alertas
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🔥 Críticas", len(alertas_criticas))
                with col2:
                    st.metric("🚨 Altas", len(alertas_altas))
                with col3:
                    st.metric("⚠️ Medias", len(alertas_medias))
                with col4:
                    st.metric("ℹ️ Bajas", len(alertas_bajas))
                
                # Mostrar alertas críticas y altas
                alertas_importantes = alertas_criticas + alertas_altas
                
                if alertas_importantes:
                    st.markdown("#### Alertas Prioritarias")
                    
                    for alerta in alertas_importantes:
                        color_prioridad = {
                            'Crítica': '#9C27B0',
                            'Alta': '#f44336',
                            'Media': '#FF9800',
                            'Baja': '#2196F3'
                        }
                        
                        emoji_tipo = {
                            'UIAF': '📋',
                            'Fraude': '🚨',
                            'Operacional': '⚙️',
                            'Compliance': '📜',
                            'Reputacional': '👁️'
                        }
                        
                        st.markdown(f"""
                        <div style='background: {color_prioridad.get(alerta['prioridad'], "#757575")}15; 
                                    border-left: 5px solid {color_prioridad.get(alerta['prioridad'], "#757575")};
                                    padding: 15px; 
                                    margin: 10px 0; 
                                    border-radius: 8px;
                                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
                            <h4 style='margin: 0 0 8px 0; color: {color_prioridad.get(alerta['prioridad'], "#757575")};'>
                                {emoji_tipo.get(alerta['tipo'], '⚠️')} {alerta['titulo']}
                            </h4>
                            <p style='margin: 5px 0; color: #555;'><strong>Tipo:</strong> {alerta['tipo']} | <strong>Prioridad:</strong> {alerta['prioridad']}</p>
                            <p style='margin: 5px 0; color: #666;'>{alerta['descripcion']}</p>
                            <p style='margin: 8px 0 5px 0; background: #f5f5f5; padding: 8px; border-radius: 5px;'>
                                <strong>💡 Acción requerida:</strong> {alerta['accion_requerida']}
                            </p>
                            <p style='margin: 5px 0 0 0; color: #888; font-size: 12px;'>
                                ⏰ Días para acción: {alerta['dias_para_accion']} | 
                                {'📋 Requiere reporte UIAF' if alerta['requiere_reporte_uiaf'] else '✅ No requiere reporte'}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Ver todas las alertas (colapsable)
                with st.expander(f"📋 Ver todas las alertas ({len(alertas)})"):
                    for alerta in alertas:
                        st.markdown(f"**{alerta['tipo']}** - {alerta['titulo']} ({alerta['prioridad']})")
                        st.caption(alerta['descripcion'])
                        st.markdown("---")
            
            else:
                st.success("✅ No se detectaron alertas de riesgo para este cliente")
            
            st.markdown("---")
            
            # === RECOMENDACIONES ===
            st.markdown("### 💡 Recomendaciones")
            
            recomendaciones = analisis_riesgo['recomendaciones']
            for rec in recomendaciones:
                st.info(rec)
            
            # Acciones requeridas
            col1, col2 = st.columns(2)
            with col1:
                if analisis_riesgo['requiere_due_diligence_reforzada']:
                    st.error("🔍 **Due Diligence Reforzada Requerida**")
                else:
                    st.success("✅ Due Diligence estándar suficiente")
            
            with col2:
                if analisis_riesgo['requiere_escalamiento']:
                    st.error("⬆️ **Requiere Escalamiento Inmediato**")
                else:
                    st.success("✅ No requiere escalamiento")
            
            # Próximo review
            st.info(f"📅 **Próximo review programado:** {analisis_riesgo['proximo_review']}")
            
            st.markdown("---")
            
            # === MATRIZ DE RIESGO ===
            with st.expander("🎯 Ver Matriz de Riesgo Detallada"):
                matriz = analisis_riesgo['matriz_riesgo']
                
                st.markdown("#### Riesgo Inherente vs Residual")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Riesgo Inherente (sin controles)**")
                    for categoria, valor in matriz['riesgo_inherente'].items():
                        st.progress(valor / 100, text=f"{categoria.capitalize()}: {valor}/100")
                
                with col2:
                    st.markdown("**Riesgo Residual (con controles)**")
                    for categoria, valor in matriz['riesgo_residual'].items():
                        st.progress(valor / 100, text=f"{categoria.capitalize()}: {valor}/100")
                
                st.markdown("#### Controles Aplicados")
                for control in matriz['controles_aplicados']:
                    st.markdown(f"✅ {control}")
                
                if matriz['gaps_control']:
                    st.markdown("#### Gaps de Control")
                    for gap in matriz['gaps_control']:
                        st.warning(f"⚠️ {gap}")
                
                if matriz['apetito_riesgo_superado']:
                    st.error("🚨 **ALERTA:** Apetito de riesgo superado")
                else:
                    st.success("✅ Dentro del apetito de riesgo")

else:
    st.warning("⚠️ No se pudieron cargar los datos.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>© 2025 AdamoPay - Sistema de Análisis y Reporte Transaccional</p>
        <p>Versión 1.0.0</p>
    </div>
    """,
    unsafe_allow_html=True
)
