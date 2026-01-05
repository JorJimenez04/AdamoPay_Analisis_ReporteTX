"""
Contrato de datos para la capa GAFI
Define los schemas de entrada/salida para todas las funciones de caracterización

📌 REGLA DE ORO:
- La capa GAFI SOLO procesa datos
- NO debe importar streamlit
- NO debe generar UI
- Solo devuelve diccionarios estructurados
"""

from typing import TypedDict, List, Dict, Any, Literal
from datetime import datetime


# ========== SCHEMAS DE ENTRADA ==========

class DataFrameContractIn:
    """
    Contrato de entrada: DataFrame del cliente
    
    Columnas esperadas (opcionales según análisis):
    - FECHA: datetime
    - MONTO (COP): float
    - ESTADO: str
    - TIPO DE TRA: str
    - TIPO_PERSONA: str ('Natural', 'Jurídica', 'Desconocido')
    - COMISION ((MONTO TOT): float
    - CLIENTE: str
    """
    pass


# ========== SCHEMAS DE SALIDA ==========

class MetricasBasicas(TypedDict):
    """Métricas básicas de transacciones"""
    total_transacciones: int
    volumen_total: float
    promedio_transaccion: float
    frecuencia_diaria: float


class PerfilGAFI(TypedDict):
    """
    Schema de salida para clasificar_perfil_gafi()
    
    Returns:
        perfil: Descripción del perfil de riesgo
        nivel_riesgo: 'Bajo' | 'Medio' | 'Alto'
        score: int (0-100)
        factores: List[str] - Factores de riesgo detectados
        metricas: MetricasBasicas
    """
    perfil: str
    nivel_riesgo: Literal['Bajo', 'Medio', 'Alto', 'N/A']
    score: int
    factores: List[str]
    metricas: MetricasBasicas


class RecomendacionGAFI(TypedDict):
    """Lista de recomendaciones de acción"""
    recomendaciones: List[str]


class TendenciaRiesgo(TypedDict):
    """
    Schema de salida para calcular_tendencia_riesgo()
    
    Returns:
        tendencia: Descripción de la tendencia
        variacion: float - Variación del score
        score_actual: int
        score_anterior: int
    """
    tendencia: str
    variacion: float
    score_actual: int
    score_anterior: int


class MetricasComportamiento(TypedDict, total=False):
    """
    Schema de salida para calcular_metricas_comportamiento()
    
    Returns: Dict con todas las métricas calculadas
    """
    # Métricas básicas
    total_transacciones: int
    volumen_total: float
    volumen_promedio: float
    volumen_mediana: float
    
    # Variabilidad
    desviacion_estandar: float
    coeficiente_variacion: float
    monto_minimo: float
    monto_maximo: float
    rango: float
    
    # Temporales
    fecha_primera_tx: str
    fecha_ultima_tx: str
    dias_activo: int
    frecuencia_diaria: float
    distribucion_dias_semana: Dict[str, int]
    hora_promedio: float
    distribucion_horaria: Dict[int, int]
    
    # Tipos y estados
    tipos_transaccion: Dict[str, int]
    tipo_predominante: str
    diversidad_tipos: int
    distribucion_estados: Dict[str, int]
    tasa_exito: float
    tasa_rechazo: float
    
    # Beneficiarios
    distribucion_personas: Dict[str, int]
    proporcion_naturales: float
    proporcion_juridicas: float
    
    # Consistencia
    indice_consistencia: int


class Anomalia(TypedDict):
    """Estructura de una anomalía detectada"""
    fecha: str
    monto: float
    desviacion: float
    tipo: str


class AnomaliaFrecuencia(TypedDict):
    """Anomalía de frecuencia"""
    fecha: str
    cantidad_tx: int
    promedio_normal: float
    desviacion: float


class AnomaliaTemporal(TypedDict):
    """Anomalía temporal"""
    tipo: str
    cantidad: int
    porcentaje: float


class PatronesAnomalos(TypedDict):
    """
    Schema de salida para detectar_patrones_anomalos()
    
    Returns:
        total_anomalias: int
        anomalias_monto: List[Anomalia]
        anomalias_frecuencia: List[AnomaliaFrecuencia]
        anomalias_temporales: List[AnomaliaTemporal]
        nivel_alerta: 'Normal' | 'Bajo' | 'Medio' | 'Alto'
    """
    total_anomalias: int
    anomalias_monto: List[Anomalia]
    anomalias_frecuencia: List[AnomaliaFrecuencia]
    anomalias_temporales: List[AnomaliaTemporal]
    nivel_alerta: Literal['Normal', 'Bajo', 'Medio', 'Alto']


