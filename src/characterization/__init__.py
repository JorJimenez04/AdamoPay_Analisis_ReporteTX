"""
Módulo de caracterización y análisis de riesgo transaccional
Incluye perfiles GAFI, métricas de comportamiento y banderas de riesgo

📌 CONTRATO DE LA CAPA GAFI:
- Recibe: pandas.DataFrame (df_cliente)
- Devuelve: dict estructurado (ver contracts.py)
- NO usa Streamlit ni genera UI
- Solo procesamiento de datos y lógica de negocio
"""

from .base_characterization import (
    caracterizar_cliente_gafi,
    caracterizar_cartera_clientes,
    obtener_resumen_caracterizacion
)
from .gafi_profile import clasificar_perfil_gafi, obtener_recomendaciones_gafi, calcular_tendencia_riesgo
from .behavior_metrics import calcular_metricas_comportamiento, detectar_patrones_anomalos, analizar_estacionalidad
from .risk_flags import evaluar_banderas_riesgo, calcular_score_riesgo
from .contracts import (
    PerfilGAFI,
    MetricasComportamiento,
    PatronesAnomalos,
    EvaluacionBanderas,
    validar_perfil_gafi,
    validar_banderas_riesgo
)

__version__ = "1.0.0"
__all__ = [
    # Caracterización base
    'caracterizar_cliente_gafi',
    'caracterizar_cartera_clientes',
    'obtener_resumen_caracterizacion',
    # Perfiles GAFI
    'clasificar_perfil_gafi',
    'obtener_recomendaciones_gafi',
    'calcular_tendencia_riesgo',
    # Métricas de comportamiento
    'calcular_metricas_comportamiento',
    'detectar_patrones_anomalos',
    'analizar_estacionalidad',
    # Banderas de riesgo
    'evaluar_banderas_riesgo',
    'calcular_score_riesgo',
    # Contratos y validadores
    'PerfilGAFI',
    'MetricasComportamiento',
    'PatronesAnomalos',
    'EvaluacionBanderas',
    'validar_perfil_gafi',
    'validar_banderas_riesgo'
]
