"""
Aplicación web (Streamlit) para el sistema de análisis y reporte transaccional de AdamoPay
- Carga robusta desde Excel (multi-hoja)
- Normalización de columnas (canónicas) + compatibilidad con nombres antiguos
- Bandera TX efectiva (Pagado/Validado) sin regex repetida
- Beneficiarios/Bancos con columnas fijas (sin heurísticas)
- Mitigación básica de HTML injection (escape)
- Pre-cálculo / cache de resúmenes por cliente
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import io
import sys
import html
import logging
import gc
from pathlib import Path
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent / "src"))

from config.settings import (
    ESTADOS_EFECTIVOS,
    TIPOS_PERSONA_NATURAL,
    TIPOS_PERSONA_JURIDICA,
    COLUMNAS_REQUERIDAS,
    COLUMNAS_CRITICAS,
    CACHE_TTL,
    LOG_LEVEL,
    LOG_FORMAT,
)
from config.ui_config import obtener_configuracion
from src.characterization.base_characterization import caracterizar_cliente_gafi
from src.risk_analysis import analizar_riesgo_cliente

# Configuración de logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Optimizaciones de rendimiento y memoria
sys.setrecursionlimit(3000)
gc.collect()

# Constantes de límites
MAX_FILE_SIZE_MB = 100
MAX_ROWS_WARNING = 100000


# =========================
# Helpers de normalización
# =========================
def _clean_text(x):
    """Convierte NaN/None/vacíos y strings 'nan'/'none' en None; si no, retorna str.strip()."""
    if pd.isna(x):
        return None
    s = str(x).strip()
    if s == "":
        return None
    if s.lower() in {"nan", "none", "null"}:
        return None
    return s


def _norm_upper(x):
    s = _clean_text(x)
    return s.upper() if s else None


def clasificar_tipo_persona(tipo_id):
    """Clasifica si es Persona Natural o Jurídica según el tipo de identificación (del BENEFICIARIO)."""
    if tipo_id is None:
        return "Desconocido"
    t = str(tipo_id).strip().upper()
    # Naturales
    if t in TIPOS_PERSONA_NATURAL:
        return "Natural"
    # Jurídicas
    if t in TIPOS_PERSONA_JURIDICA:
        return "Jurídica"
    return "Desconocido"


def _safe(s: str) -> str:
    """Escape para textos que van a HTML."""
    return html.escape(str(s))


def normalizar_nombre_entidad(nombre: str) -> str:
    """
    Normaliza nombres de beneficiarios y bancos para evitar duplicados por variaciones sintácticas.
    
    Transformaciones aplicadas:
    - Convierte a mayúsculas
    - Elimina espacios múltiples
    - Elimina puntos, comas, guiones
    - Elimina artículos y palabras comunes
    - Estandariza formas jurídicas (S.A.S -> SAS, LTDA -> LIMITADA)
    
    Ejemplos:
        "JL Outsurcer SAS" -> "JLOUTSOURCERSAS"
        "JLOutsourcer S.A.S." -> "JLOUTSOURCERSAS"
        "Banco de Bogotá" -> "BANCOBOGOTA"
        "Bancolombia S.A." -> "BANCOLOMBIASA"
    """
    import re
    
    if pd.isna(nombre) or nombre is None:
        return "DESCONOCIDO"
    
    # Convertir a string y mayúsculas
    nombre_norm = str(nombre).upper().strip()
    
    # Eliminar caracteres especiales y puntuación
    nombre_norm = re.sub(r'[.,\-_/\\(){}\[\]<>@#$%^&*+=|~`\'"°]', ' ', nombre_norm)
    
    # Normalizar formas jurídicas comunes
    formas_juridicas = {
        r'\bS\.?\s*A\.?\s*S\.?\b': 'SAS',
        r'\bS\.?\s*A\.?\b': 'SA',
        r'\bLTDA\.?\b': 'LIMITADA',
        r'\bE\.?\s*U\.?\b': 'EU',
        r'\bCIA\.?\b': 'COMPANIA',
        r'\bCO\.?\b': 'COMPANIA',
        r'\bCORP\.?\b': 'CORPORACION',
        r'\bINC\.?\b': 'INCORPORATED',
    }
    
    for patron, reemplazo in formas_juridicas.items():
        nombre_norm = re.sub(patron, reemplazo, nombre_norm)
    
    # Eliminar artículos y palabras conectoras comunes (entre espacios)
    palabras_eliminar = [
        r'\bDE\b', r'\bLA\b', r'\bEL\b', r'\bLOS\b', r'\bLAS\b',
        r'\bY\b', r'\bE\b', r'\bO\b', r'\bU\b',
        r'\bDEL\b', r'\bAL\b'
    ]
    
    for palabra in palabras_eliminar:
        # Solo eliminar si está entre espacios (no parte de otra palabra)
        nombre_norm = re.sub(f' {palabra} ', ' ', nombre_norm)
    
    # Eliminar todos los espacios
    nombre_norm = re.sub(r'\s+', '', nombre_norm)
    
    # Si quedó vacío, retornar desconocido
    if not nombre_norm:
        return "DESCONOCIDO"
    
    return nombre_norm


def formato_moneda(valor: float, incluir_signo: bool = True) -> str:
    """Formato consistente para moneda."""
    if valor >= 0:
        return f"$ {valor:,.0f} COP" if incluir_signo else f"{valor:,.0f}"
    else:
        return f"-$ {abs(valor):,.0f} COP" if incluir_signo else f"-{abs(valor):,.0f}"


def validar_columnas_cliente(df: pd.DataFrame, nombre_cliente: str) -> list:
    """Valida que las columnas críticas existan en el DataFrame del cliente."""
    columnas_faltantes = [c for c in COLUMNAS_CRITICAS if c not in df.columns]
    if columnas_faltantes:
        logger.warning(f"Cliente {nombre_cliente}: columnas faltantes {columnas_faltantes}")
    return columnas_faltantes


def validar_tamanio_archivo(uploaded_file):
    """Valida que el archivo no exceda el límite de tamaño"""
    if uploaded_file is None:
        return True, ""
    
    MAX_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
    file_size = uploaded_file.size if hasattr(uploaded_file, 'size') else 0
    
    if file_size > MAX_SIZE:
        return False, f"El archivo excede {MAX_FILE_SIZE_MB}MB. Tamaño: {file_size/(1024*1024):.1f}MB"
    
    return True, ""


def generar_datos_ejemplo():
    """
    Genera un dataset de ejemplo con estructura realista para demos y pruebas.
    Simula 3 clientes con transacciones de diferentes tipos.
    """
    logger.info("Generando datos de ejemplo para demo...")
    
    # Semilla para reproducibilidad
    np.random.seed(42)
    
    # Configuración de clientes
    clientes_config = [
        {"nombre": "TechCorp S.A.S", "num_tx": 150},
        {"nombre": "RetailMax LTDA", "num_tx": 200},
        {"nombre": "FinServ Colombia", "num_tx": 120}
    ]
    
    # Listas de datos sintéticos
    beneficiarios_pn = [
        "JUAN CARLOS RODRIGUEZ GOMEZ", "MARIA FERNANDA LOPEZ MARTINEZ",
        "CARLOS ANDRES PEREZ SILVA", "ANA MARIA GONZALEZ TORRES",
        "LUIS EDUARDO RAMIREZ CASTRO", "DIANA PATRICIA MORENO REYES",
        "JORGE ALBERTO DIAZ MENDOZA", "CLAUDIA MARCELA HERRERA ORTIZ"
    ]
    
    beneficiarios_pj = [
        "DISTRIBUIDORA DEL NORTE S.A.S", "INVERSIONES COLOMBIA LTDA",
        "TECNOLOGIA Y SERVICIOS S.A", "COMERCIALIZADORA ANDINA S.A.S",
        "GRUPO EMPRESARIAL DEL SUR LTDA", "LOGISTICA NACIONAL S.A"
    ]
    
    bancos = [
        "BANCOLOMBIA", "BANCO DE BOGOTA", "BBVA COLOMBIA",
        "DAVIVIENDA", "BANCO POPULAR", "COLPATRIA",
        "BANCO OCCIDENTE", "BANCO AV VILLAS"
    ]
    
    tipos_cuenta = ["AHORROS", "CORRIENTE"]
    estados = ["PAGADO", "VALIDADO", "PENDIENTE", "RECHAZADO", "ERROR"]
    tipos_tx = ["PAGO", "TRANSFERENCIA", "RETIRO", "DEPOSITO"]
    tipos_id_pn = ["CC", "CE", "PA", "TI"]
    tipos_id_pj = ["NIT", "RUT"]
    
    all_data = []
    
    # Generar transacciones para cada cliente
    for cliente_config in clientes_config:
        cliente_nombre = cliente_config["nombre"]
        num_tx = cliente_config["num_tx"]
        
        fecha_inicio = pd.Timestamp('2025-01-01')
        fecha_fin = pd.Timestamp('2025-12-31')
        
        for i in range(num_tx):
            # 70% Persona Natural, 30% Jurídica
            es_pn = np.random.random() < 0.7
            
            if es_pn:
                beneficiario = np.random.choice(beneficiarios_pn)
                tipo_id = np.random.choice(tipos_id_pn)
            else:
                beneficiario = np.random.choice(beneficiarios_pj)
                tipo_id = np.random.choice(tipos_id_pj)
            
            # 85% de transacciones efectivas (PAGADO/VALIDADO)
            es_efectiva = np.random.random() < 0.85
            estado = np.random.choice(["PAGADO", "VALIDADO"]) if es_efectiva else np.random.choice(estados)
            
            # Montos realistas (distribución sesgada hacia valores bajos)
            if es_pn:
                monto = np.random.lognormal(mean=12, sigma=1.2)  # ~100k-500k
            else:
                monto = np.random.lognormal(mean=14, sigma=1.5)  # ~500k-5M
            
            monto = round(monto, 2)
            comision = round(monto * np.random.uniform(0.001, 0.015), 2)
            monto_total = monto + comision
            
            # Fecha aleatoria
            fecha = fecha_inicio + pd.Timedelta(days=np.random.randint(0, 365))
            hora = f"{np.random.randint(8, 18):02d}:{np.random.randint(0, 60):02d}:{np.random.randint(0, 60):02d}"
            
            # ID de transacción
            tx_id = f"TX{fecha.strftime('%Y%m%d')}{np.random.randint(10000, 99999)}"
            
            registro = {
                "No.": i + 1,
                "FECHA": fecha,
                "HORA": hora,
                "ID DE TRANSACCION": tx_id,
                "TIPO DE TRANSACCION": np.random.choice(tipos_tx),
                "TIPO DE IDENTIFICACION": tipo_id,
                "BENEFICIARIO": beneficiario,
                "ID DE CLIENTE": f"{np.random.randint(1000000000, 9999999999)}",
                "BANCO": np.random.choice(bancos),
                "TIPO DE CUENTA": np.random.choice(tipos_cuenta),
                "NUMERO DE CUENTA": f"{np.random.randint(100000000, 999999999)}",
                "MONTO (COP)": monto,
                "COMISION (COP)": comision,
                "MONTO TOTAL (COP)": monto_total,
                "ESTADO": estado,
                "SALDO (COP)": round(np.random.uniform(100000, 5000000), 2),
                "DESCRIPCION": f"Pago {'servicios' if es_pn else 'proveedores'}",
                "cliente": cliente_nombre
            }
            
            all_data.append(registro)
    
    logger.info(f"Datos de ejemplo generados: {len(all_data)} transacciones para {len(clientes_config)} clientes")
    return pd.DataFrame(all_data)


def aplicar_transformaciones_columnas(df):
    """
    Aplica todas las transformaciones necesarias a un DataFrame que ya tiene columna 'cliente'.
    Usado para datos de ejemplo y procesamiento unificado.
    """
    # Diccionarios para mapeo de nombres normalizados
    beneficiarios_normalizados = {}
    bancos_normalizados = {}
    
    # Mapeo Excel -> canónico
    col_map = {
        "No.": "no",
        "FECHA": "fecha",
        "HORA": "hora",
        "ID DE TRANSACCION": "tx_id",
        "TIPO DE TRANSACCION": "tipo_tx",
        "TIPO DE IDENTIFICACION": "tipo_id_benef",
        "BENEFICIARIO": "beneficiario",
        "ID DE CLIENTE": "id_cliente",
        "BANCO": "banco",
        "TIPO DE CUENTA": "tipo_cuenta",
        "NUMERO DE CUENTA": "cuenta_numero",
        "MONTO (COP)": "monto_cop",
        "COMISION (COP)": "comision_cop",
        "MONTO TOTAL (COP)": "monto_total_cop",
        "ESTADO": "estado",
        "SALDO (COP)": "saldo_cop",
        "DESCRIPCION": "descripcion",
    }
    
    # Renombrar columnas conocidas
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
    
    # Limpieza de strings
    for c in ["tx_id", "tipo_tx", "tipo_id_benef", "beneficiario", "id_cliente",
              "banco", "tipo_cuenta", "cuenta_numero", "estado", "descripcion", "hora", "cliente"]:
        if c in df.columns:
            df[c] = df[c].map(_clean_text)
    
    # Normalización de beneficiarios
    if "beneficiario" in df.columns:
        df["beneficiario_norm"] = df["beneficiario"].apply(normalizar_nombre_entidad)
        for idx, row in df.iterrows():
            nombre_original = row["beneficiario"]
            nombre_normalizado = row["beneficiario_norm"]
            if nombre_normalizado not in beneficiarios_normalizados and pd.notna(nombre_original):
                beneficiarios_normalizados[nombre_normalizado] = nombre_original
        df["beneficiario_canonico"] = df["beneficiario_norm"].map(beneficiarios_normalizados)
    
    # Normalización de bancos
    if "banco" in df.columns:
        df["banco_norm_avanzado"] = df["banco"].apply(normalizar_nombre_entidad)
        for idx, row in df.iterrows():
            nombre_original = row["banco"]
            nombre_normalizado = row["banco_norm_avanzado"]
            if nombre_normalizado not in bancos_normalizados and pd.notna(nombre_original):
                bancos_normalizados[nombre_normalizado] = nombre_original
        df["banco_canonico"] = df["banco_norm_avanzado"].map(bancos_normalizados)
    
    # Normalizaciones útiles
    df["estado_norm"] = df["estado"].map(_norm_upper) if "estado" in df.columns else None
    df["tipo_tx_norm"] = df["tipo_tx"].map(_norm_upper) if "tipo_tx" in df.columns else None
    df["banco_norm"] = df.get("banco_canonico", df["banco"].map(_norm_upper) if "banco" in df.columns else None)
    
    # Fecha
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    
    # Timestamp combinado
    if "fecha" in df.columns and "hora" in df.columns:
        df["fecha_hora"] = pd.to_datetime(
            df["fecha"].dt.strftime("%Y-%m-%d") + " " + df["hora"].fillna("00:00:00"),
            errors="coerce",
        )
    else:
        df["fecha_hora"] = df.get("fecha", pd.NaT)
    
    # Numéricos
    for c in ["monto_cop", "comision_cop", "monto_total_cop", "saldo_cop"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    
    # Bandera TX efectiva
    df["tx_efectiva"] = df["estado_norm"].isin(ESTADOS_EFECTIVOS)
    
    # Tipo persona del beneficiario
    df["tipo_persona_benef"] = df.get("tipo_id_benef", None).map(clasificar_tipo_persona)
    
    # Columnas legacy para compatibilidad
    df["CLIENTE"] = df["cliente"]
    df["FECHA"] = df["fecha"]
    df["HORA"] = df.get("hora", None)
    df["ID DE TRANSACCION"] = df.get("tx_id", None)
    df["TIPO DE TRANSACCION"] = df.get("tipo_tx", None)
    df["TIPO DE IDENTIFICACION"] = df.get("tipo_id_benef", None)
    df["BENEFICIARIO"] = df.get("beneficiario_canonico", df.get("beneficiario", None))
    df["ID DE CLIENTE"] = df.get("id_cliente", None)
    df["BANCO"] = df.get("banco_canonico", df.get("banco", None))
    df["TIPO DE CUENTA"] = df.get("tipo_cuenta", None)
    df["NUMERO DE CUENTA"] = df.get("cuenta_numero", None)
    df["MONTO (COP)"] = df.get("monto_cop", 0)
    df["COMISION (COP)"] = df.get("comision_cop", 0)
    df["MONTO TOTAL (COP)"] = df.get("monto_total_cop", 0)
    df["ESTADO"] = df.get("estado", None)
    df["SALDO (COP)"] = df.get("saldo_cop", 0)
    df["DESCRIPCION"] = df.get("descripcion", None)
    df["TIPO DE TRA"] = df.get("tipo_tx", None)
    
    return df


# =========================
# Carga de datos desde Excel
# =========================
@st.cache_data(ttl=CACHE_TTL, show_spinner=False, max_entries=10)
def cargar_datos_clientes(archivo_subido=None, usar_datos_ejemplo=False):
    """
    Carga datos desde Excel (cada hoja = un cliente/originador) y crea:
    - columnas canónicas (snake_case)
    - columnas legacy (compatibilidad con tu código/módulos previos si las usan)
    
    Args:
        archivo_subido: Archivo Excel subido por el usuario (UploadedFile de Streamlit)
                       Si es None, intenta cargar desde ruta local (modo desarrollo)
        usar_datos_ejemplo: Si True, genera y usa datos sintéticos de ejemplo
    """
    # Si se solicitan datos de ejemplo, generarlos directamente
    if usar_datos_ejemplo:
        logger.info("Modo DEMO: Generando datos de ejemplo...")
        df_ejemplo = generar_datos_ejemplo()
        
        # El DataFrame ya viene con columna "cliente", procesarlo directamente
        # como si viniera del Excel pero sin las hojas
        lista_clientes = sorted(df_ejemplo["cliente"].unique().tolist())
        clientes_info = {c: len(df_ejemplo[df_ejemplo["cliente"] == c]) for c in lista_clientes}
        
        # Aplicar las mismas transformaciones que al Excel
        df_ejemplo = aplicar_transformaciones_columnas(df_ejemplo)
        
        logger.info(f"Datos de ejemplo listos: {len(lista_clientes)} clientes, {len(df_ejemplo)} transacciones")
        return df_ejemplo, clientes_info, lista_clientes
    
    excel_file = None
    
    # Si se proporciona un archivo subido, usarlo
    if archivo_subido is not None:
        logger.info(f"Cargando datos desde archivo subido: {archivo_subido.name}")
        try:
            excel_file = pd.ExcelFile(archivo_subido, engine='openpyxl')
        except Exception as e:
            logger.error(f"Error abriendo archivo Excel subido: {str(e)}")
            st.error(f"⚠️ Error abriendo archivo Excel: {str(e)}")
            return None, None, None
    else:
        # Modo desarrollo: intentar cargar desde ruta local
        ruta_excel = Path(__file__).parent / "data" / "Data_Clients&TX.xlsx"
        
        if not ruta_excel.exists():
            logger.warning(f"Archivo Excel local no encontrado: {ruta_excel}")
            return None, None, None
        
        logger.info(f"Cargando datos desde ruta local: {ruta_excel}")
        
        try:
            excel_file = pd.ExcelFile(ruta_excel, engine='openpyxl')
        except Exception as e:
            logger.error(f"Error abriendo archivo Excel local: {str(e)}")
            st.error(f"⚠️ Error abriendo archivo Excel: {str(e)}")
            return None, None, None

    frames = []
    clientes_info = {}
    
    # Diccionarios para mapeo de nombres normalizados a nombres canónicos
    beneficiarios_normalizados = {}
    bancos_normalizados = {}

    # Mapeo Excel -> canónico
    col_map = {
        "No.": "no",
        "FECHA": "fecha",
        "HORA": "hora",
        "ID DE TRANSACCION": "tx_id",
        "TIPO DE TRANSACCION": "tipo_tx",
        "TIPO DE IDENTIFICACION": "tipo_id_benef",
        "BENEFICIARIO": "beneficiario",
        "ID DE CLIENTE": "id_cliente",
        "BANCO": "banco",
        "TIPO DE CUENTA": "tipo_cuenta",
        "NUMERO DE CUENTA": "cuenta_numero",
        "MONTO (COP)": "monto_cop",
        "COMISION (COP)": "comision_cop",
        "MONTO TOTAL (COP)": "monto_total_cop",
        "ESTADO": "estado",
        "SALDO (COP)": "saldo_cop",
        "DESCRIPCION": "descripcion",
    }

    for sheet_name in excel_file.sheet_names:
        try:
            df = pd.read_excel(ruta_excel, sheet_name=sheet_name)
            logger.info(f"Cargando hoja: {sheet_name} ({len(df)} registros)")
        except Exception as e:
            logger.error(f"Error cargando hoja '{sheet_name}': {str(e)}")
            st.warning(f"⚠️ Error cargando hoja '{sheet_name}': {str(e)}")
            continue
        
        if df.empty:
            logger.warning(f"Hoja '{sheet_name}' está vacía, omitiendo...")
            continue
        
        df["cliente"] = sheet_name  # canónico

        # Renombrar columnas conocidas
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        # Limpieza de strings
        for c in [
            "tx_id",
            "tipo_tx",
            "tipo_id_benef",
            "beneficiario",
            "id_cliente",
            "banco",
            "tipo_cuenta",
            "cuenta_numero",
            "estado",
            "descripcion",
            "hora",
            "cliente",
        ]:
            if c in df.columns:
                df[c] = df[c].map(_clean_text)

        # ==========================================
        # NORMALIZACIÓN AVANZADA DE BENEFICIARIOS
        # ==========================================
        if "beneficiario" in df.columns:
            # Crear columna normalizada
            df["beneficiario_norm"] = df["beneficiario"].apply(normalizar_nombre_entidad)
            
            # Mantener el primer nombre original encontrado para cada versión normalizada
            for idx, row in df.iterrows():
                nombre_original = row["beneficiario"]
                nombre_normalizado = row["beneficiario_norm"]
                
                if nombre_normalizado not in beneficiarios_normalizados and pd.notna(nombre_original):
                    beneficiarios_normalizados[nombre_normalizado] = nombre_original
            
            # Reemplazar con el nombre canónico (el primero que se encontró)
            df["beneficiario_canonico"] = df["beneficiario_norm"].map(beneficiarios_normalizados)
            
            logger.info(f"  Cliente {sheet_name}: {df['beneficiario'].nunique()} beneficiarios originales -> "
                       f"{df['beneficiario_norm'].nunique()} únicos normalizados")

        # ==========================================
        # NORMALIZACIÓN AVANZADA DE BANCOS
        # ==========================================
        if "banco" in df.columns:
            # Crear columna normalizada
            df["banco_norm_avanzado"] = df["banco"].apply(normalizar_nombre_entidad)
            
            # Mantener el primer nombre original encontrado
            for idx, row in df.iterrows():
                nombre_original = row["banco"]
                nombre_normalizado = row["banco_norm_avanzado"]
                
                if nombre_normalizado not in bancos_normalizados and pd.notna(nombre_original):
                    bancos_normalizados[nombre_normalizado] = nombre_original
            
            # Reemplazar con el nombre canónico
            df["banco_canonico"] = df["banco_norm_avanzado"].map(bancos_normalizados)
            
            logger.info(f"  Cliente {sheet_name}: {df['banco'].nunique()} bancos originales -> "
                       f"{df['banco_norm_avanzado'].nunique()} únicos normalizados")

        # Normalizaciones útiles (mantener compatibilidad)
        df["estado_norm"] = df["estado"].map(_norm_upper) if "estado" in df.columns else None
        df["tipo_tx_norm"] = df["tipo_tx"].map(_norm_upper) if "tipo_tx" in df.columns else None
        df["banco_norm"] = df.get("banco_canonico", df["banco"].map(_norm_upper) if "banco" in df.columns else None)

        # Fecha
        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

        # Timestamp combinado (si HORA viene razonable)
        if "fecha" in df.columns and "hora" in df.columns:
            df["fecha_hora"] = pd.to_datetime(
                df["fecha"].dt.strftime("%Y-%m-%d") + " " + df["hora"].fillna("00:00:00"),
                errors="coerce",
            )
        else:
            df["fecha_hora"] = df.get("fecha", pd.NaT)

        # Numéricos
        for c in ["monto_cop", "comision_cop", "monto_total_cop", "saldo_cop"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        # Bandera TX efectiva (usando configuración)
        df["tx_efectiva"] = df["estado_norm"].isin(ESTADOS_EFECTIVOS)
        
        # Validar columnas críticas
        validar_columnas_cliente(df, sheet_name)

        # Tipo persona del beneficiario (según TIPO DE IDENTIFICACION)
        df["tipo_persona_benef"] = df.get("tipo_id_benef", None).map(clasificar_tipo_persona)

        # ==========================
        # Compatibilidad (legacy)
        # ==========================
        # Tu app anterior y/o módulos pueden estar esperando estos nombres:
        df["CLIENTE"] = df["cliente"]
        df["FECHA"] = df["fecha"]
        df["HORA"] = df.get("hora", None)
        df["ID DE TRANSACCION"] = df.get("tx_id", None)
        df["TIPO DE TRANSACCION"] = df.get("tipo_tx", None)
        df["TIPO DE IDENTIFICACION"] = df.get("tipo_id_benef", None)
        df["BENEFICIARIO"] = df.get("beneficiario_canonico", df.get("beneficiario", None))  # Usar canónico
        df["ID DE CLIENTE"] = df.get("id_cliente", None)
        df["BANCO"] = df.get("banco_canonico", df.get("banco", None))  # Usar canónico
        df["TIPO DE CUENTA"] = df.get("tipo_cuenta", None)
        df["NUMERO DE CUENTA"] = df.get("cuenta_numero", None)
        df["MONTO (COP)"] = df.get("monto_cop", 0)
        df["COMISION (COP)"] = df.get("comision_cop", 0)
        df["MONTO TOTAL (COP)"] = df.get("monto_total_cop", 0)
        df["ESTADO"] = df.get("estado", None)
        df["SALDO (COP)"] = df.get("saldo_cop", 0)
        df["DESCRIPCION"] = df.get("descripcion", None)

        # También tu UI vieja usaba 'TIPO DE TRA'
        df["TIPO DE TRA"] = df.get("tipo_tx", None)

        frames.append(df)
        clientes_info[sheet_name] = len(df)

    if not frames:
        logger.warning("No se cargaron datos de ninguna hoja")
        return pd.DataFrame(), {}, []
    
    df_completo = pd.concat(frames, ignore_index=True)
    lista_clientes = excel_file.sheet_names
    
    # Estadísticas de normalización
    beneficiarios_unicos_original = df_completo["beneficiario"].nunique() if "beneficiario" in df_completo.columns else 0
    beneficiarios_unicos_normalizado = df_completo["beneficiario_canonico"].nunique() if "beneficiario_canonico" in df_completo.columns else 0
    
    bancos_unicos_original = df_completo["banco"].nunique() if "banco" in df_completo.columns else 0
    bancos_unicos_normalizado = df_completo["banco_canonico"].nunique() if "banco_canonico" in df_completo.columns else 0
    
    logger.info(f"✓ Cargados {len(lista_clientes)} clientes con {len(df_completo)} transacciones totales")
    logger.info(f"  - TX efectivas: {df_completo['tx_efectiva'].sum() if 'tx_efectiva' in df_completo.columns else 0}")
    logger.info(f"  - Rango fechas: {df_completo['fecha'].min()} a {df_completo['fecha'].max()}")
    logger.info(f"  - Beneficiarios: {beneficiarios_unicos_original} originales -> {beneficiarios_unicos_normalizado} normalizados "
               f"({beneficiarios_unicos_original - beneficiarios_unicos_normalizado} duplicados eliminados)")
    logger.info(f"  - Bancos: {bancos_unicos_original} originales -> {bancos_unicos_normalizado} normalizados "
               f"({bancos_unicos_original - bancos_unicos_normalizado} duplicados eliminados)")
    
    # Limpiar memoria después de procesar datos grandes
    if len(df_completo) > 50000:
        gc.collect()
    
    return df_completo, clientes_info, lista_clientes


@st.cache_data(ttl=CACHE_TTL, show_spinner=False, max_entries=10)
def resumen_por_cliente(df_completo: pd.DataFrame, lista_clientes: list[str]) -> dict:
    """Pre-calcula resúmenes por cliente para no recalcular en cada render."""
    out = {}
    if df_completo is None or df_completo.empty:
        logger.warning("DataFrame vacío en resumen_por_cliente")
        return out
    
    logger.info(f"Calculando resúmenes para {len(lista_clientes)} clientes...")

    for cliente in lista_clientes:
        dfc = df_completo[df_completo["cliente"] == cliente].copy()
        df_eff = dfc[dfc["tx_efectiva"]].copy()

        total_tx = len(dfc)
        eff_tx = len(df_eff)
        monto_total = float(df_eff["monto_cop"].sum()) if "monto_cop" in df_eff.columns else 0.0
        monto_prom = float(df_eff["monto_cop"].mean()) if len(df_eff) > 0 else 0.0

        # Calcular fechas, filtrando valores inválidos o muy antiguos (antes de 2000)
        if "fecha" in dfc.columns:
            fechas_validas = dfc["fecha"].dropna()
            # Filtrar fechas razonables (desde año 2000 en adelante)
            fecha_minima = pd.Timestamp('2000-01-01')
            fechas_validas = fechas_validas[fechas_validas >= fecha_minima]
            primera = fechas_validas.min() if len(fechas_validas) > 0 else pd.NaT
            ultima = fechas_validas.max() if len(fechas_validas) > 0 else pd.NaT
        else:
            primera = pd.NaT
            ultima = pd.NaT
        
        dias_activo = int((ultima - primera).days) if pd.notna(primera) and pd.notna(ultima) else 0

        tasa_exito = (eff_tx / total_tx * 100) if total_tx > 0 else 0.0

        out[cliente] = {
            "df": dfc,
            "df_eff": df_eff,
            "total_tx": total_tx,
            "eff_tx": eff_tx,
            "monto_total": monto_total,
            "monto_prom": monto_prom,
            "tasa_exito": tasa_exito,
            "primera": primera,
            "ultima": ultima,
            "dias_activo": dias_activo,
        }
    
    logger.info(f"✓ Resúmenes calculados para {len(out)} clientes")
    return out


# =========================
# Configuración de la página
# =========================
st.set_page_config(
    page_title="AdamoPay - Análisis Transaccional",
    page_icon="💳",
    layout="wide",
)

# =========================
# Cargar configuración de UI
# =========================
ui_config = obtener_configuracion()

# Extraer valores para uso en CSS
f = ui_config["fuentes"]
t = ui_config["texto"]
m = ui_config["metricas"]
tc = ui_config["tarjetas"]
comp = ui_config.get("componentes", {})

# CSS Global dinámico basado en configuración
st.markdown(f"""
<style>
    /* Aumentar tamaño base de texto en toda la app */
    html, body, [class*="css"], .stApp {{
        font-size: {t['base']}px !important;
    }}
    
    /* Aumentar tamaño de valores en métricas - SIN NEGRITA */
    [data-testid="stMetricValue"] {{
        font-size: {m['valor']}px !important;
        font-weight: 500 !important;
        line-height: 1.2 !important;
    }}
    
    /* Labels de métricas - MÁS GRANDE, SIN NEGRITA */
    [data-testid="stMetricLabel"] {{
        font-size: {m['label']}px !important;
        font-weight: 400 !important;
        margin-bottom: 8px !important;
    }}
    
    /* Delta de métricas - MÁS GRANDE, SIN NEGRITA */
    [data-testid="stMetricDelta"] {{
        font-size: {m['delta']}px !important;
        font-weight: 400 !important;
    }}
    
    /* Texto en markdown */
    .stMarkdown {{
        font-size: {t['base']}px !important;
    }}
    
    /* Headers h1, h2, h3, h4, h5 más grandes */
    h1 {{
        font-size: {f['h1']}px !important;
        font-weight: 600 !important;
        margin-bottom: 20px !important;
    }}
    h2 {{
        font-size: {f['h2']}px !important;
        font-weight: 500 !important;
        margin-bottom: 16px !important;
    }}
    h3 {{
        font-size: {f['h3']}px !important;
        font-weight: 500 !important;
        margin-bottom: 14px !important;
    }}
    h4 {{
        font-size: {f['h4']}px !important;
        font-weight: 500 !important;
        margin-bottom: 12px !important;
    }}
    h5 {{
        font-size: {f['h5']}px !important;
        font-weight: 500 !important;
        margin-bottom: 10px !important;
    }}
    
    /* Párrafos y texto general */
    p {{
        font-size: {t['parrafo']}px !important;
        line-height: 1.6 !important;
    }}
    
    /* Expanders */
    .streamlit-expanderHeader {{
        font-size: {comp.get('expander', 20)}px !important;
        font-weight: 400 !important;
    }}
    .streamlit-expanderContent {{
        font-size: {comp.get('expander', 20) - 1}px !important;
    }}
    
    /* Captions */
    .stCaption {{
        font-size: {t['caption']}px !important;
    }}
    
    /* Botones */
    .stButton button {{
        font-size: {comp.get('boton', 19)}px !important;
        font-weight: 400 !important;
        padding: 12px 24px !important;
    }}
    
    /* Dataframes */
    .dataframe {{
        font-size: {comp.get('dataframe', 18)}px !important;
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {{
        font-size: {comp.get('tab', 20)}px !important;
        font-weight: 400 !important;
        padding: 12px 20px !important;
    }}
    
    /* Listas y bullets */
    li {{
        font-size: {t['base']}px !important;
        line-height: 1.6 !important;
    }}
    
    /* Texto en inputs y selectbox */
    input, select, textarea {{
        font-size: {comp.get('input', 19)}px !important;
    }}
    
    /* ===================================== */
    /* ESTILOS ESPECÍFICOS PARA TARJETAS DE CLIENTE */
    /* ===================================== */
    
    /* Container de tarjetas - identificador único */
    .tarjeta-cliente-container [data-testid="stMetricValue"] {{
        font-size: {tc['valor_metrica']}px !important;
    }}
    
    .tarjeta-cliente-container [data-testid="stMetricLabel"] {{
        font-size: {tc['label_metrica']}px !important;
    }}
    
    .tarjeta-cliente-container [data-testid="stMetricDelta"] {{
        font-size: {tc['delta']}px !important;
    }}
    
    .tarjeta-cliente-container .streamlit-expanderHeader {{
        font-size: {tc['expander_header']}px !important;
    }}
    
    .tarjeta-cliente-container .streamlit-expanderContent {{
        font-size: {tc['expander_content']}px !important;
    }}
    
    .tarjeta-cliente-container p {{
        font-size: {tc['texto']}px !important;
    }}
    
    .tarjeta-cliente-container strong {{
        font-size: {tc['texto']}px !important;
    }}
</style>
""", unsafe_allow_html=True)

# Título principal con logos - Buscar rutas de logos primero
logo_path1 = None
for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
    test_path = Path(__file__).parent / "assets" / f"LogoAdamoServices{ext}"
    if test_path.exists():
        logo_path1 = test_path
        break

logo_path2 = None
for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
    test_path = Path(__file__).parent / "assets" / f"LogoAdamoPay{ext}"
    if test_path.exists():
        logo_path2 = test_path
        break

# Convertir logos a base64 para incrustarlos en HTML
import base64
logo1_base64 = ""
logo2_base64 = ""

if logo_path1 and logo_path1.exists():
    with open(logo_path1, "rb") as f:
        logo1_base64 = base64.b64encode(f.read()).decode()

if logo_path2 and logo_path2.exists():
    with open(logo_path2, "rb") as f:
        logo2_base64 = base64.b64encode(f.read()).decode()

# Crear header con fondo azul y logos
header_html = f"""
<div style='
    background: linear-gradient(135deg, #1c2a38 0%, #2a4458 100%);
    padding: 40px 20px;
    border-radius: 10px;
    margin-bottom: 30px;
    position: relative;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
'>
    <div style='display: flex; align-items: center; justify-content: space-between;'>
        <div style='flex: 0 0 200px;'>
            {f'<img src="data:image/png;base64,{logo1_base64}" style="width: 200px; height: auto; mix-blend-mode: lighten; filter: brightness(1.2);">' if logo1_base64 else ''}
        </div>
        <div style='flex: 1; text-align: center; padding: 0 20px;'>
            <h1 style='color: white; margin: 0; font-size: 2.5rem; font-weight: 700;'>
                AdamoServices – Plataforma de Inteligencia Transaccional
            </h1>
            <p style='color: #e0e0e0; margin: 15px 0 5px 0; font-size: 1.2rem;'>
                Monitoreo, análisis y generación de reportes transaccionales
            </p>
            <p style='color: #b0b0b0; margin: 5px 0 0 0; font-size: 0.95rem;'>
                Sistema de Análisis y Reporte Transaccional
            </p>
        </div>
        <div style='flex: 0 0 300px; text-align: right;'>
            {f'<img src="data:image/jpeg;base64,{logo2_base64}" style="width: 300px; height: auto; mix-blend-mode: lighten; filter: brightness(1.2);">' if logo2_base64 else ''}
        </div>
    </div>
</div>
"""

st.markdown(header_html, unsafe_allow_html=True)


# =========================
# Cargar datos
# =========================
logger.info("="*50)
logger.info("Iniciando aplicación AdamoPay - Análisis Transaccional")
logger.info("="*50)

# Limpiar memoria al inicio
gc.collect()

# Sidebar: Selector de método de carga
st.sidebar.markdown("## 🔧 Configuración de Datos")
st.sidebar.markdown("---")

metodo_carga = st.sidebar.radio(
    "Método de carga de datos:",
    options=["📤 Subir Archivo", "🎯 Datos de Ejemplo (Demo)", "📁 Archivo Local"],
    index=0,
    help="""
    **Subir Archivo**: Carga tu propio archivo Excel (recomendado para producción)
    **Datos de Ejemplo**: Usa datos sintéticos para probar la aplicación
    **Archivo Local**: Busca 'Data_Clients&TX.xlsx' en carpeta data/ (desarrollo)
    """
)

st.sidebar.markdown("---")

# Widget de carga de archivo
st.markdown("## 📂 Cargar Datos Transaccionales")

df_completo = None
clientes_info = None
lista_clientes = None

# Modo 1: Subir Archivo
if metodo_carga == "📤 Subir Archivo":
    st.markdown(
        f"""Por favor, sube tu archivo Excel con los datos transaccionales. 
        El archivo debe contener múltiples hojas, donde cada hoja representa un cliente/originador.
        
        **Límite de tamaño:** {MAX_FILE_SIZE_MB}MB por archivo"""
    )
    
    archivo_subido = st.file_uploader(
        "Selecciona el archivo Excel",
        type=["xlsx", "xls"],
        help=f"Archivo Excel con transacciones. Máximo {MAX_FILE_SIZE_MB}MB",
        key="file_uploader_main"
    )
    
    if archivo_subido is not None:
        # Validar tamaño del archivo
        es_valido, mensaje_error = validar_tamanio_archivo(archivo_subido)
        
        if not es_valido:
            st.error(f"⚠️ {mensaje_error}")
            st.info("💡 **Sugerencia:** Divide tu archivo en partes más pequeñas o filtra datos antiguos.")
            st.stop()
        
        try:
            with st.spinner("📊 Cargando y procesando datos..."):
                df_completo, clientes_info, lista_clientes = cargar_datos_clientes(archivo_subido=archivo_subido)
            
            if df_completo is not None and not df_completo.empty:
                # Warning si hay muchas filas
                if len(df_completo) > MAX_ROWS_WARNING:
                    st.warning(f"⚠️ Dataset grande ({len(df_completo):,} filas). El procesamiento puede ser lento en el plan gratuito.")
                
                st.success(f"✅ Datos cargados correctamente: {len(lista_clientes)} clientes, {len(df_completo):,} transacciones")
                
                # Limpiar memoria después de carga grande
                if len(df_completo) > 50000:
                    gc.collect()
        
        except Exception as e:
            st.error(f"❌ Error al cargar archivo: {str(e)}")
            logger.error(f"Error crítico al cargar archivo: {str(e)}", exc_info=True)
            st.info("💡 Intenta con un archivo más pequeño o verifica el formato del Excel.")
            st.stop()

# Modo 2: Datos de Ejemplo
elif metodo_carga == "🎯 Datos de Ejemplo (Demo)":
    st.info("""
    ### 🎯 Modo Demo
    
    Usando datos sintéticos de ejemplo para probar la aplicación.
    
    **Incluye:**
    - 3 clientes ficticios (TechCorp, RetailMax, FinServ)
    - ~470 transacciones simuladas
    - Datos realistas de beneficiarios, bancos y montos
    - Ideal para entender las funcionalidades sin subir archivos
    """)
    
    if st.button("🚀 Cargar Datos de Ejemplo", type="primary"):
        try:
            with st.spinner("📊 Generando datos de ejemplo..."):
                df_completo, clientes_info, lista_clientes = cargar_datos_clientes(usar_datos_ejemplo=True)
            
            if df_completo is not None and not df_completo.empty:
                st.success(f"✅ Datos de ejemplo cargados: {len(lista_clientes)} clientes, {len(df_completo):,} transacciones")
        
        except Exception as e:
            st.error(f"❌ Error generando datos de ejemplo: {str(e)}")
            logger.error(f"Error generando datos de ejemplo: {str(e)}", exc_info=True)
            st.stop()

# Modo 3: Archivo Local
elif metodo_carga == "📁 Archivo Local":
    st.info("""
    ### 📁 Modo Desarrollo
    
    Buscando archivo 'Data_Clients&TX.xlsx' en la carpeta 'data/'.
    
    Este modo es útil para desarrollo local sin necesidad de subir archivos cada vez.
    """)
    
    try:
        with st.spinner("📊 Cargando datos desde archivo local..."):
            df_completo, clientes_info, lista_clientes = cargar_datos_clientes(archivo_subido=None)
        
        if df_completo is not None and not df_completo.empty:
            st.success(f"✅ Datos locales cargados: {len(lista_clientes)} clientes, {len(df_completo):,} transacciones")
    
    except Exception as e:
        st.error(f"❌ Error al cargar archivo local: {str(e)}")
        logger.warning(f"No se pudo cargar archivo local: {str(e)}")
        st.info("💡 Verifica que el archivo 'Data_Clients&TX.xlsx' exista en la carpeta 'data/'.")

# Validar que se cargaron los datos
if df_completo is None or df_completo.empty:
    st.warning(
        """⚠️ **No hay datos disponibles**
        
        Por favor, selecciona un método de carga de datos en el panel lateral:
        
        - **📤 Subir Archivo**: Sube tu archivo Excel con transacciones
        - **🎯 Datos de Ejemplo**: Usa datos sintéticos para probar la app
        - **📁 Archivo Local**: Coloca 'Data_Clients&TX.xlsx' en carpeta 'data/'
        
        **Formato requerido:**
        - Cada hoja = un cliente/originador
        - Columnas: FECHA, BENEFICIARIO, BANCO, MONTO (COP), ESTADO, etc.
        """
    )
    st.stop()

resumen = resumen_por_cliente(df_completo, lista_clientes)

st.markdown("---")

# =========================
# Capa 1: Métricas del negocio
# =========================
st.markdown("## 🟦 Métricas del Negocio")
st.caption("Indicadores objetivos de operación y comportamiento transaccional")

# Global: TX efectivas
df_relevantes = df_completo[df_completo["tx_efectiva"]].copy()

total_transacciones_global = len(df_completo)
tx_relevantes_global = len(df_relevantes)
monto_total_global = float(df_relevantes["monto_cop"].sum()) if "monto_cop" in df_relevantes.columns else 0.0
promedio_tx_global = float(df_relevantes["monto_cop"].mean()) if len(df_relevantes) else 0.0
tasa_exito_global = (tx_relevantes_global / total_transacciones_global * 100) if total_transacciones_global > 0 else 0.0

# Métricas por tipo beneficiario (PN/PJ) sobre TX efectivas
tx_pn = int((df_relevantes["tipo_persona_benef"] == "Natural").sum()) if "tipo_persona_benef" in df_relevantes.columns else 0
tx_pj = int((df_relevantes["tipo_persona_benef"] == "Jurídica").sum()) if "tipo_persona_benef" in df_relevantes.columns else 0
monto_pn = float(df_relevantes.loc[df_relevantes["tipo_persona_benef"] == "Natural", "monto_cop"].sum()) if tx_pn else 0.0
monto_pj = float(df_relevantes.loc[df_relevantes["tipo_persona_benef"] == "Jurídica", "monto_cop"].sum()) if tx_pj else 0.0

# Beneficiarios únicos por tipo (usando columnas normalizadas)
benef_unicos_pn = int(df_relevantes[df_relevantes["tipo_persona_benef"] == "Natural"]["BENEFICIARIO"].nunique()) if tx_pn and "BENEFICIARIO" in df_relevantes.columns else 0
benef_unicos_pj = int(df_relevantes[df_relevantes["tipo_persona_benef"] == "Jurídica"]["BENEFICIARIO"].nunique()) if tx_pj and "BENEFICIARIO" in df_relevantes.columns else 0

# Frecuencia de transacciones por beneficiario
frecuencia_pn = (tx_pn / benef_unicos_pn) if benef_unicos_pn > 0 else 0
frecuencia_pj = (tx_pj / benef_unicos_pj) if benef_unicos_pj > 0 else 0

# Tendencia temporal (comparar primer vs segundo mes)
if "fecha" in df_relevantes.columns and len(df_relevantes) > 0:
    df_relevantes_temp = df_relevantes.copy()
    df_relevantes_temp["mes"] = df_relevantes_temp["fecha"].dt.to_period("M")
    
    # Agrupar por mes y tipo de persona
    tendencia_pn = df_relevantes_temp[df_relevantes_temp["tipo_persona_benef"] == "Natural"].groupby("mes").size()
    tendencia_pj = df_relevantes_temp[df_relevantes_temp["tipo_persona_benef"] == "Jurídica"].groupby("mes").size()
    
    # Calcular crecimiento (último mes vs primero)
    if len(tendencia_pn) >= 2:
        crecimiento_pn = ((tendencia_pn.iloc[-1] - tendencia_pn.iloc[0]) / tendencia_pn.iloc[0] * 100) if tendencia_pn.iloc[0] > 0 else 0
    else:
        crecimiento_pn = 0
    
    if len(tendencia_pj) >= 2:
        crecimiento_pj = ((tendencia_pj.iloc[-1] - tendencia_pj.iloc[0]) / tendencia_pj.iloc[0] * 100) if tendencia_pj.iloc[0] > 0 else 0
    else:
        crecimiento_pj = 0
else:
    crecimiento_pn = 0
    crecimiento_pj = 0

# Comisiones totales generadas
comisiones_totales = float(df_relevantes["comision_cop"].sum()) if "comision_cop" in df_relevantes.columns else 0.0

# Porcentajes de participación
pct_pn = (monto_pn / monto_total_global * 100) if monto_total_global > 0 else 0
pct_pj = (monto_pj / monto_total_global * 100) if monto_total_global > 0 else 0

# Análisis de días pico por fecha específica
df_por_fecha = df_relevantes.groupby(df_relevantes["fecha"].dt.date).agg({
    "monto_cop": "sum",
    "fecha": "count"
}).rename(columns={"fecha": "cantidad_tx"})

if not df_por_fecha.empty:
    # Encontrar fecha con más transacciones
    fecha_max_tx = df_por_fecha["cantidad_tx"].idxmax()
    max_tx_dia = int(df_por_fecha.loc[fecha_max_tx, "cantidad_tx"])
    
    # Encontrar fecha con mayor monto
    fecha_max_monto = df_por_fecha["monto_cop"].idxmax()
    max_monto_dia = float(df_por_fecha.loc[fecha_max_monto, "monto_cop"])
    
    # Encontrar fecha con menos transacciones
    fecha_min_tx = df_por_fecha["cantidad_tx"].idxmin()
    min_tx_dia = int(df_por_fecha.loc[fecha_min_tx, "cantidad_tx"])
    
    # Encontrar fecha con menor monto
    fecha_min_monto = df_por_fecha["monto_cop"].idxmin()
    min_monto_dia = float(df_por_fecha.loc[fecha_min_monto, "monto_cop"])
    
    # Formatear fechas
    fecha_max_tx_str = pd.to_datetime(fecha_max_tx).strftime("%d/%m/%Y")
    fecha_max_monto_str = pd.to_datetime(fecha_max_monto).strftime("%d/%m/%Y")
    fecha_min_tx_str = pd.to_datetime(fecha_min_tx).strftime("%d/%m/%Y")
    fecha_min_monto_str = pd.to_datetime(fecha_min_monto).strftime("%d/%m/%Y")
else:
    fecha_max_tx_str = "N/A"
    max_tx_dia = 0
    fecha_max_monto_str = "N/A"
    max_monto_dia = 0.0
    fecha_min_tx_str = "N/A"
    min_tx_dia = 0
    fecha_min_monto_str = "N/A"
    min_monto_dia = 0.0

# Análisis de mes pico
if "fecha" in df_relevantes.columns and len(df_relevantes) > 0:
    df_relevantes["anio_mes"] = df_relevantes["fecha"].dt.to_period("M")
    df_por_mes = df_relevantes.groupby("anio_mes").agg({
        "monto_cop": "sum",
        "fecha": "count"
    }).rename(columns={"fecha": "cantidad_tx"})
    
    if not df_por_mes.empty:
        # Encontrar mes con más transacciones
        mes_max_tx = df_por_mes["cantidad_tx"].idxmax()
        max_tx_mes = int(df_por_mes.loc[mes_max_tx, "cantidad_tx"])
        monto_mes_max_tx = float(df_por_mes.loc[mes_max_tx, "monto_cop"])
        
        # Mapeo de meses en español
        meses_esp = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        
        mes_nombre = meses_esp.get(mes_max_tx.month, "N/A")
        anio = mes_max_tx.year
        mes_max_tx_str = f"{mes_nombre} {anio}"
    else:
        mes_max_tx_str = "N/A"
        max_tx_mes = 0
        monto_mes_max_tx = 0.0
else:
    mes_max_tx_str = "N/A"
    max_tx_mes = 0
    monto_mes_max_tx = 0.0

# ============================================
# FILA 1: MÉTRICAS CORE (5 columnas)
# ============================================
st.markdown("### 📊 Indicadores Principales")
row1_col1, row1_col2, row1_col3, row1_col4, row1_col5 = st.columns(5)

with row1_col1:
    st.metric(
        label="💰 Volumen Total Transado",
        value=formato_moneda(monto_total_global),
        delta=f"{tx_relevantes_global:,} TX efectivas",
        help="Monto total de todas las transacciones efectivas (Pagadas/Validadas)"
    )

with row1_col2:
    st.metric(
        label="💳 Transacciones Efectivas",
        value=f"{tx_relevantes_global:,}",
        delta=f"{tasa_exito_global:.1f}% efectividad",
        help="Cantidad de transacciones exitosas (Estado: Pagado o Validado)"
    )

with row1_col3:
    st.metric(
        label="📈 Ticket Promedio",
        value=formato_moneda(promedio_tx_global),
        delta=f"Por transacción",
        help="Monto promedio por transacción efectiva - Indica el perfil transaccional"
    )

with row1_col4:
    # NUEVO: Mediana de montos
    if "monto_cop" in df_relevantes.columns and len(df_relevantes) > 0:
        mediana_global = float(df_relevantes["monto_cop"].median())
        diferencia_mediana = ((promedio_tx_global - mediana_global) / mediana_global * 100) if mediana_global > 0 else 0
        st.metric(
            label="📊 Mediana de Montos",
            value=formato_moneda(mediana_global),
            delta=f"{diferencia_mediana:+.1f}% vs promedio",
            help="Valor mediano de transacciones - Más robusto ante outliers que el promedio"
        )
    else:
        st.metric(
            label="📊 Mediana de Montos",
            value="N/A",
            help="No hay datos de montos disponibles"
        )

with row1_col5:
    st.metric(
        label="💵 Comisiones Totales",
        value=formato_moneda(comisiones_totales),
        delta=f"Revenue generado",
        help="Total de comisiones generadas por transacciones efectivas"
    )

# ============================================
# FILA 2: FRECUENCIA Y RITMO OPERATIVO (5 columnas)
# ============================================
st.markdown("### ⚡ Frecuencia y Ritmo Operativo")
row2_col1, row2_col2, row2_col3, row2_col4, row2_col5 = st.columns(5)

with row2_col1:
    # Calcular días operativos (días con al menos 1 TX)
    if "fecha" in df_relevantes.columns and len(df_relevantes) > 0:
        dias_unicos = df_relevantes['fecha'].dt.date.nunique()
        dias_totales = (df_relevantes['fecha'].max() - df_relevantes['fecha'].min()).days + 1
        densidad_operativa = (dias_unicos / dias_totales * 100) if dias_totales > 0 else 0
        
        st.metric(
            label="📅 Días Operativos",
            value=f"{dias_unicos}",
            delta=f"{densidad_operativa:.1f}% densidad",
            help=f"Días con actividad de {dias_totales} totales - Indica continuidad operativa"
        )
    else:
        st.metric(
            label="📅 Días Operativos",
            value="N/A",
            help="No hay datos de fechas disponibles"
        )

with row2_col2:
    # Frecuencia transaccional diaria
    if "fecha" in df_relevantes.columns and len(df_relevantes) > 0:
        dias_unicos = df_relevantes['fecha'].dt.date.nunique()
        tx_por_dia_promedio = tx_relevantes_global / dias_unicos if dias_unicos > 0 else 0
        
        st.metric(
            label="🔄 Frecuencia Diaria",
            value=f"{tx_por_dia_promedio:.1f}",
            delta=f"TX/día promedio",
            help="Promedio de transacciones efectivas por día operativo"
        )
    else:
        st.metric(
            label="🔄 Frecuencia Diaria",
            value="N/A",
            help="No hay datos de fechas disponibles"
        )

with row2_col3:
    # Velocidad del dinero (throughput)
    if "fecha" in df_relevantes.columns and len(df_relevantes) > 0:
        dias_unicos = df_relevantes['fecha'].dt.date.nunique()
        velocidad_dinero = monto_total_global / dias_unicos if dias_unicos > 0 else 0
        
        st.metric(
            label="⚡ Velocidad Transaccional",
            value=formato_moneda(velocidad_dinero).replace(" COP", ""),
            delta=f"COP/día",
            help="Volumen promedio procesado por día operativo"
        )
    else:
        st.metric(
            label="⚡ Velocidad Transaccional",
            value="N/A",
            help="No hay datos de fechas disponibles"
        )

with row2_col4:
    # Volatilidad de TX diarias
    if "fecha" in df_relevantes.columns and len(df_relevantes) > 0:
        tx_por_fecha = df_relevantes.groupby(df_relevantes['fecha'].dt.date).size()
        volatilidad = tx_por_fecha.std() if len(tx_por_fecha) > 1 else 0
        cv = (volatilidad / tx_por_fecha.mean() * 100) if tx_por_fecha.mean() > 0 else 0
        
        st.metric(
            label="📊 Volatilidad Operativa",
            value=f"±{volatilidad:.0f} TX",
            delta=f"CV: {cv:.1f}%",
            help="Desviación estándar de TX diarias - Mide estabilidad operativa"
        )
    else:
        st.metric(
            label="📊 Volatilidad Operativa",
            value="N/A",
            help="No hay suficientes datos para calcular volatilidad"
        )

with row2_col5:
    # Costo por transacción (eficiencia)
    if tx_relevantes_global > 0:
        costo_por_tx = comisiones_totales / tx_relevantes_global
        
        st.metric(
            label="💵 Costo por TX",
            value=formato_moneda(costo_por_tx),
            delta=f"Eficiencia operativa",
            help="Comisión promedio por transacción efectiva"
        )
    else:
        st.metric(
            label="💵 Costo por TX",
            value="N/A",
            help="No hay transacciones efectivas"
        )

# ============================================
# FILA 3: TENDENCIAS Y CONCENTRACIÓN (5 columnas)
# ============================================
st.markdown("### 📈 Tendencias y Concentración")
row3_col1, row3_col2, row3_col3, row3_col4, row3_col5 = st.columns(5)

with row3_col1:
    # Tendencia mensual (primer vs último mes)
    if "fecha" in df_relevantes.columns and len(df_relevantes) > 0:
        df_relevantes_temp = df_relevantes.copy()
        df_relevantes_temp['mes'] = df_relevantes_temp['fecha'].dt.to_period('M')
        tx_por_mes = df_relevantes_temp.groupby('mes').size()
        
        if len(tx_por_mes) >= 2:
            tendencia_mensual = ((tx_por_mes.iloc[-1] - tx_por_mes.iloc[0]) / tx_por_mes.iloc[0] * 100) if tx_por_mes.iloc[0] > 0 else 0
            tendencia_icon = "📈" if tendencia_mensual > 0 else "📉" if tendencia_mensual < 0 else "➡️"
            tendencia_color = "normal" if tendencia_mensual >= 0 else "inverse"
            
            st.metric(
                label="📈 Tendencia Mensual",
                value=f"{tendencia_mensual:+.1f}%",
                delta=f"{tendencia_icon} Primer vs Último",
                delta_color=tendencia_color,
                help="Variación porcentual de TX entre el primer y último mes del período"
            )
        else:
            st.metric(
                label="📈 Tendencia Mensual",
                value="N/A",
                delta="Requiere 2+ meses",
                help="Se necesitan al menos 2 meses de datos"
            )
    else:
        st.metric(
            label="📈 Tendencia Mensual",
            value="N/A",
            help="No hay datos de fechas disponibles"
        )

with row3_col2:
    # Momentum (aceleración/desaceleración)
    if "fecha" in df_relevantes.columns and len(df_relevantes) > 0:
        df_relevantes_temp = df_relevantes.copy()
        df_relevantes_temp['mes'] = df_relevantes_temp['fecha'].dt.to_period('M')
        tx_por_mes = df_relevantes_temp.groupby('mes').size()
        
        if len(tx_por_mes) >= 3:
            # Calcular momentum (cambio en la tasa de cambio)
            cambios = tx_por_mes.pct_change().fillna(0) * 100
            momentum = cambios.iloc[-1] - cambios.iloc[-2] if len(cambios) >= 2 else 0
            momentum_icon = "🚀" if momentum > 5 else "📈" if momentum > 0 else "📉" if momentum < -5 else "➡️"
            
            st.metric(
                label="🚀 Momentum",
                value=f"{momentum:+.1f}pp",
                delta=f"{momentum_icon} Aceleración",
                delta_color="normal" if momentum >= 0 else "inverse",
                help="Aceleración/desaceleración del crecimiento (cambio en la tasa de variación)"
            )
        else:
            st.metric(
                label="🚀 Momentum",
                value="N/A",
                delta="Requiere 3+ meses",
                help="Se necesitan al menos 3 meses de datos"
            )
    else:
        st.metric(
            label="🚀 Momentum",
            value="N/A",
            help="No hay datos de fechas disponibles"
        )

with row3_col3:
    # Índice de concentración de beneficiarios (Top 10)
    if "beneficiario" in df_relevantes.columns and len(df_relevantes) > 0:
        df_benef_conc = df_relevantes.groupby('beneficiario')['monto_cop'].sum()
        total_benef = len(df_benef_conc)
        
        # Calcular % del top 10
        top10_monto = df_benef_conc.nlargest(min(10, len(df_benef_conc))).sum()
        pct_top10 = (top10_monto / monto_total_global * 100) if monto_total_global > 0 else 0
        
        # Clasificar concentración
        if pct_top10 > 80:
            conc_nivel = "Muy Alta"
            conc_icon = "🔴"
            conc_color = "inverse"
        elif pct_top10 > 60:
            conc_nivel = "Alta"
            conc_icon = "🟠"
            conc_color = "inverse"
        elif pct_top10 > 40:
            conc_nivel = "Media"
            conc_icon = "🟡"
            conc_color = "off"
        else:
            conc_nivel = "Baja"
            conc_icon = "🟢"
            conc_color = "normal"
        
        st.metric(
            label="🎯 Concentración Top 10",
            value=f"{pct_top10:.1f}%",
            delta=f"{conc_icon} {conc_nivel}",
            delta_color=conc_color,
            help=f"Los 10 beneficiarios principales concentran {pct_top10:.1f}% del volumen de {total_benef} beneficiarios totales"
        )
    else:
        st.metric(
            label="🎯 Concentración Top 10",
            value="N/A",
            help="No hay datos de beneficiarios disponibles"
        )

with row3_col4:
    # Diversificación de entidades bancarias
    if "banco_norm" in df_relevantes.columns and len(df_relevantes) > 0:
        bancos_unicos = df_relevantes['banco_norm'].nunique()
        
        # Calcular distribución
        df_bancos_dist = df_relevantes.groupby('banco_norm').size()
        if len(df_bancos_dist) > 0:
            banco_principal = df_bancos_dist.idxmax()
            pct_banco_principal = (df_bancos_dist.max() / len(df_relevantes) * 100)
            
            st.metric(
                label="🏦 Entidades Bancarias",
                value=f"{bancos_unicos}",
                delta=f"Principal: {pct_banco_principal:.1f}%",
                help=f"Diversificación bancaria - Banco principal: {banco_principal} ({pct_banco_principal:.1f}%)"
            )
        else:
            st.metric(
                label="🏦 Entidades Bancarias",
                value=f"{bancos_unicos}",
                help="Número de entidades bancarias únicas"
            )
    else:
        st.metric(
            label="🏦 Entidades Bancarias",
            value="N/A",
            help="No hay datos de bancos disponibles"
        )

with row3_col5:
    # Ratio de expansión de base (nuevos beneficiarios)
    if "fecha" in df_relevantes.columns and "beneficiario" in df_relevantes.columns and len(df_relevantes) > 0:
        df_relevantes_temp = df_relevantes.copy()
        df_relevantes_temp = df_relevantes_temp.sort_values('fecha')
        
        # Dividir en primera y segunda mitad del período
        mitad = len(df_relevantes_temp) // 2
        if mitad > 0:
            benef_primera_mitad = set(df_relevantes_temp.iloc[:mitad]['beneficiario'].unique())
            benef_segunda_mitad = set(df_relevantes_temp.iloc[mitad:]['beneficiario'].unique())
            
            benef_nuevos = len(benef_segunda_mitad - benef_primera_mitad)
            tasa_nuevos = (benef_nuevos / len(benef_segunda_mitad) * 100) if len(benef_segunda_mitad) > 0 else 0
            
            st.metric(
                label="🆕 Expansión de Base",
                value=f"{benef_nuevos}",
                delta=f"{tasa_nuevos:.1f}% nuevos",
                help="Beneficiarios nuevos en la segunda mitad del período - Indica expansión de base de clientes"
            )
        else:
            st.metric(
                label="🆕 Expansión de Base",
                value="N/A",
                delta="Datos insuficientes",
                help="Se necesitan más transacciones para calcular expansión"
            )
    else:
        st.metric(
            label="🆕 Expansión de Base",
            value="N/A",
            help="No hay datos de beneficiarios o fechas disponibles"
        )

# ============================================
# FILA 4: DÍAS PICO Y PATRONES
# ============================================
st.markdown("### 📅 Días Representativos")
row4_col1, row4_col2, row4_col3, row4_col4 = st.columns(4)

with row4_col1:
    st.metric(
        label="📅 Día con Más Transacciones",
        value=fecha_max_tx_str,
        delta=f"{max_tx_dia:,} transacciones",
        help="Fecha con el mayor número de transacciones registradas en el período"
    )

with row4_col2:
    st.metric(
        label="💵 Día con Mayor Volumen",
        value=fecha_max_monto_str,
        delta=f"{formato_moneda(max_monto_dia)}",
        help="Fecha con el mayor volumen transado en el período"
    )

with row4_col3:
    st.metric(
        label="📉 Día con Menos Transacciones",
        value=fecha_min_tx_str,
        delta=f"{min_tx_dia:,} transacciones",
        delta_color="inverse",
        help="Fecha con el menor número de transacciones registradas en el período"
    )

with row4_col4:
    st.metric(
        label="📊 Día con Menor Volumen",
        value=fecha_min_monto_str,
        delta=f"{formato_moneda(min_monto_dia)}",
        delta_color="inverse",
        help="Fecha con el menor volumen transado en el período"
    )

st.markdown("---")

# ============================================
# FILA 2: SEGMENTACIÓN Y PERFORMANCE
# ============================================
st.markdown("### 🎯 Segmentación y Desempeño")
row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)

with row2_col1:
    tendencia_icon_pn = "📈" if crecimiento_pn > 0 else "📉" if crecimiento_pn < 0 else "➡️"
    st.metric(
        label="👤 Beneficiarios Naturales",
        value=f"{benef_unicos_pn:,} únicos",
        delta=f"{tx_pn:,} TX • {frecuencia_pn:.1f} TX/benef {tendencia_icon_pn}{abs(crecimiento_pn):.1f}%",
        delta_color="normal" if crecimiento_pn >= 0 else "inverse",
        help=f"Beneficiarios únicos: {benef_unicos_pn:,}\nTransacciones totales: {tx_pn:,}\nFrecuencia promedio: {frecuencia_pn:.1f} TX por beneficiario\nTendencia: {crecimiento_pn:+.1f}% (primer vs último mes)\nVolumen: {formato_moneda(monto_pn)} ({pct_pn:.1f}%)"
    )

with row2_col2:
    tendencia_icon_pj = "📈" if crecimiento_pj > 0 else "📉" if crecimiento_pj < 0 else "➡️"
    st.metric(
        label="🏢 Beneficiarios Jurídicos",
        value=f"{benef_unicos_pj:,} únicos",
        delta=f"{tx_pj:,} TX • {frecuencia_pj:.1f} TX/benef {tendencia_icon_pj}{abs(crecimiento_pj):.1f}%",
        delta_color="normal" if crecimiento_pj >= 0 else "inverse",
        help=f"Beneficiarios únicos: {benef_unicos_pj:,}\nTransacciones totales: {tx_pj:,}\nFrecuencia promedio: {frecuencia_pj:.1f} TX por beneficiario\nTendencia: {crecimiento_pj:+.1f}% (primer vs último mes)\nVolumen: {formato_moneda(monto_pj)} ({pct_pj:.1f}%)"
    )

with row2_col3:
    st.metric(
        label="💵 Comisiones Generadas",
        value=formato_moneda(comisiones_totales),
        delta=f"Revenue del período",
        help="Total de comisiones generadas por transacciones efectivas"
    )

with row2_col4:
    st.metric(
        label="👥 Clientes Activos",
        value=f"{len(lista_clientes)}",
        delta="Originadores operando",
        help="Número total de clientes/originadores con transacciones en el período"
    )

st.markdown("---")

# ============================================
# FILA 3: GRÁFICAS DE DISTRIBUCIÓN POR CLIENTE
# ============================================
st.markdown("### 📊 Distribución por Cliente")

# Preparar datos de distribución por cliente
distribucion_clientes = []
for cliente in lista_clientes:
    info = resumen.get(cliente, {})
    distribucion_clientes.append({
        'Cliente': cliente,
        'Monto Total': info.get('monto_total', 0),
        'Transacciones': info.get('eff_tx', 0)  # Campo corregido: eff_tx
    })

df_distribucion = pd.DataFrame(distribucion_clientes)
df_distribucion = df_distribucion.sort_values('Monto Total', ascending=False)

# Crear dos columnas para las gráficas
graf_col1, graf_col2 = st.columns(2, gap="large")

with graf_col1:
    st.markdown("<h4 style='margin-bottom: 15px; color: #1c2a38;'>💰 Distribución por Montos</h4>", unsafe_allow_html=True)
    # Gráfica de barras horizontales MEJORADA para montos
    import plotly.graph_objects as go
    
    # Preparar datos
    df_montos_viz = df_distribucion.copy()
    df_montos_viz['monto_formato'] = df_montos_viz['Monto Total'].apply(
        lambda x: f"${x/1e9:.1f}B" if x >= 1e9 else f"${x/1e6:.1f}M" if x >= 1e6 else f"${x/1e3:.0f}K"
    )
    
    fig_montos = go.Figure()
    
    fig_montos.add_trace(go.Bar(
        y=df_montos_viz['Cliente'],
        x=df_montos_viz['Monto Total'],
        orientation='h',
        text=df_montos_viz['monto_formato'],
        textposition='outside',
        textfont=dict(size=14, color='#1c2a38', family='Arial, sans-serif', weight='bold'),
        marker=dict(
            color=df_montos_viz['Monto Total'],
            colorscale=[[0, '#4a90e2'], [0.5, '#5aa9d6'], [1, '#7ac8e1']],
            line=dict(color='#2d4263', width=1.5),
            opacity=0.9
        ),
        hovertemplate='<b>%{y}</b><br>' +
                      'Monto: $%{x:,.0f} COP<br>' +
                      '<extra></extra>',
        name='Volumen'
    ))
    
    fig_montos.update_layout(
        height=450,
        showlegend=False,
        margin=dict(l=10, r=80, t=60, b=60),
        plot_bgcolor='rgba(248, 249, 250, 0.5)',
        paper_bgcolor='white',
        title=dict(
            text='Volumen Transado por Cliente',
            font=dict(size=18, color='#1c2a38', family='Arial, sans-serif', weight='bold'),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title='Monto Total (COP)',
            title_font=dict(size=14, color='#666', family='Arial, sans-serif'),
            showgrid=True,
            gridcolor='rgba(200, 200, 200, 0.3)',
            showline=True,
            linewidth=2,
            linecolor='#e0e0e0',
            tickfont=dict(size=12, color='#666', family='Arial, sans-serif')
        ),
        yaxis=dict(
            title='',
            categoryorder='total ascending',
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#e0e0e0',
            tickfont=dict(size=13, color='#333', family='Arial, sans-serif', weight='bold')
        ),
        font=dict(family='Arial, sans-serif', size=13, color='#333')
    )
    
    st.plotly_chart(fig_montos, use_container_width=True)

with graf_col2:
    st.markdown("<h4 style='margin-bottom: 15px; color: #1c2a38;'>💳 Distribución por Transacciones</h4>", unsafe_allow_html=True)
    # Gráfica de barras horizontales MEJORADA para número de transacciones
    df_dist_tx = df_distribucion.sort_values('Transacciones', ascending=False)
    
    # Preparar datos
    df_tx_viz = df_dist_tx.copy()
    df_tx_viz['tx_formato'] = df_tx_viz['Transacciones'].apply(
        lambda x: f"{x/1e3:.1f}K" if x >= 1e3 else f"{int(x)}"
    )
    
    fig_tx = go.Figure()
    
    fig_tx.add_trace(go.Bar(
        y=df_tx_viz['Cliente'],
        x=df_tx_viz['Transacciones'],
        orientation='h',
        text=df_tx_viz['tx_formato'],
        textposition='outside',
        textfont=dict(size=14, color='#1c2a38', family='Arial, sans-serif', weight='bold'),
        marker=dict(
            color=df_tx_viz['Transacciones'],
            colorscale=[[0, '#2ecc71'], [0.5, '#58d68d'], [1, '#a9dfbf']],
            line=dict(color='#27ae60', width=1.5),
            opacity=0.9
        ),
        hovertemplate='<b>%{y}</b><br>' +
                      'Transacciones: %{x:,}<br>' +
                      '<extra></extra>',
        name='Transacciones'
    ))
    
    fig_tx.update_layout(
        height=450,
        showlegend=False,
        margin=dict(l=10, r=80, t=60, b=60),
        plot_bgcolor='rgba(248, 249, 250, 0.5)',
        paper_bgcolor='white',
        title=dict(
            text='Número de Transacciones por Cliente',
            font=dict(size=18, color='#1c2a38', family='Arial, sans-serif', weight='bold'),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title='Cantidad de Transacciones',
            title_font=dict(size=14, color='#666', family='Arial, sans-serif'),
            showgrid=True,
            gridcolor='rgba(200, 200, 200, 0.3)',
            showline=True,
            linewidth=2,
            linecolor='#e0e0e0',
            tickfont=dict(size=12, color='#666', family='Arial, sans-serif')
        ),
        yaxis=dict(
            title='',
            categoryorder='total ascending',
            showgrid=False,
            showline=True,
            linewidth=2,
            linecolor='#e0e0e0',
            tickfont=dict(size=13, color='#333', family='Arial, sans-serif', weight='bold')
        ),
        font=dict(family='Arial, sans-serif', size=13, color='#333')
    )
    
    st.plotly_chart(fig_tx, use_container_width=True)

st.markdown("---")


# =========================
# Tarjetas simples por cliente
# =========================
st.markdown("### 👥 Resumen por Cliente")
st.markdown("<p style='color: gray; margin-top: -10px;'>Vista rápida de volúmenes y estados por cliente</p>", unsafe_allow_html=True)

# Obtener número de columnas desde configuración
num_cols_tarjetas = tc.get('columnas', 4)

# Agregar clase CSS para identificar las tarjetas
st.markdown('<div class="tarjeta-cliente-container">', unsafe_allow_html=True)

for i in range(0, len(lista_clientes), num_cols_tarjetas):
    cols = st.columns(num_cols_tarjetas, gap="medium")
    for j, col in enumerate(cols):
        if i + j >= len(lista_clientes):
            continue
        cliente = lista_clientes[i + j]
        r = resumen.get(cliente)
        if not r:
            continue

        with col:
            container = st.container(border=True)
            with container:
                total_tx = r["eff_tx"]
                total_monto = r["monto_total"]
                promedio_tx = (total_monto / total_tx) if total_tx > 0 else 0

                # Tipos de transacción (sobre todo el cliente, no solo efectivas)
                tipos_dict = {}
                dfc = r["df"]
                if "tipo_tx_norm" in dfc.columns:
                    for tipo, count in dfc["tipo_tx_norm"].value_counts(dropna=False).items():
                        t = tipo or "DESCONOCIDO"
                        if "FONDO" in t or "FONDEO" in t:
                            tipos_dict["Fondeo"] = tipos_dict.get("Fondeo", 0) + int(count)
                        elif "CREDITO" in t or "CRÉDITO" in t:
                            tipos_dict["Crédito"] = tipos_dict.get("Crédito", 0) + int(count)
                        elif "DEBITO" in t or "DÉBITO" in t:
                            tipos_dict["Débito"] = tipos_dict.get("Débito", 0) + int(count)
                        else:
                            tipos_dict["Otro"] = tipos_dict.get("Otro", 0) + int(count)

                # Beneficiarios PN/PJ (sobre TX efectivas)
                df_eff = r["df_eff"]
                pn_count = int((df_eff["tipo_persona_benef"] == "Natural").sum()) if "tipo_persona_benef" in df_eff.columns else 0
                pj_count = int((df_eff["tipo_persona_benef"] == "Jurídica").sum()) if "tipo_persona_benef" in df_eff.columns else 0

                # Estados (sobre todo el cliente)
                metricas_estado = {}
                if "estado_norm" in dfc.columns:
                    vc = dfc["estado_norm"].value_counts(dropna=False)
                    for estado, cnt in vc.items():
                        est = estado or "DESCONOCIDO"
                        df_est = dfc[dfc["estado_norm"].fillna("DESCONOCIDO") == est]
                        metricas_estado[est] = {
                            "tx": int(cnt),
                            "monto": float(df_est["monto_cop"].sum()) if "monto_cop" in df_est.columns else 0.0,
                        }

                # Header (escape cliente) - Tamaño desde configuración
                st.markdown(
                    f"""
                    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                padding: {tc['padding']};
                                border-radius: 10px;
                                margin-bottom: 14px;
                                box-shadow: 0 3px 10px rgba(102,126,234,0.3);'>
                        <h3 style='margin: 0; color: white; font-size: {tc['header']}px; font-weight: 500; letter-spacing: 0.3px;'>🏢 {_safe(cliente)}</h3>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Métricas principales con labels más cortos
                mcols = st.columns(3)
                with mcols[0]:
                    st.metric("💳 TX", f"{total_tx:,}", help="Transacciones Efectivas")
                with mcols[1]:
                    st.metric("💰 Volumen", formato_moneda(total_monto).replace(" COP", ""), help="Volumen Total en COP")
                with mcols[2]:
                    st.metric("📊 Promedio", formato_moneda(promedio_tx).replace(" COP", ""), help="Promedio por TX")

                with st.expander("📊 Ver detalle operativo", expanded=False):
                    if tipos_dict:
                        st.markdown("**📋 Tipos de Transacción**")
                        tcols = st.columns(len(tipos_dict))
                        iconos = {"Fondeo": "💰", "Crédito": "💳", "Débito": "🏧", "Otro": "📊"}
                        for idx_tipo, (tipo, count) in enumerate(tipos_dict.items()):
                            with tcols[idx_tipo]:
                                st.metric(f"{iconos.get(tipo,'📊')} {tipo}", f"{count:,}")

                    if pn_count > 0 or pj_count > 0:
                        st.markdown("---")
                        st.markdown("**👥 Beneficiarios (TX efectivas)**")
                        bcols = st.columns(2)
                        if pn_count > 0:
                            with bcols[0]:
                                pn_pct = (pn_count / total_tx * 100) if total_tx else 0
                                st.metric("👤 Naturales", f"{pn_count:,}", delta=f"{pn_pct:.1f}%")
                        if pj_count > 0:
                            with bcols[1]:
                                pj_pct = (pj_count / total_tx * 100) if total_tx else 0
                                st.metric("🏢 Jurídicos", f"{pj_count:,}", delta=f"{pj_pct:.1f}%")

                    if metricas_estado:
                        st.markdown("---")
                        st.markdown("**📋 Estados de Transacciones**")
                        # Mostrar solo los 3 estados más importantes con texto desde configuración
                        estados_ordenados = sorted(metricas_estado.items(), key=lambda x: x[1]['tx'], reverse=True)[:3]
                        for estado, datos in estados_ordenados:
                            st.markdown(
                                f"<p style='font-size: {tc['texto']}px; margin: 5px 0; line-height: 1.4; font-weight: 400;'>"
                                f"<strong style='color: #333; font-weight: 500;'>{estado}:</strong> "
                                f"<span style='color: #1f77b4; font-weight: 400;'>{datos['tx']:,} TX</span> | "
                                f"<span style='color: #2ca02c; font-weight: 400;'>{formato_moneda(datos['monto']).replace(' COP', '')}</span>"
                                f"</p>",
                                unsafe_allow_html=True
                            )
                        if len(metricas_estado) > 3:
                            st.caption(f"... y {len(metricas_estado) - 3} estados más")

    if i + num_cols_tarjetas < len(lista_clientes):
        st.markdown(
            """
            <div style='border-bottom: 2px dashed #ccc;
                        margin: 30px 0 40px 0;
                        opacity: 0.5;'></div>
            """,
            unsafe_allow_html=True,
        )

# Cerrar el contenedor de tarjetas
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")


# =========================
# Dashboard detallado
# =========================
st.header("📊 Dashboard Detallado - Análisis Completo")
st.markdown("---")


# =========================
# Tabs por cliente (detallado)
# =========================
st.markdown("### 👥 Información General de Clientes")

# =========================
# FILTRO DE FECHAS GLOBAL
# =========================
st.markdown("#### 📅 Filtro de Período")

# Obtener rango de fechas disponible
if "fecha" in df_completo.columns:
    fechas_validas = df_completo["fecha"].dropna()
    # Filtrar fechas razonables (desde año 2000)
    fecha_minima_valida = pd.Timestamp('2000-01-01')
    fechas_validas = fechas_validas[fechas_validas >= fecha_minima_valida]
    
    if len(fechas_validas) > 0:
        fecha_min_global = fechas_validas.min().date()
        fecha_max_global = fechas_validas.max().date()
    else:
        fecha_min_global = pd.Timestamp.now().date()
        fecha_max_global = pd.Timestamp.now().date()
else:
    fecha_min_global = pd.Timestamp.now().date()
    fecha_max_global = pd.Timestamp.now().date()

col_fecha1, col_fecha2, col_fecha3 = st.columns([2, 2, 1])

with col_fecha1:
    fecha_inicio = st.date_input(
        "📅 Fecha Inicio",
        value=fecha_min_global,
        min_value=fecha_min_global,
        max_value=fecha_max_global,
        help="Selecciona la fecha de inicio del período a analizar",
        key="fecha_inicio_global"
    )

with col_fecha2:
    fecha_fin = st.date_input(
        "📅 Fecha Fin",
        value=fecha_max_global,
        min_value=fecha_min_global,
        max_value=fecha_max_global,
        help="Selecciona la fecha de fin del período a analizar",
        key="fecha_fin_global"
    )

with col_fecha3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Restablecer", use_container_width=True, help="Restablecer al rango completo de fechas"):
        st.rerun()

# Validar que fecha_inicio <= fecha_fin
if fecha_inicio > fecha_fin:
    st.error("⚠️ La fecha de inicio no puede ser posterior a la fecha de fin")
    st.stop()

# Convertir a Timestamp para comparación
fecha_inicio_ts = pd.Timestamp(fecha_inicio)
fecha_fin_ts = pd.Timestamp(fecha_fin)

# Mostrar información del filtro
dias_seleccionados = (fecha_fin_ts - fecha_inicio_ts).days + 1
st.info(f"📊 Período seleccionado: **{dias_seleccionados} días** ({fecha_inicio.strftime('%d/%m/%Y')} - {fecha_fin.strftime('%d/%m/%Y')})")

st.markdown("---")
st.markdown("#### 🟦 Capa 1: Datos Transaccionales")
st.caption("Métricas operativas y comportamiento del cliente")

tabs = st.tabs([f"📋 {c}" for c in lista_clientes])

for idx, cliente in enumerate(lista_clientes):
    with tabs[idx]:
        r = resumen.get(cliente)
        if not r:
            st.info("Sin datos para este cliente.")
            continue

        # APLICAR FILTRO DE FECHAS
        df_cliente = r["df"]
        df_cliente_efectivo = r["df_eff"]
        
        # Filtrar por rango de fechas seleccionado
        if "fecha" in df_cliente.columns:
            df_cliente = df_cliente[
                (df_cliente['fecha'] >= fecha_inicio_ts) & 
                (df_cliente['fecha'] <= fecha_fin_ts)
            ].copy()
            
            df_cliente_efectivo = df_cliente_efectivo[
                (df_cliente_efectivo['fecha'] >= fecha_inicio_ts) & 
                (df_cliente_efectivo['fecha'] <= fecha_fin_ts)
            ].copy()
        
        # Verificar si hay datos en el período
        if len(df_cliente) == 0:
            st.warning(f"⚠️ No hay transacciones para {cliente} en el período seleccionado")
            continue

        # RECALCULAR MÉTRICAS con datos filtrados
        total_tx_cliente = len(df_cliente)
        tx_efectivas_cliente = len(df_cliente_efectivo)
        monto_total_cliente = float(df_cliente_efectivo["monto_cop"].sum()) if "monto_cop" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0 else 0.0
        monto_promedio_cliente = float(df_cliente_efectivo["monto_cop"].mean()) if "monto_cop" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0 else 0.0
        tasa_exito_cliente = (tx_efectivas_cliente / total_tx_cliente * 100) if total_tx_cliente > 0 else 0.0
        
        # Fechas del período filtrado
        if "fecha" in df_cliente.columns and len(df_cliente) > 0:
            fechas_validas = df_cliente["fecha"].dropna()
            fecha_minima = pd.Timestamp('2000-01-01')
            fechas_validas = fechas_validas[fechas_validas >= fecha_minima]
            primera_tx = fechas_validas.min() if len(fechas_validas) > 0 else pd.NaT
            ultima_tx = fechas_validas.max() if len(fechas_validas) > 0 else pd.NaT
        else:
            primera_tx = pd.NaT
            ultima_tx = pd.NaT
        
        dias_activo = int((ultima_tx - primera_tx).days) if pd.notna(primera_tx) and pd.notna(ultima_tx) else 0

        # Header cliente
        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 15px; color: white; margin-bottom: 20px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                <h2 style='margin: 0; font-size: 28px;'>🏢 {_safe(cliente)}</h2>
                <p style='margin: 5px 0 0 0; opacity: 0.9; font-size: 14px;'>
                    Período: {primera_tx.strftime('%d/%m/%Y') if pd.notna(primera_tx) else 'N/A'} - {ultima_tx.strftime('%d/%m/%Y') if pd.notna(ultima_tx) else 'N/A'}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Métricas - FILA 1: Transaccionales y Financieras (5 columnas)
        row1_col1, row1_col2, row1_col3, row1_col4, row1_col5 = st.columns(5)
        
        with row1_col1:
            st.metric(
                label="📊 TX Efectivas",
                value=f"{tx_efectivas_cliente:,}",
                delta=f"De {total_tx_cliente:,} totales",
                help="Transacciones efectivas del cliente"
            )
        
        with row1_col2:
            st.metric(
                label="💰 Monto Total",
                value=formato_moneda(monto_total_cliente),
                delta=f"Volumen transado",
                help="Volumen total de transacciones efectivas"
            )
        
        with row1_col3:
            st.metric(
                label="📈 Promedio TX",
                value=formato_moneda(monto_promedio_cliente),
                delta=f"Ticket promedio",
                help="Monto promedio por transacción efectiva"
            )
        
        with row1_col4:
            st.metric(
                label="✅ Efectividad",
                value=f"{tasa_exito_cliente:.1f}%",
                delta=f"Tasa de éxito",
                help="Porcentaje de transacciones exitosas"
            )
        
        with row1_col5:
            comision_total = 0
            if "comision_cop" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                comision_total = float(df_cliente_efectivo["comision_cop"].sum())
            
            st.metric(
                label="💵 Comisiones",
                value=formato_moneda(comision_total),
                delta=f"Total generado",
                help="Comisiones totales generadas por el cliente"
            )

        # FILA 2: Temporales y Beneficiarios (5 columnas)
        row2_col1, row2_col2, row2_col3, row2_col4, row2_col5 = st.columns(5)
        
        with row2_col1:
            st.metric(
                label="📅 Días Activo",
                value=f"{dias_activo}",
                delta=f"Período de actividad",
                help="Días transcurridos desde la primera transacción"
            )
        
        with row2_col2:
            st.metric(
                label="🕐 Primera TX",
                value=primera_tx.strftime('%d/%m/%Y') if pd.notna(primera_tx) else 'N/A',
                delta=f"Fecha de inicio",
                help="Fecha de la primera transacción registrada"
            )
        
        with row2_col3:
            st.metric(
                label="🕐 Última TX",
                value=ultima_tx.strftime('%d/%m/%Y') if pd.notna(ultima_tx) else 'N/A',
                delta=f"Actividad reciente",
                help="Fecha de la última transacción registrada"
            )
        
        with row2_col4:
            # Calcular beneficiarios únicos para personas naturales
            beneficiarios_naturales = 0
            if "beneficiario_canonico" in df_cliente_efectivo.columns and "tipo_persona_benef" in df_cliente_efectivo.columns:
                beneficiarios_naturales = df_cliente_efectivo[
                    df_cliente_efectivo["tipo_persona_benef"] == "Natural"
                ]["beneficiario_canonico"].nunique()
            
            st.metric(
                label="👤 Beneficiarios Naturales",
                value=f"{beneficiarios_naturales:,}",
                delta=f"Únicos",
                help="Número de beneficiarios únicos de tipo Persona Natural en el período"
            )
        
        with row2_col5:
            # Calcular beneficiarios únicos para personas jurídicas
            beneficiarios_juridicas = 0
            if "beneficiario_canonico" in df_cliente_efectivo.columns and "tipo_persona_benef" in df_cliente_efectivo.columns:
                beneficiarios_juridicas = df_cliente_efectivo[
                    df_cliente_efectivo["tipo_persona_benef"] == "Jurídica"
                ]["beneficiario_canonico"].nunique()
            
            st.metric(
                label="🏢 Beneficiarios Jurídicos",
                value=f"{beneficiarios_juridicas:,}",
                delta=f"Únicos",
                help="Número de beneficiarios únicos de tipo Persona Jurídica en el período"
            )

        st.markdown("---")

        # ============================================
        # RESUMEN DE ACTIVIDAD - ANÁLISIS COMPLETO
        # ============================================
        st.markdown("#### 📊 Resumen de Actividad")

        # ============================================
        # 1. ANÁLISIS TEMPORAL
        # ============================================
        st.markdown("##### 📅 Distribución Temporal")

        col_temp1, col_temp2, col_temp3 = st.columns([1, 1, 2.2])

        with col_temp1:
            # Actividad por día de la semana
            if "fecha" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                df_dias = df_cliente_efectivo.copy()
                df_dias['dia_semana'] = df_dias['fecha'].dt.day_name()
                dias_esp = {
                    'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 
                    'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
                }
                
                tx_por_dia = df_dias['dia_semana'].value_counts()
                if len(tx_por_dia) > 0:
                    dia_max = tx_por_dia.idxmax()
                    dia_min = tx_por_dia.idxmin()
                    
                    st.metric(
                        "🔝 Día más activo", 
                        dias_esp.get(dia_max, dia_max), 
                        f"{tx_por_dia[dia_max]:,} TX",
                        help="Día de la semana con mayor cantidad de transacciones"
                    )
                    st.metric(
                        "📉 Día menos activo", 
                        dias_esp.get(dia_min, dia_min), 
                        f"{tx_por_dia[dia_min]:,} TX",
                        help="Día de la semana con menor cantidad de transacciones"
                    )

        with col_temp2:
            # Tendencia mensual
            if "fecha" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                df_meses = df_cliente_efectivo.copy()
                df_meses['mes'] = df_meses['fecha'].dt.to_period('M')
                tx_por_mes = df_meses.groupby('mes').size()
                
                if len(tx_por_mes) >= 2:
                    variacion = ((tx_por_mes.iloc[-1] - tx_por_mes.iloc[-2]) / tx_por_mes.iloc[-2] * 100)
                    st.metric(
                        "📈 Tendencia mensual", 
                        f"{variacion:+.1f}%", 
                        f"Último mes: {tx_por_mes.iloc[-1]:,} TX",
                        help="Variación porcentual del último mes vs mes anterior"
                    )
                
                st.metric(
                    "📊 Promedio mensual", 
                    f"{tx_por_mes.mean():,.0f} TX", 
                    f"Total: {len(tx_por_mes)} meses",
                    help="Promedio de transacciones por mes en el período"
                )

        with col_temp3:
            # GRÁFICA MEJORADA: Días más representativos (Top 10)
            st.markdown("<h4 style='margin-bottom: 15px; color: #1c2a38;'>📊 Días más Representativos</h4>", unsafe_allow_html=True)
            if "fecha" in df_cliente_efectivo.columns and "monto_cop" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                # Agrupar por fecha y calcular monto total por día
                df_dias_repr = df_cliente_efectivo.groupby('fecha').agg({
                    'monto_cop': 'sum',
                    'tx_id': 'count'
                }).reset_index()
                
                # Obtener top 10 días con mayor monto
                df_top_dias = df_dias_repr.nlargest(10, 'monto_cop')
                df_top_dias = df_top_dias.sort_values('fecha')
                
                # Formatear fecha para visualización mejorada
                df_top_dias['fecha_str'] = df_top_dias['fecha'].dt.strftime('%d %b')
                df_top_dias['monto_formato'] = df_top_dias['monto_cop'].apply(lambda x: f"${x/1e6:.1f}M" if x >= 1e6 else f"${x/1e3:.0f}K")
                
                if len(df_top_dias) > 0:
                    import plotly.graph_objects as go
                    
                    # Colores corporativos: gradiente azul-verde
                    colores = ['#1c2a38', '#2d4263', '#3e5a8e', '#4a7ba7', '#5a9fc7', 
                               '#6ab7d4', '#7ac8e1', '#8ad9ec', '#9ae4f5', '#aaf0ff']
                    
                    fig_dias = go.Figure()
                    
                    fig_dias.add_trace(go.Bar(
                        x=df_top_dias['fecha_str'],
                        y=df_top_dias['monto_cop'],
                        text=df_top_dias['monto_formato'],
                        textposition='outside',
                        textfont=dict(size=13, color='#1c2a38', family='Arial, sans-serif', weight='bold'),
                        marker=dict(
                            color=df_top_dias['monto_cop'],
                            colorscale=[[0, '#4a90e2'], [0.5, '#5aa9d6'], [1, '#7ac8e1']],
                            line=dict(color='#2d4263', width=1.5),
                            opacity=0.9
                        ),
                        hovertemplate='<b>%{x}</b><br>' +
                                      'Monto: $%{y:,.0f} COP<br>' +
                                      '<extra></extra>',
                        name='Monto'
                    ))
                    
                    # Agregar etiquetas de transacciones como anotaciones
                    for idx, row in df_top_dias.iterrows():
                        fig_dias.add_annotation(
                            x=row['fecha_str'],
                            y=row['monto_cop'] * 0.5,
                            text=f"{int(row['tx_id'])} TX",
                            showarrow=False,
                            font=dict(size=11, color='white', family='Arial, sans-serif', weight='bold'),
                            bgcolor='rgba(45, 66, 99, 0.8)',
                            borderpad=4,
                            bordercolor='white',
                            borderwidth=1
                        )
                    
                    fig_dias.update_layout(
                        height=270,
                        showlegend=False,
                        margin=dict(l=50, r=30, t=40, b=50),
                        plot_bgcolor='rgba(248, 249, 250, 0.5)',
                        paper_bgcolor='white',
                        xaxis=dict(
                            showgrid=False,
                            showline=True,
                            linewidth=2,
                            linecolor='#e0e0e0',
                            tickfont=dict(size=12, color='#333', family='Arial, sans-serif'),
                            title=dict(text='', font=dict(size=13, color='#666'))
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor='rgba(200, 200, 200, 0.3)',
                            showline=True,
                            linewidth=2,
                            linecolor='#e0e0e0',
                            tickfont=dict(size=11, color='#666', family='Arial, sans-serif'),
                            title=dict(text='Volumen (COP)', font=dict(size=13, color='#666', family='Arial, sans-serif'))
                        ),
                        font=dict(family='Arial, sans-serif', size=12, color='#333')
                    )
                    
                    st.plotly_chart(fig_dias, use_container_width=True)
                    
                    # Nota con observaciones mejorada
                    total_top10 = df_top_dias['monto_cop'].sum()
                    pct_top10 = (total_top10 / monto_total_cliente * 100) if monto_total_cliente > 0 else 0
                    tx_top10 = df_top_dias['tx_id'].sum()
                    
                    insight_color = '#d32f2f' if pct_top10 > 50 else '#f57c00' if pct_top10 > 30 else '#388e3c'
                    insight_icon = '🔴' if pct_top10 > 50 else '🟠' if pct_top10 > 30 else '🟢'
                    insight_text = 'muy alta concentración' if pct_top10 > 50 else 'alta concentración' if pct_top10 > 30 else 'distribución equilibrada'
                    
                    st.markdown(
                        f"""
                        <div style='background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                                    padding: 12px 15px; border-radius: 8px; border-left: 4px solid {insight_color};
                                    margin-top: 10px;'>
                            <p style='margin: 0; font-size: 13px; color: #495057; line-height: 1.6;'>
                                {insight_icon} <strong>Análisis:</strong> Los 10 días pico concentran 
                                <strong style='color: {insight_color};'>{formato_moneda(total_top10)}</strong> 
                                ({pct_top10:.1f}% del volumen total) con <strong>{tx_top10:,} TX</strong>. 
                                Indica <strong style='color: {insight_color};'>{insight_text}</strong> de la operación.
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # Segunda fila: Evolución Temporal MEJORADA (TX + Volumen)
        st.markdown("")
        st.markdown("<h4 style='margin-bottom: 15px; margin-top: 20px; color: #1c2a38;'>📈 Evolución de Transacciones en el Tiempo</h4>", unsafe_allow_html=True)
        
        if "fecha" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
            df_timeline = df_cliente_efectivo.copy()
            df_timeline['fecha_simple'] = df_timeline['fecha'].dt.date
            tx_por_fecha = df_timeline.groupby('fecha_simple').agg({
                'tx_id': 'count',
                'monto_cop': 'sum'
            }).reset_index()
            tx_por_fecha.columns = ['fecha', 'transacciones', 'monto']
            
            if len(tx_por_fecha) > 0:
                # Gráfica dual MEJORADA: TX + Monto
                from plotly.subplots import make_subplots
                import plotly.graph_objects as go
                
                fig_timeline = make_subplots(
                    rows=1, cols=1,
                    specs=[[{"secondary_y": True}]]
                )
                
                # Barras con estilo corporativo
                fig_timeline.add_trace(
                    go.Bar(
                        x=tx_por_fecha['fecha'],
                        y=tx_por_fecha['transacciones'],
                        name="Transacciones",
                        marker=dict(
                            color='#4a90e2',
                            opacity=0.7,
                            line=dict(color='#2d4263', width=0.5)
                        ),
                        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>' +
                                      'Transacciones: %{y:,}<br>' +
                                      '<extra></extra>'
                    ),
                    secondary_y=False
                )
                
                # Línea con marcadores mejorada
                fig_timeline.add_trace(
                    go.Scatter(
                        x=tx_por_fecha['fecha'],
                        y=tx_por_fecha['monto'],
                        name="Volumen (COP)",
                        line=dict(color='#2ecc71', width=3, shape='spline'),
                        mode='lines+markers',
                        marker=dict(size=6, color='#27ae60', line=dict(color='white', width=2)),
                        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>' +
                                      'Volumen: $%{y:,.0f} COP<br>' +
                                      '<extra></extra>'
                    ),
                    secondary_y=True
                )
                
                fig_timeline.update_layout(
                    height=320,
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        font=dict(size=13, color='#333', family='Arial, sans-serif'),
                        bgcolor='rgba(255, 255, 255, 0.9)',
                        bordercolor='#e0e0e0',
                        borderwidth=1
                    ),
                    margin=dict(l=60, r=60, t=50, b=50),
                    plot_bgcolor='rgba(248, 249, 250, 0.5)',
                    paper_bgcolor='white',
                    font=dict(family='Arial, sans-serif', size=12, color='#333')
                )
                
                # Ejes mejorados
                fig_timeline.update_xaxes(
                    title_text="",
                    showgrid=True,
                    gridcolor='rgba(200, 200, 200, 0.2)',
                    showline=True,
                    linewidth=2,
                    linecolor='#e0e0e0',
                    tickfont=dict(size=11, color='#666', family='Arial, sans-serif')
                )
                
                fig_timeline.update_yaxes(
                    title_text="Transacciones",
                    title_font=dict(size=13, color='#4a90e2', family='Arial, sans-serif'),
                    showgrid=True,
                    gridcolor='rgba(74, 144, 226, 0.1)',
                    showline=True,
                    linewidth=2,
                    linecolor='#4a90e2',
                    tickfont=dict(size=11, color='#4a90e2', family='Arial, sans-serif'),
                    secondary_y=False
                )
                
                fig_timeline.update_yaxes(
                    title_text="Volumen (COP)",
                    title_font=dict(size=13, color='#2ecc71', family='Arial, sans-serif'),
                    showgrid=False,
                    showline=True,
                    linewidth=2,
                    linecolor='#2ecc71',
                    tickfont=dict(size=11, color='#2ecc71', family='Arial, sans-serif'),
                    secondary_y=True
                )
                
                st.plotly_chart(fig_timeline, use_container_width=True)

        st.markdown("---")

        # ============================================
        # 2. CONCENTRACIÓN DE OPERACIONES
        # ============================================
        st.markdown("##### 🎯 Concentración de Operaciones")

        col_conc1, col_conc2, col_conc3 = st.columns(3)

        with col_conc1:
            st.markdown("**👤 Top 5 Personas Naturales**")
            if "beneficiario" in df_cliente_efectivo.columns and "tipo_persona_benef" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                df_pn = df_cliente_efectivo[df_cliente_efectivo['tipo_persona_benef'] == 'Natural'].copy()
                if len(df_pn) > 0:
                    df_top_pn = df_pn.groupby('beneficiario').agg({
                        'monto_cop': 'sum',
                        'tx_id': 'count'
                    }).sort_values('monto_cop', ascending=False).head(5)
                    
                    for idx, (benef, row) in enumerate(df_top_pn.iterrows(), 1):
                        pct = (row['monto_cop'] / monto_total_cliente * 100) if monto_total_cliente > 0 else 0
                        benef_display = _safe(str(benef)[:25]) + ('...' if len(str(benef)) > 25 else '')
                        st.write(f"{idx}. **{benef_display}**")
                        st.caption(f"   💰 {formato_moneda(row['monto_cop'])} ({pct:.1f}%)")
                        st.caption(f"   💳 {int(row['tx_id']):,} TX")
                else:
                    st.info("Sin TX a Personas Naturales")
            else:
                st.info("Sin datos de tipo de persona")

        with col_conc2:
            st.markdown("**🏢 Top 5 Personas Jurídicas**")
            if "beneficiario" in df_cliente_efectivo.columns and "tipo_persona_benef" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                df_pj = df_cliente_efectivo[df_cliente_efectivo['tipo_persona_benef'] == 'Jurídica'].copy()
                if len(df_pj) > 0:
                    df_top_pj = df_pj.groupby('beneficiario').agg({
                        'monto_cop': 'sum',
                        'tx_id': 'count'
                    }).sort_values('monto_cop', ascending=False).head(5)
                    
                    for idx, (benef, row) in enumerate(df_top_pj.iterrows(), 1):
                        pct = (row['monto_cop'] / monto_total_cliente * 100) if monto_total_cliente > 0 else 0
                        benef_display = _safe(str(benef)[:25]) + ('...' if len(str(benef)) > 25 else '')
                        st.write(f"{idx}. **{benef_display}**")
                        st.caption(f"   💰 {formato_moneda(row['monto_cop'])} ({pct:.1f}%)")
                        st.caption(f"   💳 {int(row['tx_id']):,} TX")
                else:
                    st.info("Sin TX a Personas Jurídicas")
            else:
                st.info("Sin datos de tipo de persona")

        with col_conc3:
            st.markdown("**🏦 Top 5 Bancos Receptores**")
            if "banco_norm" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                df_top_bancos = df_cliente_efectivo.groupby('banco_norm').agg({
                    'monto_cop': 'sum',
                    'tx_id': 'count'
                }).sort_values('monto_cop', ascending=False).head(5)
                
                for idx, (banco, row) in enumerate(df_top_bancos.iterrows(), 1):
                    pct = (row['monto_cop'] / monto_total_cliente * 100) if monto_total_cliente > 0 else 0
                    banco_display = _safe(str(banco)[:25]) + ('...' if len(str(banco)) > 25 else '')
                    st.write(f"{idx}. **{banco_display}**")
                    st.caption(f"   💰 {formato_moneda(row['monto_cop'])} ({pct:.1f}%)")
                    st.caption(f"   💳 {int(row['tx_id']):,} TX")
            else:
                st.info("Sin datos de bancos")

        st.markdown("---")

        # ============================================
        # 2B. ANÁLISIS DE INACTIVIDAD Y BAJA ACTIVIDAD
        # ============================================
        st.markdown("##### ⚠️ Beneficiarios Inactivos y Baja Actividad")
        
        if "beneficiario" in df_cliente_efectivo.columns and "fecha" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
            # Calcular última transacción por beneficiario
            df_benef_actividad = df_cliente_efectivo.groupby('beneficiario').agg({
                'fecha': ['min', 'max', 'count'],
                'monto_cop': ['sum', 'mean']
            })
            
            df_benef_actividad.columns = ['primera_tx', 'ultima_tx', 'cantidad_tx', 'monto_total', 'monto_promedio']
            df_benef_actividad = df_benef_actividad.reset_index()
            
            # Calcular días desde última transacción
            fecha_max_periodo = df_cliente_efectivo['fecha'].max()
            df_benef_actividad['dias_sin_actividad'] = (fecha_max_periodo - df_benef_actividad['ultima_tx']).dt.days
            
            # Clasificar beneficiarios
            umbral_inactividad = 90  # días
            umbral_baja_actividad_tx = 3  # menos de 3 TX
            umbral_bajo_monto = df_benef_actividad['monto_promedio'].quantile(0.25)  # 25% más bajo
            
            # Beneficiarios inactivos (sin actividad en 90+ días)
            benef_inactivos = df_benef_actividad[df_benef_actividad['dias_sin_actividad'] >= umbral_inactividad].copy()
            
            # Beneficiarios con baja actividad (pocas TX)
            benef_baja_actividad = df_benef_actividad[
                (df_benef_actividad['cantidad_tx'] <= umbral_baja_actividad_tx) & 
                (df_benef_actividad['dias_sin_actividad'] < umbral_inactividad)
            ].copy()
            
            # Beneficiarios con bajos montos
            benef_bajos_montos = df_benef_actividad[
                (df_benef_actividad['monto_promedio'] <= umbral_bajo_monto) &
                (df_benef_actividad['dias_sin_actividad'] < umbral_inactividad)
            ].copy()
            
            # Métricas generales
            col_inact1, col_inact2, col_inact3, col_inact4 = st.columns(4)
            
            with col_inact1:
                total_beneficiarios = len(df_benef_actividad)
                st.metric(
                    label="👥 Total Beneficiarios",
                    value=f"{total_beneficiarios:,}",
                    delta="Base completa",
                    help="Número total de beneficiarios únicos en el período"
                )
            
            with col_inact2:
                pct_inactivos = (len(benef_inactivos) / total_beneficiarios * 100) if total_beneficiarios > 0 else 0
                st.metric(
                    label="😴 Inactivos (90+ días)",
                    value=f"{len(benef_inactivos):,}",
                    delta=f"{pct_inactivos:.1f}% del total",
                    delta_color="inverse",
                    help=f"Beneficiarios sin transacciones en los últimos {umbral_inactividad} días"
                )
            
            with col_inact3:
                pct_baja_act = (len(benef_baja_actividad) / total_beneficiarios * 100) if total_beneficiarios > 0 else 0
                st.metric(
                    label="📉 Baja Actividad",
                    value=f"{len(benef_baja_actividad):,}",
                    delta=f"{pct_baja_act:.1f}% del total",
                    delta_color="inverse",
                    help=f"Beneficiarios con ≤{umbral_baja_actividad_tx} transacciones (activos)"
                )
            
            with col_inact4:
                pct_bajos_montos = (len(benef_bajos_montos) / total_beneficiarios * 100) if total_beneficiarios > 0 else 0
                st.metric(
                    label="💸 Bajos Montos",
                    value=f"{len(benef_bajos_montos):,}",
                    delta=f"{pct_bajos_montos:.1f}% del total",
                    delta_color="off",
                    help=f"Beneficiarios con monto promedio en el 25% inferior (≤{formato_moneda(umbral_bajo_monto)})"
                )
            
            # Detalles con DATAFRAMES INTERACTIVOS
            col_det1, col_det2, col_det3 = st.columns(3)
            
            with col_det1:
                if len(benef_inactivos) > 0:
                    with st.expander(f"📋 Ver Inactivos ({len(benef_inactivos)})", expanded=False):
                        st.caption(f"**Listado completo de {len(benef_inactivos)} beneficiarios inactivos:**")
                        
                        # Preparar dataframe para visualización
                        df_inactivos_display = benef_inactivos.sort_values('dias_sin_actividad', ascending=False).copy()
                        
                        # Formatear columnas para mejor visualización
                        df_inactivos_display['Beneficiario'] = df_inactivos_display['beneficiario'].astype(str)
                        df_inactivos_display['Última TX'] = df_inactivos_display['ultima_tx'].dt.strftime('%d/%m/%Y')
                        df_inactivos_display['Primera TX'] = df_inactivos_display['primera_tx'].dt.strftime('%d/%m/%Y')
                        df_inactivos_display['Días Inactivo'] = df_inactivos_display['dias_sin_actividad'].astype(int)
                        df_inactivos_display['TX Históricas'] = df_inactivos_display['cantidad_tx'].astype(int)
                        df_inactivos_display['Monto Total'] = df_inactivos_display['monto_total'].apply(lambda x: f"${x:,.0f}")
                        df_inactivos_display['Monto Promedio'] = df_inactivos_display['monto_promedio'].apply(lambda x: f"${x:,.0f}")
                        
                        # Seleccionar y ordenar columnas
                        df_display = df_inactivos_display[[
                            'Beneficiario', 
                            'Días Inactivo',
                            'Última TX',
                            'Primera TX',
                            'TX Históricas',
                            'Monto Total',
                            'Monto Promedio'
                        ]]
                        
                        # Mostrar dataframe interactivo con configuración mejorada
                        st.dataframe(
                            df_display,
                            use_container_width=True,
                            height=400,
                            hide_index=True,
                            column_config={
                                "Beneficiario": st.column_config.TextColumn(
                                    "Beneficiario",
                                    help="Nombre del beneficiario",
                                    width="large"
                                ),
                                "Días Inactivo": st.column_config.NumberColumn(
                                    "Días Inactivo",
                                    help="Días desde última transacción",
                                    format="%d días"
                                ),
                                "Última TX": st.column_config.TextColumn(
                                    "Última TX",
                                    help="Fecha de última transacción"
                                ),
                                "Primera TX": st.column_config.TextColumn(
                                    "Primera TX",
                                    help="Fecha de primera transacción"
                                ),
                                "TX Históricas": st.column_config.NumberColumn(
                                    "TX Históricas",
                                    help="Total de transacciones realizadas",
                                    format="%d TX"
                                ),
                                "Monto Total": st.column_config.TextColumn(
                                    "Monto Total",
                                    help="Volumen total transado (COP)"
                                ),
                                "Monto Promedio": st.column_config.TextColumn(
                                    "Monto Promedio",
                                    help="Monto promedio por transacción (COP)"
                                )
                            }
                        )
                        
                        # Botón de descarga
                        csv_inactivos = df_display.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 Descargar CSV",
                            data=csv_inactivos,
                            file_name=f"{cliente}_beneficiarios_inactivos.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # Estadísticas adicionales
                        st.markdown("---")
                        st.markdown("**📊 Estadísticas del grupo:**")
                        col_stat1, col_stat2 = st.columns(2)
                        with col_stat1:
                            dias_promedio = df_inactivos_display['Días Inactivo'].mean()
                            st.metric("Promedio días inactivo", f"{dias_promedio:.0f}")
                        with col_stat2:
                            tx_total = df_inactivos_display['TX Históricas'].sum()
                            st.metric("TX históricas totales", f"{tx_total:,}")
            
            with col_det2:
                if len(benef_baja_actividad) > 0:
                    with st.expander(f"📋 Ver Baja Actividad ({len(benef_baja_actividad)})", expanded=False):
                        st.caption(f"**Listado completo de {len(benef_baja_actividad)} beneficiarios con baja actividad:**")
                        
                        # Preparar dataframe
                        df_baja_act_display = benef_baja_actividad.sort_values('cantidad_tx').copy()
                        
                        df_baja_act_display['Beneficiario'] = df_baja_act_display['beneficiario'].astype(str)
                        df_baja_act_display['TX Realizadas'] = df_baja_act_display['cantidad_tx'].astype(int)
                        df_baja_act_display['Última TX'] = df_baja_act_display['ultima_tx'].dt.strftime('%d/%m/%Y')
                        df_baja_act_display['Primera TX'] = df_baja_act_display['primera_tx'].dt.strftime('%d/%m/%Y')
                        df_baja_act_display['Monto Total'] = df_baja_act_display['monto_total'].apply(lambda x: f"${x:,.0f}")
                        df_baja_act_display['Monto Promedio'] = df_baja_act_display['monto_promedio'].apply(lambda x: f"${x:,.0f}")
                        df_baja_act_display['Días sin TX'] = df_baja_act_display['dias_sin_actividad'].astype(int)
                        
                        df_display = df_baja_act_display[[
                            'Beneficiario',
                            'TX Realizadas',
                            'Última TX',
                            'Primera TX',
                            'Días sin TX',
                            'Monto Total',
                            'Monto Promedio'
                        ]]
                        
                        st.dataframe(
                            df_display,
                            use_container_width=True,
                            height=400,
                            hide_index=True,
                            column_config={
                                "Beneficiario": st.column_config.TextColumn(
                                    "Beneficiario",
                                    width="large"
                                ),
                                "TX Realizadas": st.column_config.NumberColumn(
                                    "TX Realizadas",
                                    format="%d TX"
                                ),
                                "Días sin TX": st.column_config.NumberColumn(
                                    "Días sin TX",
                                    format="%d días"
                                )
                            }
                        )
                        
                        csv_baja_act = df_display.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 Descargar CSV",
                            data=csv_baja_act,
                            file_name=f"{cliente}_beneficiarios_baja_actividad.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        st.markdown("---")
                        st.markdown("**📊 Estadísticas del grupo:**")
                        col_stat1, col_stat2 = st.columns(2)
                        with col_stat1:
                            tx_promedio = df_baja_act_display['TX Realizadas'].mean()
                            st.metric("Promedio TX", f"{tx_promedio:.1f}")
                        with col_stat2:
                            monto_total_grupo = benef_baja_actividad['monto_total'].sum()
                            st.metric("Volumen total", formato_moneda(monto_total_grupo))
            
            with col_det3:
                if len(benef_bajos_montos) > 0:
                    with st.expander(f"📋 Ver Bajos Montos ({len(benef_bajos_montos)})", expanded=False):
                        st.caption(f"**Listado completo de {len(benef_bajos_montos)} beneficiarios con bajos montos:**")
                        
                        # Preparar dataframe
                        df_bajos_display = benef_bajos_montos.sort_values('monto_promedio').copy()
                        
                        df_bajos_display['Beneficiario'] = df_bajos_display['beneficiario'].astype(str)
                        df_bajos_display['Monto Promedio'] = df_bajos_display['monto_promedio'].apply(lambda x: f"${x:,.0f}")
                        df_bajos_display['Monto Total'] = df_bajos_display['monto_total'].apply(lambda x: f"${x:,.0f}")
                        df_bajos_display['TX Realizadas'] = df_bajos_display['cantidad_tx'].astype(int)
                        df_bajos_display['Última TX'] = df_bajos_display['ultima_tx'].dt.strftime('%d/%m/%Y')
                        df_bajos_display['Primera TX'] = df_bajos_display['primera_tx'].dt.strftime('%d/%m/%Y')
                        df_bajos_display['Días sin TX'] = df_bajos_display['dias_sin_actividad'].astype(int)
                        
                        df_display = df_bajos_display[[
                            'Beneficiario',
                            'Monto Promedio',
                            'Monto Total',
                            'TX Realizadas',
                            'Última TX',
                            'Primera TX',
                            'Días sin TX'
                        ]]
                        
                        st.dataframe(
                            df_display,
                            use_container_width=True,
                            height=400,
                            hide_index=True,
                            column_config={
                                "Beneficiario": st.column_config.TextColumn(
                                    "Beneficiario",
                                    width="large"
                                ),
                                "TX Realizadas": st.column_config.NumberColumn(
                                    "TX Realizadas",
                                    format="%d TX"
                                ),
                                "Días sin TX": st.column_config.NumberColumn(
                                    "Días sin TX",
                                    format="%d días"
                                )
                            }
                        )
                        
                        csv_bajos = df_display.to_csv(index=False).encode('utf-8-sig')
                        st.download_button(
                            label="📥 Descargar CSV",
                            data=csv_bajos,
                            file_name=f"{cliente}_beneficiarios_bajos_montos.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        st.markdown("---")
                        st.markdown("**📊 Estadísticas del grupo:**")
                        st.info(f"💰 Umbral de bajo monto: {formato_moneda(umbral_bajo_monto)} (percentil 25)")
                        col_stat1, col_stat2 = st.columns(2)
                        with col_stat1:
                            monto_min = benef_bajos_montos['monto_promedio'].min()
                            st.metric("Monto más bajo", formato_moneda(monto_min))
                        with col_stat2:
                            tx_total_grupo = benef_bajos_montos['cantidad_tx'].sum()
                            st.metric("TX totales", f"{tx_total_grupo:,}")
            
            # Gráfico de distribución de actividad
            st.markdown("**📊 Distribución de Actividad de Beneficiarios**")
            
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots
            
            fig_actividad = make_subplots(
                rows=1, cols=2,
                subplot_titles=('Distribución por Cantidad de TX', 'Distribución por Días sin Actividad'),
                specs=[[{"type": "histogram"}, {"type": "histogram"}]]
            )
            
            # Histograma de cantidad de TX
            fig_actividad.add_trace(
                go.Histogram(
                    x=df_benef_actividad['cantidad_tx'],
                    name='TX por Beneficiario',
                    marker_color='#4a90e2',
                    opacity=0.7,
                    nbinsx=20
                ),
                row=1, col=1
            )
            
            # Histograma de días sin actividad
            fig_actividad.add_trace(
                go.Histogram(
                    x=df_benef_actividad['dias_sin_actividad'],
                    name='Días sin Actividad',
                    marker_color='#e74c3c',
                    opacity=0.7,
                    nbinsx=20
                ),
                row=1, col=2
            )
            
            fig_actividad.update_xaxes(title_text="Cantidad de TX", row=1, col=1)
            fig_actividad.update_xaxes(title_text="Días sin Actividad", row=1, col=2)
            fig_actividad.update_yaxes(title_text="Cantidad de Beneficiarios", row=1, col=1)
            fig_actividad.update_yaxes(title_text="Cantidad de Beneficiarios", row=1, col=2)
            
            fig_actividad.update_layout(
                height=400,
                showlegend=False,
                plot_bgcolor='rgba(248, 249, 250, 0.5)',
                paper_bgcolor='white',
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            st.plotly_chart(fig_actividad, use_container_width=True)
        else:
            st.info("No hay suficientes datos para analizar inactividad de beneficiarios")

        st.markdown("---")

        # ============================================
        # 3. ANÁLISIS DE MONTOS Y EFICIENCIA
        # ============================================
        st.markdown("##### 💰 Análisis de Montos y Eficiencia")

        col_montos1, col_montos2, col_montos3, col_montos4 = st.columns(4)

        with col_montos1:
            if "monto_cop" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                monto_min = float(df_cliente_efectivo['monto_cop'].min())
                st.metric(
                    "📉 Monto Mínimo", 
                    formato_moneda(monto_min),
                    help="Transacción efectiva de menor valor"
                )

        with col_montos2:
            if "monto_cop" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                monto_max = float(df_cliente_efectivo['monto_cop'].max())
                st.metric(
                    "📈 Monto Máximo", 
                    formato_moneda(monto_max),
                    help="Transacción efectiva de mayor valor"
                )

        with col_montos3:
            if "monto_cop" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                monto_mediana = float(df_cliente_efectivo['monto_cop'].median())
                st.metric(
                    "📊 Mediana", 
                    formato_moneda(monto_mediana),
                    help="Valor mediano de transacciones (mejor indicador que promedio)"
                )

        with col_montos4:
            # Tasa de rechazo
            if "estado_norm" in df_cliente.columns:
                tx_rechazadas = len(df_cliente[df_cliente['estado_norm'].isin(['RECHAZADO', 'FALLIDO'])])
                tasa_rechazo = (tx_rechazadas / total_tx_cliente * 100) if total_tx_cliente > 0 else 0
                st.metric(
                    "⚠️ Tasa de Rechazo", 
                    f"{tasa_rechazo:.1f}%", 
                    f"{tx_rechazadas:,} TX", 
                    delta_color="inverse",
                    help="Porcentaje de transacciones rechazadas o fallidas"
                )

        # Indicador de concentración y diversificación
        col_div1, col_div2 = st.columns(2)
        
        with col_div1:
            if "beneficiario" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                benef_unicos = df_cliente_efectivo['beneficiario'].nunique()
                st.metric(
                    "👥 Beneficiarios Únicos", 
                    f"{benef_unicos:,}", 
                    "Diversificación",
                    help="Cantidad de beneficiarios únicos que reciben pagos"
                )
        
        with col_div2:
            if "banco_norm" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
                bancos_unicos = df_cliente_efectivo['banco_norm'].nunique()
                st.metric(
                    "🏦 Bancos Únicos", 
                    f"{bancos_unicos:,}", 
                    "Entidades utilizadas",
                    help="Cantidad de entidades bancarias únicas utilizadas"
                )

        st.markdown("---")

        # ============================================
        # 4. TIPOS DE TRANSACCIONES
        # ============================================
        if "tipo_tx_norm" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
            tipos_tx = df_cliente_efectivo["tipo_tx_norm"].fillna("DESCONOCIDO").value_counts()
            st.markdown("**📋 Tipos de Transacciones (Efectivas):**")
            for tipo, cantidad in tipos_tx.items():
                pct_tipo = (cantidad / tx_efectivas_cliente * 100) if tx_efectivas_cliente > 0 else 0
                st.write(f"• {tipo}: {int(cantidad):,} ({pct_tipo:.1f}%)")

        # Tabla transacciones recientes
        st.markdown("---")
        st.markdown("#### 📋 Últimas 50 Transacciones")
        st.dataframe(df_cliente.head(50), use_container_width=True, height=300)

        # =========================
        # Top beneficiarios (fijo)
        # =========================
        st.markdown("---")
        st.markdown("#### 🎯 Análisis de Participación")
        st.markdown("<p style='color: gray; margin-top: -10px;'>Beneficiarios y entidades bancarias con mayor actividad</p>", unsafe_allow_html=True)

        if "beneficiario" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
            try:
                df_benef = (
                    df_cliente_efectivo.groupby("beneficiario", dropna=False)
                    .agg(tx=("tx_id", "count"), monto_total=("monto_cop", "sum"), monto_prom=("monto_cop", "mean"))
                    .reset_index()
                )
                df_benef["beneficiario"] = df_benef["beneficiario"].fillna("DESCONOCIDO")
                df_benef["%participacion"] = np.where(
                    monto_total_cliente > 0,
                    (df_benef["monto_total"] / monto_total_cliente * 100).round(2),
                    0,
                )
                if "tipo_persona_benef" in df_cliente_efectivo.columns:
                    tipo_map = df_cliente_efectivo.groupby("beneficiario")["tipo_persona_benef"].first()
                    df_benef["tipo"] = df_benef["beneficiario"].map(tipo_map).fillna("Desconocido")
                else:
                    df_benef["tipo"] = "Desconocido"
                
                logger.debug(f"Cliente {cliente}: {len(df_benef)} beneficiarios únicos")

                df_pn = df_benef[df_benef["tipo"] == "Natural"].copy()
                df_pj = df_benef[df_benef["tipo"] == "Jurídica"].copy()

                st.markdown("##### 👤 Personas Naturales")
                if len(df_pn) > 0:
                    try:
                        top = df_pn.sort_values("monto_total", ascending=True).tail(10)
                        top["beneficiario_display"] = top["beneficiario"].apply(lambda x: f"👤 {str(x)[:40]}{'...' if len(str(x)) > 40 else ''}")

                        fig_pn = px.bar(
                            top,
                            y="beneficiario_display",
                            x="monto_total",
                            orientation="h",
                            text="tx",
                            hover_data={"tx": True, "monto_prom": ":,.0f", "%participacion": True, "monto_total": ":,.0f", "beneficiario_display": False},
                            labels={"monto_total": "Volumen Total (COP)", "beneficiario_display": ""},
                        )
                        fig_pn.update_layout(height=400, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_pn, use_container_width=True)
                    except Exception as e:
                        logger.error(f"Error generando gráfico PN para {cliente}: {str(e)}")
                        st.warning("⚠️ Error generando gráfico de Personas Naturales")
                else:
                    st.info("📊 No hay beneficiarios PN (TX efectivas)")

                st.markdown("##### 🏢 Personas Jurídicas")
                if len(df_pj) > 0:
                    try:
                        top = df_pj.sort_values("monto_total", ascending=True).tail(10)
                        top["beneficiario_display"] = top["beneficiario"].apply(lambda x: f"🏢 {str(x)[:40]}{'...' if len(str(x)) > 40 else ''}")

                        fig_pj = px.bar(
                            top,
                            y="beneficiario_display",
                            x="monto_total",
                            orientation="h",
                            text="tx",
                            hover_data={"tx": True, "monto_prom": ":,.0f", "%participacion": True, "monto_total": ":,.0f", "beneficiario_display": False},
                            labels={"monto_total": "Volumen Total (COP)", "beneficiario_display": ""},
                        )
                        fig_pj.update_layout(height=400, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_pj, use_container_width=True)
                    except Exception as e:
                        logger.error(f"Error generando gráfico PJ para {cliente}: {str(e)}")
                        st.warning("⚠️ Error generando gráfico de Personas Jurídicas")
                else:
                    st.info("📊 No hay beneficiarios PJ (TX efectivas)")
            except Exception as e:
                logger.error(f"Error procesando beneficiarios para {cliente}: {str(e)}")
                st.warning("⚠️ Error procesando información de beneficiarios")
        else:
            st.info("📊 No se encontró información de beneficiarios en TX efectivas")

        # =========================
        # Top bancos (fijo)
        # =========================
        st.markdown("---")
        st.markdown("##### 🏦 Top Bancos por Volumen")

        if "banco_norm" in df_cliente_efectivo.columns and len(df_cliente_efectivo) > 0:
            try:
                df_bancos = (
                    df_cliente_efectivo.groupby("banco_norm", dropna=False)
                    .agg(tx=("tx_id", "count"), monto_total=("monto_cop", "sum"), monto_prom=("monto_cop", "mean"))
                    .reset_index()
                )
                df_bancos["banco_norm"] = df_bancos["banco_norm"].fillna("DESCONOCIDO")
                df_bancos["%participacion"] = np.where(
                    monto_total_cliente > 0,
                    (df_bancos["monto_total"] / monto_total_cliente * 100).round(2),
                    0,
                )
                
                logger.debug(f"Cliente {cliente}: {len(df_bancos)} bancos únicos")

                top = df_bancos.sort_values("monto_total", ascending=True).tail(10)
                top["banco_display"] = top["banco_norm"].apply(lambda x: f"🏦 {str(x)[:40]}{'...' if len(str(x)) > 40 else ''}")

                fig_b = px.bar(
                    top,
                    y="banco_display",
                    x="monto_total",
                    orientation="h",
                    text="tx",
                    hover_data={"tx": True, "monto_prom": ":,.0f", "%participacion": True, "monto_total": ":,.0f", "banco_display": False},
                    labels={"monto_total": "Volumen Total (COP)", "banco_display": ""},
                )
                fig_b.update_layout(height=450, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_b, use_container_width=True)
            except Exception as e:
                logger.error(f"Error procesando bancos para {cliente}: {str(e)}")
                st.warning("⚠️ Error procesando información de bancos")
        else:
            st.info("🏦 No se encontró información de bancos en TX efectivas")

        # =========================
        # Capa 2: Riesgo integral
        # =========================
        st.markdown("---")
        st.markdown("## 🟥 Capa 2: Evaluación de Riesgo y Cumplimiento")
        st.caption("Interpretación regulatoria y señales de riesgo derivadas del comportamiento")

        st.markdown("### 🎯 Análisis de Riesgo Integral")
        st.markdown("<p style='color: gray; margin-top: -10px;'>Sistema completo de evaluación multicapa (GAFI + UIAF + Operativo)</p>", unsafe_allow_html=True)

        # Para compatibilidad: pasamos df_cliente con columnas legacy presentes
        logger.info(f"Iniciando análisis de riesgo para cliente: {cliente}")
        try:
            perfil_gafi = caracterizar_cliente_gafi(df_cliente)
            analisis_riesgo = analizar_riesgo_cliente(df_cliente, perfil_gafi, cliente)
            logger.info(f"✓ Análisis de riesgo completado para {cliente} - Nivel: {analisis_riesgo.get('scoring', {}).get('nivel_riesgo', 'N/A')}")
        except Exception as e:
            logger.error(f"Error en análisis de riesgo para {cliente}: {str(e)}")
            st.error(f"⚠️ Error analizando riesgo: {str(e)}")
            continue

        # Scoring
        st.markdown("### 📊 Scoring de Riesgo")
        scoring = analisis_riesgo.get("scoring", {})

        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric("Score Total", f"{scoring.get('score_total','N/A')}/100")
        with sc2:
            st.metric("Score GAFI", f"{scoring.get('score_gafi','N/A')}/100", delta="40% peso")
        with sc3:
            st.metric("Score UIAF", f"{scoring.get('score_uiaf','N/A')}/100", delta="35% peso")
        with sc4:
            st.metric("Score Operativo", f"{scoring.get('score_operativo','N/A')}/100", delta="25% peso")

        nivel = scoring.get("nivel_riesgo", "No Evaluado")
        colores_nivel = {"Bajo": "#4CAF50", "Medio": "#FF9800", "Alto": "#f44336", "Crítico": "#9C27B0", "No Evaluado": "#757575"}
        emojis_nivel = {"Bajo": "✅", "Medio": "⚠️", "Alto": "🚨", "Crítico": "🔥", "No Evaluado": "❓"}

        st.markdown(
            f"""
            <div style='background: {colores_nivel.get(nivel, "#757575")};
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        margin: 20px 0;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.15);'>
                <h2 style='margin: 0; color: white; font-size: 28px;'>{emojis_nivel.get(nivel, "❓")} Nivel de Riesgo: {_safe(nivel)}</h2>
            </div>
            """,
            unsafe_allow_html=True,
        )

        factores = scoring.get("factores_criticos", [])
        if factores:
            st.markdown("#### ⚠️ Factores Críticos Detectados")
            for f in factores:
                st.warning(f"🔴 {_safe(f)}")

        # Alertas
        st.markdown("---")
        st.markdown("### 🚨 Alertas de Riesgo")
        alertas = analisis_riesgo.get("alertas", [])

        if alertas:
            crit = [a for a in alertas if a.get("prioridad") == "Crítica"]
            altas = [a for a in alertas if a.get("prioridad") == "Alta"]
            medias = [a for a in alertas if a.get("prioridad") == "Media"]
            bajas = [a for a in alertas if a.get("prioridad") == "Baja"]

            a1, a2, a3, a4 = st.columns(4)
            with a1:
                st.metric("🔥 Críticas", len(crit))
            with a2:
                st.metric("🚨 Altas", len(altas))
            with a3:
                st.metric("⚠️ Medias", len(medias))
            with a4:
                st.metric("ℹ️ Bajas", len(bajas))

            st.markdown("#### Alertas Prioritarias")
            importantes = crit + altas
            if importantes:
                for alerta in importantes:
                    prioridad = alerta.get("prioridad", "Media")
                    color = {"Crítica": "#9C27B0", "Alta": "#f44336", "Media": "#FF9800", "Baja": "#2196F3"}.get(prioridad, "#757575")
                    tipo = alerta.get("tipo", "Compliance")
                    emoji_tipo = {"UIAF": "📋", "Fraude": "🚨", "Operacional": "⚙️", "Compliance": "📜", "Reputacional": "👁️"}.get(tipo, "⚠️")

                    st.markdown(
                        f"""
                        <div style='background: {color}15;
                                    border-left: 5px solid {color};
                                    padding: 15px;
                                    margin: 10px 0;
                                    border-radius: 8px;
                                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
                            <h4 style='margin: 0 0 8px 0; color: {color};'>
                                {emoji_tipo} {_safe(alerta.get('titulo','Alerta'))}
                            </h4>
                            <p style='margin: 5px 0; color: #555;'><strong>Tipo:</strong> {_safe(tipo)} | <strong>Prioridad:</strong> {_safe(prioridad)}</p>
                            <p style='margin: 5px 0; color: #666;'>{_safe(alerta.get('descripcion',''))}</p>
                            <p style='margin: 8px 0 5px 0; background: #f5f5f5; padding: 8px; border-radius: 5px;'>
                                <strong>💡 Acción requerida:</strong> {_safe(alerta.get('accion_requerida',''))}
                            </p>
                            <p style='margin: 5px 0 0 0; color: #888; font-size: 12px;'>
                                ⏰ Días para acción: {_safe(alerta.get('dias_para_accion',''))} |
                                {'📋 Requiere reporte UIAF' if alerta.get('requiere_reporte_uiaf', False) else '✅ No requiere reporte'}
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No hay alertas Críticas/Altas.")

            with st.expander(f"📋 Ver todas las alertas ({len(alertas)})"):
                for alerta in alertas:
                    st.markdown(f"**{_safe(alerta.get('tipo',''))}** - {_safe(alerta.get('titulo',''))} ({_safe(alerta.get('prioridad',''))})")
                    st.caption(_safe(alerta.get("descripcion", "")))
                    st.markdown("---")
        else:
            st.success("✅ No se detectaron alertas de riesgo para este cliente")

        # Recomendaciones
        st.markdown("---")
        st.markdown("### 💡 Recomendaciones")
        recomendaciones = analisis_riesgo.get("recomendaciones", [])
        if recomendaciones:
            for rec in recomendaciones:
                st.info(_safe(rec))
        else:
            st.info("Sin recomendaciones adicionales.")

        # Acciones requeridas
        x1, x2 = st.columns(2)
        with x1:
            if analisis_riesgo.get("requiere_due_diligence_reforzada", False):
                st.error("🔍 **Due Diligence Reforzada Requerida**")
            else:
                st.success("✅ Due Diligence estándar suficiente")
        with x2:
            if analisis_riesgo.get("requiere_escalamiento", False):
                st.error("⬆️ **Requiere Escalamiento Inmediato**")
            else:
                st.success("✅ No requiere escalamiento")

        st.info(f"📅 **Próximo review programado:** {_safe(analisis_riesgo.get('proximo_review','N/A'))}")

        # Matriz de riesgo
        with st.expander("🎯 Ver Matriz de Riesgo Detallada"):
            matriz = analisis_riesgo.get("matriz_riesgo", {})

            st.markdown("#### Riesgo Inherente vs Residual")
            m1, m2 = st.columns(2)

            with m1:
                st.markdown("**Riesgo Inherente (sin controles)**")
                for categoria, valor in (matriz.get("riesgo_inherente", {}) or {}).items():
                    try:
                        v = float(valor)
                    except Exception:
                        v = 0.0
                    st.progress(min(max(v, 0), 100) / 100, text=f"{categoria.capitalize()}: {v:.0f}/100")

            with m2:
                st.markdown("**Riesgo Residual (con controles)**")
                for categoria, valor in (matriz.get("riesgo_residual", {}) or {}).items():
                    try:
                        v = float(valor)
                    except Exception:
                        v = 0.0
                    st.progress(min(max(v, 0), 100) / 100, text=f"{categoria.capitalize()}: {v:.0f}/100")

            st.markdown("#### Controles Aplicados")
            for control in (matriz.get("controles_aplicados", []) or []):
                st.markdown(f"✅ {_safe(control)}")

            gaps = matriz.get("gaps_control", []) or []
            if gaps:
                st.markdown("#### Gaps de Control")
                for gap in gaps:
                    st.warning(f"⚠️ {_safe(gap)}")

            if matriz.get("apetito_riesgo_superado", False):
                st.error("🚨 **ALERTA:** Apetito de riesgo superado")
            else:
                st.success("✅ Dentro del apetito de riesgo")


# =========================
# Footer
# =========================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>© 2026 AdamoPay - Sistema de Análisis y Reporte Transaccional</p>
        <p>Versión 1.0.0</p>
    </div>
    """,
    unsafe_allow_html=True,
)
