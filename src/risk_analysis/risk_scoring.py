"""
Sistema de scoring de riesgo
Calcula scores GAFI, UIAF y operativos
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict
from .risk_contracts import ScoreRiesgo, crear_score_vacio


def calcular_score_integral(
    df_cliente: pd.DataFrame,
    perfil_gafi: Optional[Dict] = None
) -> ScoreRiesgo:
    """
    Calcula score integral de riesgo combinando múltiples factores
    
    Ponderación:
    - GAFI: 40%
    - UIAF: 35%
    - Operativo: 25%
    """
    if df_cliente is None or df_cliente.empty:
        return crear_score_vacio()
    
    # Calcular scores individuales
    score_gafi = _calcular_score_gafi(df_cliente, perfil_gafi)
    score_uiaf = calcular_score_uiaf(df_cliente)
    score_operativo = calcular_score_operativo(df_cliente)
    
    # Ponderación
    ponderacion = {
        'gafi': 0.40,
        'uiaf': 0.35,
        'operativo': 0.25
    }
    
    # Score total ponderado
    score_total = int(
        score_gafi * ponderacion['gafi'] +
        score_uiaf * ponderacion['uiaf'] +
        score_operativo * ponderacion['operativo']
    )
    
    # Identificar factores críticos
    factores_criticos = []
    if score_gafi > 70:
        factores_criticos.append('Perfil GAFI de alto riesgo')
    if score_uiaf > 70:
        factores_criticos.append('Señales UIAF detectadas')
    if score_operativo > 70:
        factores_criticos.append('Riesgo operativo elevado')
    
    # Importar función de clasificación
    from .risk_engine import clasificar_nivel_riesgo
    
    return {
        'score_total': score_total,
        'score_gafi': score_gafi,
        'score_uiaf': score_uiaf,
        'score_operativo': score_operativo,
        'nivel_riesgo': clasificar_nivel_riesgo(score_total),
        'factores_criticos': factores_criticos,
        'ponderacion': ponderacion
    }


def _calcular_score_gafi(df_cliente: pd.DataFrame, perfil_gafi: Optional[Dict]) -> int:
    """Score basado en criterios GAFI"""
    if perfil_gafi and 'score_riesgo' in perfil_gafi:
        return perfil_gafi['score_riesgo']
    
    # Fallback: calcular score básico
    score = 0
    
    # Volumen
    monto_total = df_cliente['MONTO (COP)'].sum() if 'MONTO (COP)' in df_cliente.columns else 0
    if monto_total > 500_000_000:
        score += 25
    elif monto_total > 100_000_000:
        score += 15
    
    # Frecuencia
    total_tx = len(df_cliente)
    if 'FECHA' in df_cliente.columns:
        fechas = pd.to_datetime(df_cliente['FECHA'], errors='coerce').dropna()
        if len(fechas) > 0:
            dias = (fechas.max() - fechas.min()).days
            freq = total_tx / max(dias, 1)
            if freq > 20:
                score += 20
            elif freq > 10:
                score += 10
    
    # Diversidad
    if 'TIPO DE TRA' in df_cliente.columns:
        tipos = df_cliente['TIPO DE TRA'].nunique()
        score += min(15, tipos * 4)
    
    return min(score, 100)


def calcular_score_uiaf(df_cliente: pd.DataFrame) -> int:
    """
    Score basado en señales de alerta UIAF
    Circular Externa 55 de 2016
    """
    score = 0
    
    if df_cliente.empty:
        return 0
    
    # 1. Transacciones en efectivo altas (>$10M)
    if 'MONTO (COP)' in df_cliente.columns:
        tx_altas = (df_cliente['MONTO (COP)'] > 10_000_000).sum()
        if tx_altas > 10:
            score += 20
        elif tx_altas > 5:
            score += 10
    
    # 2. Fragmentación (múltiples TX pequeñas)
    if 'MONTO (COP)' in df_cliente.columns and 'FECHA' in df_cliente.columns:
        df_temp = df_cliente.copy()
        df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
        df_diario = df_temp.groupby(df_temp['FECHA'].dt.date)['MONTO (COP)'].agg(['count', 'sum'])
        dias_fragmentados = ((df_diario['count'] > 5) & (df_diario['sum'] > 50_000_000)).sum()
        if dias_fragmentados > 3:
            score += 25
        elif dias_fragmentados > 1:
            score += 15
    
    # 3. Inconsistencias en actividad
    if 'ESTADO' in df_cliente.columns:
        rechazos = df_cliente['ESTADO'].str.lower().str.contains('rechaz|retor', na=False).sum()
        tasa_rechazo = (rechazos / len(df_cliente)) * 100 if len(df_cliente) > 0 else 0
        if tasa_rechazo > 20:
            score += 20
        elif tasa_rechazo > 10:
            score += 10
    
    return min(score, 100)


def calcular_score_operativo(df_cliente: pd.DataFrame) -> int:
    """Score de riesgo operativo (errores, inconsistencias, complejidad)"""
    score = 0
    
    if df_cliente.empty:
        return 0
    
    # 1. Complejidad de operaciones
    if 'TIPO DE TRA' in df_cliente.columns:
        diversidad = df_cliente['TIPO DE TRA'].nunique()
        if diversidad >= 5:
            score += 20
        elif diversidad >= 3:
            score += 10
    
    # 2. Volatilidad de montos
    if 'MONTO (COP)' in df_cliente.columns:
        montos = df_cliente['MONTO (COP)'].dropna()
        if len(montos) > 0 and montos.mean() > 0:
            cv = montos.std() / montos.mean()
            if cv > 1.5:  # Alta volatilidad
                score += 15
            elif cv > 1.0:
                score += 8
    
    # 3. Tasa de errores/rechazos
    if 'ESTADO' in df_cliente.columns:
        errores = df_cliente['ESTADO'].str.lower().str.contains('rechaz|error|retor', na=False).sum()
        tasa_error = (errores / len(df_cliente)) * 100 if len(df_cliente) > 0 else 0
        if tasa_error > 15:
            score += 25
        elif tasa_error > 10:
            score += 15
    
    # 4. Concentración temporal
    if 'FECHA' in df_cliente.columns:
        df_temp = df_cliente.copy()
        df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
        df_semanal = df_temp.groupby(pd.Grouper(key='FECHA', freq='W')).size()
        if len(df_semanal) > 0 and df_semanal.mean() > 0:
            if df_semanal.max() > df_semanal.mean() * 3:  # Semana con 3x promedio
                score += 15
    
    # 5. Uso de múltiples beneficiarios
    if 'TIPO_PERSONA' in df_cliente.columns:
        beneficiarios = df_cliente['TIPO_PERSONA'].nunique()
        if beneficiarios > 50:
            score += 10
    
    return min(score, 100)