class Estacionalidad(TypedDict, total=False):
    """
    Schema de salida para analizar_estacionalidad()
    """
    transacciones_por_mes: Dict[str, int]
    volumen_por_mes: Dict[str, float]
    transacciones_por_trimestre: Dict[str, int]
    mes_mayor_actividad: str
    mes_menor_actividad: str
    coeficiente_estacionalidad: float
    patron: str


class ScoreConsistencia(TypedDict):
    """
    Schema de salida para calcular_score_consistencia()
    
    Returns:
        score: int (0-100)
        clasificacion: 'Excelente' | 'Bueno' | 'Regular' | 'Deficiente'
        color: str (emoji)
        factores: List[str]
    """
    score: int
    clasificacion: Literal['Excelente', 'Bueno', 'Regular', 'Deficiente']
    color: str
    factores: List[str]


class BanderaRiesgo(TypedDict):
    """Estructura de una bandera de riesgo"""
    tipo: str
    severidad: Literal['Baja', 'Media', 'Alta', 'Crítica']
    descripcion: str
    detalles: Dict[str, Any]
    recomendacion: str
    puntos: int


class EvaluacionBanderas(TypedDict):
    """
    Schema de salida para evaluar_banderas_riesgo()
    
    Returns:
        banderas: List[BanderaRiesgo]
        total_banderas: int
        nivel_alerta: 'Sin datos' | 'Bajo' | 'Medio' | 'Alto' | 'Crítico'
        score_riesgo: int (0-100)
        requiere_reporte_uiaf: bool
        requiere_investigacion: bool
    """
    banderas: List[BanderaRiesgo]
    total_banderas: int
    nivel_alerta: Literal['Sin datos', 'Bajo', 'Medio', 'Alto', 'Crítico']
    score_riesgo: int
    requiere_reporte_uiaf: bool
    requiere_investigacion: bool


# ========== CONTRATO CONSOLIDADO ==========

class ResultadoAnalisisCompleto(TypedDict):
    """
    Schema consolidado con todos los análisis
    Útil para procesar todos los análisis de un cliente de una vez
    """
    perfil_gafi: PerfilGAFI
    metricas_comportamiento: MetricasComportamiento
    patrones_anomalos: PatronesAnomalos
    banderas_riesgo: EvaluacionBanderas
    score_consistencia: ScoreConsistencia
    timestamp: str


# ========== VALIDADORES ==========

def validar_dataframe_entrada(df) -> tuple[bool, str]:
    """
    Valida que el DataFrame cumpla el contrato mínimo
    
    Args:
        df: pandas.DataFrame
        
    Returns:
        (bool, str): (es_valido, mensaje_error)
    """
    if df is None:
        return False, "DataFrame es None"
    
    if df.empty:
        return False, "DataFrame está vacío"
    
    # No validamos columnas específicas porque son opcionales
    # según el tipo de análisis
    
    return True, "OK"


def validar_perfil_gafi(resultado: dict) -> tuple[bool, str]:
    """
    Valida que el resultado de clasificar_perfil_gafi() cumple el contrato
    
    Args:
        resultado: Dict retornado por clasificar_perfil_gafi()
        
    Returns:
        (bool, str): (es_valido, mensaje_error)
    """
    campos_requeridos = ['perfil', 'nivel_riesgo', 'score', 'factores', 'metricas']
    
    for campo in campos_requeridos:
        if campo not in resultado:
            return False, f"Falta campo requerido: {campo}"
    
    # Validar nivel_riesgo
    if resultado['nivel_riesgo'] not in ['Bajo', 'Medio', 'Alto', 'N/A']:
        return False, f"nivel_riesgo inválido: {resultado['nivel_riesgo']}"
    
    # Validar score
    if not isinstance(resultado['score'], (int, float)) or not 0 <= resultado['score'] <= 100:
        return False, f"score debe estar entre 0-100, recibido: {resultado['score']}"
    
    return True, "OK"


