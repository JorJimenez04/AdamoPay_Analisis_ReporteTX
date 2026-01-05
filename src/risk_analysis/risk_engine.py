"""
Motor principal de análisis de riesgo
Orquesta scoring, alertas y clasificación
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from .risk_contracts import AnalisisRiesgo, NivelRiesgo, crear_analisis_vacio
from .risk_scoring import calcular_score_integral
from .risk_alerts import generar_alertas_automaticas


def analizar_riesgo_cliente(
    df_cliente: pd.DataFrame,
    perfil_gafi: Optional[Dict] = None,
    cliente_nombre: str = "Cliente"
) -> AnalisisRiesgo:
    """
    Análisis completo de riesgo de un cliente
    
    Args:
        df_cliente: DataFrame con transacciones del cliente
        perfil_gafi: Dict con caracterización GAFI (opcional)
        cliente_nombre: Nombre del cliente
    
    Returns:
        AnalisisRiesgo: Dict con análisis completo
    """
    if df_cliente is None or df_cliente.empty:
        return crear_analisis_vacio(cliente_nombre)
    
    # 1. Calcular scoring integral
    scoring = calcular_score_integral(df_cliente, perfil_gafi)
    
    # 2. Generar alertas automáticas
    alertas = generar_alertas_automaticas(df_cliente, scoring)
    
    # 3. Construir matriz de riesgo
    matriz = _construir_matriz_riesgo(df_cliente, scoring)
    
    # 4. Generar recomendaciones
    recomendaciones = _generar_recomendaciones(scoring, alertas)
    
    # 5. Determinar acciones requeridas
    requiere_ddr = scoring['score_total'] >= 70
    requiere_escalamiento = len([a for a in alertas if a['prioridad'] in ['Alta', 'Crítica']]) > 0
    
    # 6. Calcular próximo review
    proximo_review = _calcular_proximo_review(scoring['nivel_riesgo'])
    
    return {
        'cliente': cliente_nombre,
        'timestamp_analisis': datetime.now().isoformat(),
        'scoring': scoring,
        'alertas': alertas,
        'matriz_riesgo': matriz,
        'recomendaciones': recomendaciones,
        'requiere_due_diligence_reforzada': requiere_ddr,
        'requiere_escalamiento': requiere_escalamiento,
        'proximo_review': proximo_review
    }


def analizar_riesgo_cartera(
    df_completo: pd.DataFrame,
    lista_clientes: List[str]
) -> Dict[str, AnalisisRiesgo]:
    """
    Analiza riesgo de múltiples clientes
    
    Args:
        df_completo: DataFrame con todas las transacciones
        lista_clientes: Lista de nombres de clientes
    
    Returns:
        Dict con análisis por cliente
    """
    analisis_cartera = {}
    
    for cliente in lista_clientes:
        df_cliente = df_completo[df_completo['CLIENTE'] == cliente]
        analisis_cartera[cliente] = analizar_riesgo_cliente(df_cliente, cliente_nombre=cliente)
    
    return analisis_cartera


def clasificar_nivel_riesgo(score: int) -> NivelRiesgo:
    """
    Clasifica nivel de riesgo según score
    
    Umbrales:
    - 0-30: Bajo
    - 31-50: Medio
    - 51-75: Alto
    - 76-100: Crítico
    """
    if score < 0 or score > 100:
        return 'No Evaluado'
    
    if score <= 30:
        return 'Bajo'
    elif score <= 50:
        return 'Medio'
    elif score <= 75:
        return 'Alto'
    else:
        return 'Crítico'


def _construir_matriz_riesgo(df_cliente: pd.DataFrame, scoring: dict) -> dict:
    """Construye matriz de riesgo inherente vs residual"""
    
    # Riesgo inherente (sin controles)
    monto_total = df_cliente['MONTO (COP)'].sum() if 'MONTO (COP)' in df_cliente.columns else 0
    volumen_score = min(100, int(monto_total / 1_000_000)) if monto_total > 0 else 0
    
    riesgo_inherente = {
        'volumen': volumen_score,
        'frecuencia': min(100, len(df_cliente) * 2),
        'complejidad': scoring.get('score_operativo', 0),
        'geografia': 50  # Placeholder - depende de si opera internacionalmente
    }
    
    # Controles aplicados (reduce riesgo)
    controles = [
        'Monitoreo transaccional continuo',
        'Validación de beneficiarios',
        'Análisis de patrones GAFI',
        'Sistema de alertas automáticas'
    ]
    
    # Riesgo residual (después de controles)
    factor_reduccion = 0.7  # Controles reducen 30%
    riesgo_residual = {k: int(v * factor_reduccion) for k, v in riesgo_inherente.items()}
    
    # Gaps de control
    gaps = []
    if scoring['score_total'] > 70:
        gaps.append('Due Diligence Reforzada requerida')
    if len(df_cliente) > 1000:
        gaps.append('Volumen alto requiere revisión manual periódica')
    
    return {
        'riesgo_inherente': riesgo_inherente,
        'riesgo_residual': riesgo_residual,
        'controles_aplicados': controles,
        'gaps_control': gaps,
        'apetito_riesgo_superado': scoring['score_total'] > 75
    }


def _generar_recomendaciones(scoring: dict, alertas: list) -> List[str]:
    """Genera recomendaciones basadas en scoring y alertas"""
    recomendaciones = []
    
    nivel = scoring['nivel_riesgo']
    
    if nivel == 'Crítico':
        recomendaciones.append('🚨 ACCIÓN INMEDIATA: Suspender operaciones y realizar investigación profunda')
        recomendaciones.append('📋 Preparar reporte para UIAF en próximas 24 horas')
        recomendaciones.append('👥 Escalar a Oficial de Cumplimiento')
    
    elif nivel == 'Alto':
        recomendaciones.append('⚠️ Implementar Due Diligence Reforzada (DDR)')
        recomendaciones.append('📊 Revisión quincenal de actividad transaccional')
        recomendaciones.append('🔍 Validar origen de fondos en próximas 72 horas')
    
    elif nivel == 'Medio':
        recomendaciones.append('📌 Monitoreo mensual de actividad')
        recomendaciones.append('✅ Mantener alertas automáticas activas')
        recomendaciones.append('📄 Actualizar documentación KYC si tiene más de 1 año')
    
    else:  # Bajo
        recomendaciones.append('✅ Mantener monitoreo estándar')
        recomendaciones.append('📅 Revisión anual suficiente')
    
    # Recomendaciones por alertas
    alertas_criticas = [a for a in alertas if a['prioridad'] == 'Crítica']
    if alertas_criticas:
        recomendaciones.append(f'🔴 {len(alertas_criticas)} alertas críticas requieren atención inmediata')
    
    return recomendaciones


def _calcular_proximo_review(nivel: NivelRiesgo) -> str:
    """Calcula fecha de próximo review según nivel de riesgo"""
    hoy = datetime.now()
    
    if nivel == 'Crítico':
        dias = 7  # Semanal
    elif nivel == 'Alto':
        dias = 15  # Quincenal
    elif nivel == 'Medio':
        dias = 30  # Mensual
    else:  # Bajo
        dias = 90  # Trimestral
    
    proximo = hoy + timedelta(days=dias)
    return proximo.strftime('%Y-%m-%d')
