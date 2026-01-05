"""
Módulo de Análisis de Riesgo Transaccional
Sistema completo de evaluación, scoring y alertas de riesgo

📌 CONTRATO DEL MÓDULO:
- Recibe: pandas.DataFrame + dict (perfil GAFI opcional)
- Devuelve: dict estructurado con análisis de riesgo
- NO usa Streamlit ni genera UI
- Independiente pero complementario a characterization/
"""

from .risk_engine import (
    analizar_riesgo_cliente,
    analizar_riesgo_cartera,
    clasificar_nivel_riesgo
)
from .risk_scoring import (
    calcular_score_integral,
    calcular_score_uiaf,
    calcular_score_operativo
)
from .risk_alerts import (
    generar_alertas_automaticas,
    priorizar_alertas,
    clasificar_alerta
)
from .risk_reports import (
    generar_reporte_riesgo,
    exportar_matriz_riesgo,
    crear_resumen_ejecutivo
)

__version__ = "1.0.0"
__all__ = [
    # Motor de riesgo
    'analizar_riesgo_cliente',
    'analizar_riesgo_cartera',
    'clasificar_nivel_riesgo',
    # Scoring
    'calcular_score_integral',
    'calcular_score_uiaf',
    'calcular_score_operativo',
    # Alertas
    'generar_alertas_automaticas',
    'priorizar_alertas',
    'clasificar_alerta',
    # Reportes
    'generar_reporte_riesgo',
    'exportar_matriz_riesgo',
    'crear_resumen_ejecutivo'
]
