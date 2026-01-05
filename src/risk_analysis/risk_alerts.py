"""
Sistema de alertas de riesgo
Genera y prioriza alertas automáticas
"""

import pandas as pd
import uuid
from datetime import datetime
from typing import List, Dict
from .risk_contracts import AlertaRiesgo, TipoAlerta, PrioridadAlerta


def generar_alertas_automaticas(df_cliente: pd.DataFrame, scoring: Dict) -> List[AlertaRiesgo]:
    """
    Genera alertas automáticas basadas en patrones detectados
    
    Args:
        df_cliente: DataFrame con transacciones
        scoring: Dict con scores calculados
    
    Returns:
        Lista de AlertaRiesgo
    """
    alertas = []
    
    if df_cliente.empty:
        return alertas
    
    # 1. Alertas de volumen alto
    alertas.extend(_alertas_volumen(df_cliente))
    
    # 2. Alertas UIAF
    alertas.extend(_alertas_uiaf(df_cliente))
    
    # 3. Alertas operacionales
    alertas.extend(_alertas_operacionales(df_cliente))
    
    # 4. Alertas por score crítico
    if scoring['score_total'] >= 76:
        alertas.append({
            'id_alerta': f"SCORE-{uuid.uuid4().hex[:8].upper()}",
            'tipo': 'Compliance',
            'prioridad': 'Crítica',
            'titulo': 'Score de riesgo crítico',
            'descripcion': f'Score total de {scoring["score_total"]} supera umbral crítico de 75',
            'valor_detectado': float(scoring['score_total']),
            'umbral': 75.0,
            'accion_requerida': 'Suspender operaciones y realizar investigación inmediata',
            'fecha_deteccion': datetime.now().isoformat(),
            'requiere_reporte_uiaf': True,
            'dias_para_accion': 1
        })
    
    # Priorizar alertas
    alertas_priorizadas = priorizar_alertas(alertas)
    
    return alertas_priorizadas


def _alertas_volumen(df_cliente: pd.DataFrame) -> List[AlertaRiesgo]:
    """Genera alertas relacionadas con volumen de transacciones"""
    alertas = []
    
    if 'MONTO (COP)' not in df_cliente.columns:
        return alertas
    
    monto_total = df_cliente['MONTO (COP)'].sum()
    monto_promedio = df_cliente['MONTO (COP)'].mean()
    
    # Alerta: Volumen total muy alto
    if monto_total > 1_000_000_000:  # >$1,000M
        alertas.append({
            'id_alerta': f"VOL-{uuid.uuid4().hex[:8].upper()}",
            'tipo': 'UIAF',
            'prioridad': 'Alta',
            'titulo': 'Volumen transaccional extremadamente alto',
            'descripcion': f'Volumen total de ${monto_total:,.0f} supera significativamente umbrales normales',
            'valor_detectado': float(monto_total),
            'umbral': 1_000_000_000.0,
            'accion_requerida': 'Validar origen de fondos y justificación económica',
            'fecha_deteccion': datetime.now().isoformat(),
            'requiere_reporte_uiaf': True,
            'dias_para_accion': 3
        })
    
    # Alerta: Ticket promedio muy alto
    if monto_promedio > 50_000_000:  # >$50M
        alertas.append({
            'id_alerta': f"TKT-{uuid.uuid4().hex[:8].upper()}",
            'tipo': 'UIAF',
            'prioridad': 'Media',
            'titulo': 'Ticket promedio inusualmente alto',
            'descripcion': f'Monto promedio de ${monto_promedio:,.0f} por transacción es atípico',
            'valor_detectado': float(monto_promedio),
            'umbral': 50_000_000.0,
            'accion_requerida': 'Revisar perfil transaccional y naturaleza del negocio',
            'fecha_deteccion': datetime.now().isoformat(),
            'requiere_reporte_uiaf': False,
            'dias_para_accion': 7
        })
    
    return alertas


