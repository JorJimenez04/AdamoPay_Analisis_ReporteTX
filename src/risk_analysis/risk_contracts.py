"""
Contratos y schemas para el módulo de análisis de riesgo
Define la estructura de datos de entrada/salida
"""

from typing import TypedDict, List, Dict, Literal, Optional, Any
from datetime import datetime

# Niveles de riesgo posibles
NivelRiesgo = Literal['Bajo', 'Medio', 'Alto', 'Crítico', 'No Evaluado']
TipoAlerta = Literal['Operacional', 'UIAF', 'Compliance', 'Fraude', 'Reputacional']
PrioridadAlerta = Literal['Baja', 'Media', 'Alta', 'Crítica']


class ScoreRiesgo(TypedDict):
    """Score de riesgo integral"""
    score_total: int  # 0-100
    score_gafi: int  # 0-100
    score_uiaf: int  # 0-100
    score_operativo: int  # 0-100
    nivel_riesgo: NivelRiesgo
    factores_criticos: List[str]
    ponderacion: Dict[str, float]


class AlertaRiesgo(TypedDict):
    """Alerta de riesgo detectada"""
    id_alerta: str
    tipo: TipoAlerta
    prioridad: PrioridadAlerta
    titulo: str
    descripcion: str
    valor_detectado: float
    umbral: float
    accion_requerida: str
    fecha_deteccion: str
    requiere_reporte_uiaf: bool
    dias_para_accion: int


class AnalisisRiesgo(TypedDict):
    """Resultado completo del análisis de riesgo"""
    cliente: str
    timestamp_analisis: str
    scoring: ScoreRiesgo
    alertas: List[AlertaRiesgo]
    matriz_riesgo: Dict[str, Any]
    recomendaciones: List[str]
    requiere_due_diligence_reforzada: bool
    requiere_escalamiento: bool
    proximo_review: str


class MatrizRiesgo(TypedDict):
    """Matriz de riesgo por categorías"""
    riesgo_inherente: Dict[str, int]
    riesgo_residual: Dict[str, int]
    controles_aplicados: List[str]
    gaps_control: List[str]
    apetito_riesgo_superado: bool


class ResumenEjecutivo(TypedDict):
    """Resumen ejecutivo para alta gerencia"""
    total_clientes: int
    clientes_por_nivel: Dict[str, int]
    alertas_criticas: int
    alertas_pendientes: int
    reportes_uiaf_requeridos: int
    top_riesgos: List[Dict[str, Any]]
    recomendaciones_estrategicas: List[str]
    timestamp: str


# Validadores
def validar_score_riesgo(score: dict) -> tuple:
    """Valida estructura de ScoreRiesgo"""
    required = ['score_total', 'score_gafi', 'score_uiaf', 'score_operativo', 'nivel_riesgo']
    for field in required:
        if field not in score:
            return False, f"Campo requerido faltante: {field}"
    
    if not (0 <= score['score_total'] <= 100):
        return False, "score_total debe estar entre 0 y 100"
    
    return True, "Válido"


def validar_alerta_riesgo(alerta: dict) -> tuple:
    """Valida estructura de AlertaRiesgo"""
    required = ['tipo', 'prioridad', 'titulo', 'descripcion', 'accion_requerida']
    for field in required:
        if field not in alerta:
            return False, f"Campo requerido faltante: {field}"
    
    return True, "Válido"


# Helpers
def crear_score_vacio() -> ScoreRiesgo:
    """Score vacío para casos sin datos"""
    return {
        'score_total': 0,
        'score_gafi': 0,
        'score_uiaf': 0,
        'score_operativo': 0,
        'nivel_riesgo': 'No Evaluado',
        'factores_criticos': [],
        'ponderacion': {}
    }


def crear_analisis_vacio(cliente: str) -> AnalisisRiesgo:
    """Análisis vacío para casos sin datos"""
    return {
        'cliente': cliente,
        'timestamp_analisis': datetime.now().isoformat(),
        'scoring': crear_score_vacio(),
        'alertas': [],
        'matriz_riesgo': {},
        'recomendaciones': ['Sin datos suficientes para análisis'],
        'requiere_due_diligence_reforzada': False,
        'requiere_escalamiento': False,
        'proximo_review': 'N/A'
    }
