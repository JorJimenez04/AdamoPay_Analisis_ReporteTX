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
    st.markdown("### 📊 Vista General del Negocio")
    st.markdown("<p style='color: gray; margin-top: -10px;'>Resumen ejecutivo de clientes activos y métricas clave</p>", unsafe_allow_html=True)
    
    # Métricas generales del negocio
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    
    # Filtrar solo transacciones PAGADAS y VALIDADAS
    if 'ESTADO' in df_completo.columns:
        df_relevantes = df_completo[df_completo['ESTADO'].str.lower().str.contains('pagado|validado', na=False)].copy()
    else:
        df_relevantes = df_completo.copy()
    
    total_transacciones_global = len(df_completo)
    tx_relevantes_global = len(df_relevantes)
    monto_total_global = df_relevantes['MONTO (COP)'].sum() if 'MONTO (COP)' in df_relevantes.columns else 0
    
    tasa_exito_global = (tx_relevantes_global / total_transacciones_global * 100) if total_transacciones_global > 0 else 0
    
    comision_total_global = df_relevantes['COMISION ((MONTO TOT'].sum() if 'COMISION ((MONTO TOT' in df_relevantes.columns else 0
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
        st.metric("💰 Volumen Efectivo", f"${monto_total_global:,.0f}", delta=f"Promedio: ${promedio_tx_global:,.0f}")
    with col4:
        st.metric("✅ Tasa Efectividad", f"{tasa_exito_global:.1f}%", delta="Pagadas/Validadas")
    with col5:
        st.metric("💵 Comisiones", f"${comision_total_global:,.0f}", delta="Recaudadas")
    with col6:
        st.metric("👤 Personas Naturales", f"{tx_pn:,} TX", delta=f"${monto_pn:,.0f}")
    with col7:
        st.metric("🏢 Personas Jurídicas", f"{tx_pj:,} TX", delta=f"${monto_pj:,.0f}")
    
    st.markdown("---")
    
    # === TARJETAS SIMPLES POR CLIENTE ===
    st.markdown("### 👥 Resumen por Cliente")
    st.markdown("<p style='color: gray; margin-top: -10px;'>Vista rápida de volúmenes y estados por cliente</p>", unsafe_allow_html=True)
    
    # Crear tarjetas en filas de 2 columnas
    for i in range(0, len(lista_clientes), 2):
        cols = st.columns(2)
        
        for idx, col in enumerate(cols):
            if i + idx < len(lista_clientes):
                cliente = lista_clientes[i + idx]
                df_cliente = df_completo[df_completo['CLIENTE'] == cliente]
                
                with col:
                    # Calcular métricas simples
                    total_tx = len(df_cliente)
                    total_monto = df_cliente['MONTO (COP)'].sum() if 'MONTO (COP)' in df_cliente.columns else 0
                    
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
                    
                    # Card del cliente
                    st.markdown(f"""
                    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 15px; border-radius: 10px; margin-bottom: 15px;
                                box-shadow: 0 2px 8px rgba(0,0,0,0.15);'>
                        <h3 style='margin: 0; color: white; font-size: 20px;'>🏢 {cliente}</h3>
                        <p style='margin: 5px 0 0 0; color: #ffffffcc; font-size: 13px;'>
                            {total_tx:,} transacciones | ${total_monto:,.0f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Mostrar tipos de transacción usando componentes de Streamlit
                    if tipos_dict:
                        tipos_cols = st.columns(len(tipos_dict))
                        iconos_mini = {'Fondeo': '💰', 'Crédito': '💳', 'Débito': '🏧', 'Otro': '📊'}
                        for idx_tipo, (tipo, count) in enumerate(tipos_dict.items()):
                            with tipos_cols[idx_tipo]:
                                st.metric(
                                    label=f"{iconos_mini.get(tipo, '📊')} {tipo}",
                                    value=f"{count:,}"
                                )
                    
                    # Mostrar beneficiarios usando componentes de Streamlit
                    if pn_count > 0 or pj_count > 0:
                        st.markdown("**Beneficiarios:**")
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
                    
                    # Mini cards por estado
                    if metricas_estado:
                        st.markdown("**Estados:**")
                        colores_estado = {
                            'Pagado': '#4CAF50',
                            'Validado': '#2196F3',
                            'Retornado': '#FF9800',
                            'Rechazado': '#f44336',
                            'Aprobado': '#9C27B0'
                        }
                        
                        emojis_estado = {
                            'Pagado': '✅',
                            'Validado': '🔵',
                            'Retornado': '🔄',
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
                                st.caption(f"${datos['monto']:,.0f}")
                    
                    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    
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
                    <h3 style='margin: 5px 0; color: #2c3e50; font-size: 24px;'>${monto_total_cliente:,.0f}</h3>
                    <p style='margin: 0; color: #2196F3; font-size: 11px;'>Transaccionado</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div style='background: #f8f9fa; padding: 15px; border-radius: 10px; 
                            border-left: 4px solid #FF9800; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                    <p style='margin: 0; color: #666; font-size: 12px;'>📈 Promedio TX</p>
                    <h3 style='margin: 5px 0; color: #2c3e50; font-size: 24px;'>${monto_promedio_cliente:,.0f}</h3>
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
                
                if 'TIPO DE TRA' in df_cliente.columns:
                    tipos_tx = df_cliente['TIPO DE TRA'].value_counts()
                    st.markdown("**Tipos de Transacciones:**")
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
                    
                    st.write(f"**Monto Mínimo:** ${monto_min:,.0f}")
                    st.write(f"**Monto Mediana:** ${monto_mediana:,.0f}")
                    st.write(f"**Monto Máximo:** ${monto_max:,.0f}")
                
                st.markdown("---")
                
                if 'COMISION ((MONTO TOT' in df_cliente_efectivo.columns:
                    comision_total = df_cliente_efectivo['COMISION ((MONTO TOT'].sum()
                    comision_promedio = df_cliente_efectivo['COMISION ((MONTO TOT'].mean()
                    
                    st.write(f"**Comisión Total:** ${comision_total:,.0f}")
                    st.write(f"**Comisión Promedio:** ${comision_promedio:,.0f}")
            
            # Tabla de transacciones recientes
            st.markdown("---")
            st.markdown("#### 📋 Últimas 50 Transacciones")
            st.dataframe(df_cliente.head(50), use_container_width=True, height=300)

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
