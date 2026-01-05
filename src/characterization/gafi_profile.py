"""
Módulo para clasificación de perfiles según recomendaciones GAFI
(Grupo de Acción Financiera Internacional)

Implementa clasificación de riesgo basada en:
- Volumen transaccional
- Frecuencia de operaciones
- Tipos de transacciones
- Comportamiento histórico
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List


def clasificar_perfil_gafi(df_cliente: pd.DataFrame) -> Dict[str, any]:
    """
    Clasifica el perfil de riesgo de un cliente según criterios GAFI
    
    Args:
        df_cliente: DataFrame con transacciones del cliente
        
    Returns:
        Dict con perfil de riesgo y detalles
    """
    if df_cliente.empty:
        return {
            'perfil': 'Sin Datos',
            'nivel_riesgo': 'N/A',
            'score': 0,
            'factores': []
        }
    
    # Calcular métricas base
    total_tx = len(df_cliente)
    volumen_total = df_cliente['MONTO (COP)'].sum() if 'MONTO (COP)' in df_cliente.columns else 0
    promedio_tx = df_cliente['MONTO (COP)'].mean() if 'MONTO (COP)' in df_cliente.columns else 0
    
    # Calcular período de actividad
    if 'FECHA' in df_cliente.columns:
        fecha_min = df_cliente['FECHA'].min()
        fecha_max = df_cliente['FECHA'].max()
        dias_activo = (fecha_max - fecha_min).days if pd.notna(fecha_min) and pd.notna(fecha_max) else 1
        frecuencia_diaria = total_tx / max(dias_activo, 1)
    else:
        frecuencia_diaria = 0
    
    # Calcular score de riesgo (0-100)
    score = 0
    factores_riesgo = []
    
    # Factor 1: Volumen alto (>$100M COP)
    if volumen_total > 100_000_000:
        score += 20
        factores_riesgo.append(f"Volumen alto: ${volumen_total:,.0f}")
    
    # Factor 2: Transacciones promedio altas (>$10M COP)
    if promedio_tx > 10_000_000:
        score += 15
        factores_riesgo.append(f"Monto promedio alto: ${promedio_tx:,.0f}")
    
    # Factor 3: Alta frecuencia (>10 TX/día)
    if frecuencia_diaria > 10:
        score += 15
        factores_riesgo.append(f"Alta frecuencia: {frecuencia_diaria:.1f} TX/día")
    
    # Factor 4: Diversidad de tipos de transacción
    if 'TIPO DE TRA' in df_cliente.columns:
        tipos_unicos = df_cliente['TIPO DE TRA'].nunique()
        if tipos_unicos >= 3:
            score += 10
            factores_riesgo.append(f"Diversidad de TX: {tipos_unicos} tipos")
    
    # Factor 5: Tasa de rechazo/retorno alta
    if 'ESTADO' in df_cliente.columns:
        tx_rechazadas = df_cliente['ESTADO'].str.lower().str.contains('rechazado|retornado', na=False).sum()
        tasa_rechazo = (tx_rechazadas / total_tx * 100) if total_tx > 0 else 0
        if tasa_rechazo > 15:
            score += 20
            factores_riesgo.append(f"Alta tasa de rechazo: {tasa_rechazo:.1f}%")
    
    # Factor 6: Transacciones con personas jurídicas
    if 'TIPO_PERSONA' in df_cliente.columns:
        tx_juridicas = (df_cliente['TIPO_PERSONA'] == 'Jurídica').sum()
        proporcion_juridicas = (tx_juridicas / total_tx * 100) if total_tx > 0 else 0
        if proporcion_juridicas > 50:
            score += 10
            factores_riesgo.append(f"Alta proporción jurídicas: {proporcion_juridicas:.1f}%")
    
    # Determinar nivel de riesgo
    if score >= 60:
        nivel_riesgo = 'Alto'
        perfil = 'Cliente de Alto Riesgo - Requiere Monitoreo Reforzado'
    elif score >= 30:
        nivel_riesgo = 'Medio'
        perfil = 'Cliente de Riesgo Medio - Monitoreo Estándar'
    else:
        nivel_riesgo = 'Bajo'
        perfil = 'Cliente de Bajo Riesgo - Monitoreo Normal'
    
    return {
        'perfil': perfil,
        'nivel_riesgo': nivel_riesgo,
        'score': min(score, 100),
        'factores': factores_riesgo,
        'metricas': {
            'total_transacciones': total_tx,
            'volumen_total': volumen_total,
            'promedio_transaccion': promedio_tx,
            'frecuencia_diaria': frecuencia_diaria
        }
    }


def obtener_recomendaciones_gafi(perfil_riesgo: Dict) -> List[str]:
    """
    Genera recomendaciones de acción según el perfil de riesgo GAFI
    
    Args:
        perfil_riesgo: Diccionario con clasificación de riesgo
        
    Returns:
        Lista de recomendaciones específicas
    """
    recomendaciones = []
    nivel = perfil_riesgo.get('nivel_riesgo', 'N/A')
    score = perfil_riesgo.get('score', 0)
    
    if nivel == 'Alto':
        recomendaciones = [
            "🔴 Implementar Due Diligence Reforzado (DDR)",
            "🔴 Solicitar documentación adicional de soporte",
            "🔴 Revisar origen y destino de fondos",
            "🔴 Monitoreo continuo de transacciones",
            "🔴 Reportar a Oficial de Cumplimiento",
            "🔴 Considerar límites transaccionales temporales"
        ]
    elif nivel == 'Medio':
        recomendaciones = [
            "🟡 Aplicar Due Diligence Estándar",
            "🟡 Revisar periódicamente el perfil transaccional",
            "🟡 Documentar actividad inusual",
            "🟡 Monitoreo mensual de patrones",
            "🟡 Validar información de beneficiarios finales"
        ]
    else:
        recomendaciones = [
            "🟢 Mantener Due Diligence Simplificado",
            "🟢 Monitoreo trimestral de actividad",
            "🟢 Actualización anual de información",
            "🟢 Validar cambios significativos en comportamiento"
        ]
    
    # Recomendaciones específicas por factores
    factores = perfil_riesgo.get('factores', [])
    for factor in factores:
        if 'rechazo' in factor.lower():
            recomendaciones.append("⚠️ Investigar causas de rechazos frecuentes")
        if 'frecuencia' in factor.lower():
            recomendaciones.append("⚠️ Analizar patrón horario de transacciones")
        if 'jurídicas' in factor.lower():
            recomendaciones.append("⚠️ Verificar estructura corporativa de beneficiarios")
    
    return recomendaciones


def generar_reporte_gafi(df_completo: pd.DataFrame, clientes: List[str]) -> pd.DataFrame:
    """
    Genera reporte consolidado de perfiles GAFI para todos los clientes
    
    Args:
        df_completo: DataFrame con todas las transacciones
        clientes: Lista de nombres de clientes
        
    Returns:
        DataFrame con resumen de perfiles GAFI
    """
    reportes = []
    
    for cliente in clientes:
        df_cliente = df_completo[df_completo['CLIENTE'] == cliente]
        perfil = clasificar_perfil_gafi(df_cliente)
        
        reportes.append({
            'Cliente': cliente,
            'Nivel_Riesgo': perfil['nivel_riesgo'],
            'Score': perfil['score'],
            'Perfil': perfil['perfil'],
            'Total_TX': perfil['metricas']['total_transacciones'],
            'Volumen': perfil['metricas']['volumen_total'],
            'Promedio_TX': perfil['metricas']['promedio_transaccion'],
            'Factores_Riesgo': len(perfil['factores'])
        })
    
    df_reporte = pd.DataFrame(reportes)
    
    # Ordenar por score descendente
    df_reporte = df_reporte.sort_values('Score', ascending=False)
    
    return df_reporte


def calcular_tendencia_riesgo(df_cliente: pd.DataFrame, ventana_dias: int = 30) -> Dict:
    """
    Calcula la tendencia de riesgo en el tiempo para un cliente
    
    Args:
        df_cliente: DataFrame con transacciones del cliente
        ventana_dias: Días para análisis de ventana móvil
        
    Returns:
        Dict con análisis de tendencia
    """
    if 'FECHA' not in df_cliente.columns or df_cliente.empty:
        return {'tendencia': 'Sin datos', 'variacion': 0}
    
    df_sorted = df_cliente.sort_values('FECHA')
    fecha_max = df_sorted['FECHA'].max()
    fecha_limite = fecha_max - pd.Timedelta(days=ventana_dias)
    
    # Período reciente
    df_reciente = df_sorted[df_sorted['FECHA'] > fecha_limite]
    
    # Período anterior
    fecha_anterior = fecha_limite - pd.Timedelta(days=ventana_dias)
    df_anterior = df_sorted[(df_sorted['FECHA'] > fecha_anterior) & (df_sorted['FECHA'] <= fecha_limite)]
    
    if df_anterior.empty or df_reciente.empty:
        return {'tendencia': 'Insuficientes datos', 'variacion': 0}
    
    # Calcular scores
    perfil_reciente = clasificar_perfil_gafi(df_reciente)
    perfil_anterior = clasificar_perfil_gafi(df_anterior)
    
    score_reciente = perfil_reciente['score']
    score_anterior = perfil_anterior['score']
    
    variacion = score_reciente - score_anterior
    
    if variacion > 10:
        tendencia = 'Incremento de riesgo'
    elif variacion < -10:
        tendencia = 'Disminución de riesgo'
    else:
        tendencia = 'Estable'
    
    return {
        'tendencia': tendencia,
        'variacion': variacion,
        'score_actual': score_reciente,
        'score_anterior': score_anterior
    }