def _alertas_uiaf(df_cliente: pd.DataFrame) -> List[AlertaRiesgo]:
    """Genera alertas relacionadas con señales UIAF"""
    alertas = []
    
    # Alerta: Fragmentación (smurfing)
    if 'MONTO (COP)' in df_cliente.columns and 'FECHA' in df_cliente.columns:
        df_temp = df_cliente.copy()
        df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
        df_diario = df_temp.groupby(df_temp['FECHA'].dt.date)['MONTO (COP)'].agg(['count', 'sum'])
        
        # Detectar días con muchas TX pequeñas que suman mucho
        dias_sospechosos = ((df_diario['count'] > 10) & (df_diario['sum'] > 100_000_000)).sum()
        
        if dias_sospechosos > 2:
            alertas.append({
                'id_alerta': f"FRAG-{uuid.uuid4().hex[:8].upper()}",
                'tipo': 'UIAF',
                'prioridad': 'Crítica',
                'titulo': 'Posible fragmentación (Smurfing)',
                'descripcion': f'Detectados {dias_sospechosos} días con múltiples transacciones que suman montos altos',
                'valor_detectado': float(dias_sospechosos),
                'umbral': 2.0,
                'accion_requerida': 'Investigar patrón de fragmentación y reportar a UIAF si se confirma',
                'fecha_deteccion': datetime.now().isoformat(),
                'requiere_reporte_uiaf': True,
                'dias_para_accion': 2
            })
    
    # Alerta: Alta tasa de rechazo (posible lavado fallido)
    if 'ESTADO' in df_cliente.columns:
        rechazos = df_cliente['ESTADO'].str.lower().str.contains('rechaz|retor', na=False).sum()
        tasa_rechazo = (rechazos / len(df_cliente)) * 100 if len(df_cliente) > 0 else 0
        
        if tasa_rechazo > 25:
            alertas.append({
                'id_alerta': f"RECH-{uuid.uuid4().hex[:8].upper()}",
                'tipo': 'Fraude',
                'prioridad': 'Alta',
                'titulo': 'Tasa de rechazo extremadamente alta',
                'descripcion': f'Tasa de rechazo de {tasa_rechazo:.1f}% sugiere intentos fallidos repetidos',
                'valor_detectado': tasa_rechazo,
                'umbral': 25.0,
                'accion_requerida': 'Investigar motivos de rechazo y posible intento de fraude',
                'fecha_deteccion': datetime.now().isoformat(),
                'requiere_reporte_uiaf': False,
                'dias_para_accion': 5
            })
    
    return alertas


def _alertas_operacionales(df_cliente: pd.DataFrame) -> List[AlertaRiesgo]:
    """Genera alertas operacionales"""
    alertas = []
    
    # Alerta: Volumen de transacciones muy alto
    if len(df_cliente) > 1000:
        alertas.append({
            'id_alerta': f"FREQ-{uuid.uuid4().hex[:8].upper()}",
            'tipo': 'Operacional',
            'prioridad': 'Media',
            'titulo': 'Volumen transaccional muy alto',
            'descripcion': f'{len(df_cliente):,} transacciones requieren revisión periódica',
            'valor_detectado': float(len(df_cliente)),
            'umbral': 1000.0,
            'accion_requerida': 'Implementar revisiones manuales muestrales periódicas',
            'fecha_deteccion': datetime.now().isoformat(),
            'requiere_reporte_uiaf': False,
            'dias_para_accion': 14
        })
    
    # Alerta: Alta diversidad de tipos de transacción
    if 'TIPO DE TRA' in df_cliente.columns:
        diversidad = df_cliente['TIPO DE TRA'].nunique()
        if diversidad >= 6:
            alertas.append({
                'id_alerta': f"DIV-{uuid.uuid4().hex[:8].upper()}",
                'tipo': 'Compliance',
                'prioridad': 'Baja',
                'titulo': 'Alta diversidad de tipos de transacción',
                'descripcion': f'{diversidad} tipos diferentes de transacciones detectados',
                'valor_detectado': float(diversidad),
                'umbral': 6.0,
                'accion_requerida': 'Validar coherencia con actividad económica del cliente',
                'fecha_deteccion': datetime.now().isoformat(),
                'requiere_reporte_uiaf': False,
                'dias_para_accion': 30
            })
    
    return alertas


def priorizar_alertas(alertas: List[AlertaRiesgo]) -> List[AlertaRiesgo]:
    """
    Prioriza alertas por criticidad
    
    Orden: Crítica > Alta > Media > Baja
    """
    orden_prioridad = {'Crítica': 1, 'Alta': 2, 'Media': 3, 'Baja': 4}
    
    alertas_ordenadas = sorted(
        alertas,
        key=lambda x: (orden_prioridad.get(x['prioridad'], 5), x.get('dias_para_accion', 999))
    )
    
    return alertas_ordenadas


def clasificar_alerta(
    tipo: str,
    valor: float,
    umbral: float,
    descripcion: str
) -> AlertaRiesgo:
    """
    Clasifica y crea una alerta individual
    
    Args:
        tipo: Tipo de alerta
        valor: Valor detectado
        umbral: Umbral de referencia
        descripcion: Descripción de la alerta
    
    Returns:
        AlertaRiesgo
    """
    # Determinar prioridad según desviación del umbral
    desviacion = (valor - umbral) / umbral if umbral > 0 else 0
    
    if desviacion > 1.0:  # >100% del umbral
        prioridad: PrioridadAlerta = 'Crítica'
        dias = 2
    elif desviacion > 0.5:  # >50% del umbral
        prioridad = 'Alta'
        dias = 5
    elif desviacion > 0.2:  # >20% del umbral
        prioridad = 'Media'
        dias = 10
    else:
        prioridad = 'Baja'
        dias = 30
    
    return {
        'id_alerta': f"CUST-{uuid.uuid4().hex[:8].upper()}",
        'tipo': tipo,
        'prioridad': prioridad,
        'titulo': f'Alerta {tipo}',
        'descripcion': descripcion,
        'valor_detectado': valor,
        'umbral': umbral,
        'accion_requerida': 'Revisar y validar',
        'fecha_deteccion': datetime.now().isoformat(),
        'requiere_reporte_uiaf': prioridad in ['Crítica', 'Alta'],
        'dias_para_accion': dias
    }