def validar_banderas_riesgo(resultado: dict) -> tuple[bool, str]:
    """
    Valida que el resultado de evaluar_banderas_riesgo() cumple el contrato
    
    Args:
        resultado: Dict retornado por evaluar_banderas_riesgo()
        
    Returns:
        (bool, str): (es_valido, mensaje_error)
    """
    campos_requeridos = ['banderas', 'total_banderas', 'nivel_alerta', 'score_riesgo']
    
    for campo in campos_requeridos:
        if campo not in resultado:
            return False, f"Falta campo requerido: {campo}"
    
    # Validar nivel_alerta
    niveles_validos = ['Sin datos', 'Bajo', 'Medio', 'Alto', 'Crítico']
    if resultado['nivel_alerta'] not in niveles_validos:
        return False, f"nivel_alerta inválido: {resultado['nivel_alerta']}"
    
    # Validar score_riesgo
    if not isinstance(resultado['score_riesgo'], (int, float)) or not 0 <= resultado['score_riesgo'] <= 100:
        return False, f"score_riesgo debe estar entre 0-100, recibido: {resultado['score_riesgo']}"
    
    # Validar banderas
    if not isinstance(resultado['banderas'], list):
        return False, "banderas debe ser una lista"
    
    return True, "OK"


# ========== FUNCIONES HELPER ==========

def crear_respuesta_vacia() -> Dict[str, Any]:
    """
    Crea una respuesta vacía cuando no hay datos para analizar
    Útil para mantener consistencia en respuestas
    """
    return {
        'error': 'Sin datos para analizar',
        'tiene_datos': False
    }


def crear_perfil_gafi_vacio() -> PerfilGAFI:
    """Crea un perfil GAFI vacío con valores por defecto"""
    return {
        'perfil': 'Sin Datos',
        'nivel_riesgo': 'N/A',
        'score': 0,
        'factores': [],
        'metricas': {
            'total_transacciones': 0,
            'volumen_total': 0.0,
            'promedio_transaccion': 0.0,
            'frecuencia_diaria': 0.0
        }
    }


def crear_evaluacion_banderas_vacia() -> EvaluacionBanderas:
    """Crea una evaluación de banderas vacía con valores por defecto"""
    return {
        'banderas': [],
        'total_banderas': 0,
        'nivel_alerta': 'Sin datos',
        'score_riesgo': 0,
        'requiere_reporte_uiaf': False,
        'requiere_investigacion': False
    }


# ========== DOCUMENTACIÓN DEL CONTRATO ==========

"""
CONTRATO DE LA CAPA GAFI
========================

Todas las funciones de la capa GAFI deben cumplir:

✅ ENTRADA:
- pandas.DataFrame con transacciones del cliente
- Puede incluir parámetros adicionales (int, str, etc.)
- NO debe recibir componentes de Streamlit

✅ SALIDA:
- Dict estructurado según los TypedDict definidos arriba
- Tipos primitivos: str, int, float, bool, list, dict
- NO debe devolver componentes de Streamlit
- NO debe devolver HTML

✅ PROCESAMIENTO:
- Solo lógica de negocio y cálculos
- Puede usar: pandas, numpy, datetime
- NO debe usar: streamlit, st.*, cualquier librería de UI

✅ EXCEPCIONES:
- Debe manejar casos vacíos devolviendo estructuras válidas
- No debe lanzar excepciones no capturadas
- Debe validar datos de entrada

FUNCIONES PRINCIPALES Y SUS CONTRATOS:
=======================================

1. clasificar_perfil_gafi(df_cliente) -> PerfilGAFI
2. obtener_recomendaciones_gafi(perfil_riesgo) -> List[str]
3. calcular_tendencia_riesgo(df_cliente, ventana_dias) -> TendenciaRiesgo
4. calcular_metricas_comportamiento(df_cliente) -> MetricasComportamiento
5. detectar_patrones_anomalos(df_cliente, umbral_std) -> PatronesAnomalos
6. analizar_estacionalidad(df_cliente) -> Estacionalidad
7. calcular_score_consistencia(metricas, anomalias) -> ScoreConsistencia
8. evaluar_banderas_riesgo(df_cliente) -> EvaluacionBanderas
9. calcular_score_riesgo(evaluacion) -> int

SEPARACIÓN DE RESPONSABILIDADES:
=================================

CAPA GAFI (src/characterization/):
- Procesa datos
- Devuelve diccionarios
- Sin dependencias de UI

CAPA UI (app.py):
- Lee diccionarios de la capa GAFI
- Renderiza en Streamlit
- Maneja interacción con usuario

NUNCA MEZCLAR ambas capas en el mismo archivo.
"""
