"""
Módulo para análisis de métricas de comportamiento transaccional

Implementa:
- Patrones temporales
- Análisis de frecuencia
- Detección de anomalías
- Métricas de consistencia
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


def calcular_metricas_comportamiento(df_cliente: pd.DataFrame) -> Dict:
    """
    Calcula métricas detalladas del comportamiento transaccional
    
    Args:
        df_cliente: DataFrame con transacciones del cliente
        
    Returns:
        Dict con métricas de comportamiento
    """
    if df_cliente.empty:
        return {'error': 'Sin datos para analizar'}
    
    metricas = {}
    
    # Métricas básicas
    metricas['total_transacciones'] = len(df_cliente)
    metricas['volumen_total'] = df_cliente['MONTO (COP)'].sum() if 'MONTO (COP)' in df_cliente.columns else 0
    metricas['volumen_promedio'] = df_cliente['MONTO (COP)'].mean() if 'MONTO (COP)' in df_cliente.columns else 0
    metricas['volumen_mediana'] = df_cliente['MONTO (COP)'].median() if 'MONTO (COP)' in df_cliente.columns else 0
    
    # Métricas de variabilidad
    if 'MONTO (COP)' in df_cliente.columns:
        metricas['desviacion_estandar'] = df_cliente['MONTO (COP)'].std()
        metricas['coeficiente_variacion'] = (metricas['desviacion_estandar'] / metricas['volumen_promedio'] * 100) if metricas['volumen_promedio'] > 0 else 0
        metricas['monto_minimo'] = df_cliente['MONTO (COP)'].min()
        metricas['monto_maximo'] = df_cliente['MONTO (COP)'].max()
        metricas['rango'] = metricas['monto_maximo'] - metricas['monto_minimo']
    
    # Análisis temporal
    if 'FECHA' in df_cliente.columns:
        df_temp = df_cliente.copy()
        df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
        df_temp = df_temp.dropna(subset=['FECHA'])
        
        if not df_temp.empty:
            fecha_min = df_temp['FECHA'].min()
            fecha_max = df_temp['FECHA'].max()
            dias_activo = (fecha_max - fecha_min).days + 1
            
            metricas['fecha_primera_tx'] = fecha_min.strftime('%Y-%m-%d')
            metricas['fecha_ultima_tx'] = fecha_max.strftime('%Y-%m-%d')
            metricas['dias_activo'] = dias_activo
            metricas['frecuencia_diaria'] = len(df_temp) / max(dias_activo, 1)
            
            # Análisis por día de la semana
            df_temp['dia_semana'] = df_temp['FECHA'].dt.dayofweek
            distribucion_dias = df_temp['dia_semana'].value_counts().sort_index()
            dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            metricas['distribucion_dias_semana'] = {dias_nombres[i]: int(distribucion_dias.get(i, 0)) for i in range(7)}
            
            # Análisis por hora (si existe)
            if df_temp['FECHA'].dt.time.notna().any():
                df_temp['hora'] = df_temp['FECHA'].dt.hour
                metricas['hora_promedio'] = df_temp['hora'].mean()
                metricas['distribucion_horaria'] = df_temp['hora'].value_counts().sort_index().to_dict()
    
    # Análisis de tipos de transacción
    if 'TIPO DE TRA' in df_cliente.columns:
        tipos_dist = df_cliente['TIPO DE TRA'].value_counts()
        metricas['tipos_transaccion'] = tipos_dist.to_dict()
        metricas['tipo_predominante'] = tipos_dist.index[0] if len(tipos_dist) > 0 else 'N/A'
        metricas['diversidad_tipos'] = len(tipos_dist)
    
    # Análisis de estados
    if 'ESTADO' in df_cliente.columns:
        estados_dist = df_cliente['ESTADO'].value_counts()
        metricas['distribucion_estados'] = estados_dist.to_dict()
        
        total_tx = len(df_cliente)
        tx_exitosas = df_cliente['ESTADO'].str.lower().str.contains('pagado|validado', na=False).sum()
        tx_rechazadas = df_cliente['ESTADO'].str.lower().str.contains('rechazado|retornado', na=False).sum()
        
        metricas['tasa_exito'] = (tx_exitosas / total_tx * 100) if total_tx > 0 else 0
        metricas['tasa_rechazo'] = (tx_rechazadas / total_tx * 100) if total_tx > 0 else 0
    
    # Análisis de beneficiarios
    if 'TIPO_PERSONA' in df_cliente.columns:
        personas_dist = df_cliente['TIPO_PERSONA'].value_counts()
        metricas['distribucion_personas'] = personas_dist.to_dict()
        
        tx_naturales = (df_cliente['TIPO_PERSONA'] == 'Natural').sum()
        tx_juridicas = (df_cliente['TIPO_PERSONA'] == 'Jurídica').sum()
        total_tx = len(df_cliente)
        
        metricas['proporcion_naturales'] = (tx_naturales / total_tx * 100) if total_tx > 0 else 0
        metricas['proporcion_juridicas'] = (tx_juridicas / total_tx * 100) if total_tx > 0 else 0
    
    # Índice de consistencia (0-100)
    consistencia_score = 100
    
    # Penalizar alta variabilidad
    if metricas.get('coeficiente_variacion', 0) > 100:
        consistencia_score -= 20
    
    # Penalizar alta tasa de rechazo
    if metricas.get('tasa_rechazo', 0) > 10:
        consistencia_score -= 30
    
    # Penalizar baja frecuencia irregular
    if metricas.get('frecuencia_diaria', 0) < 0.1:
        consistencia_score -= 10
    
    metricas['indice_consistencia'] = max(consistencia_score, 0)
    
    return metricas


def detectar_patrones_anomalos(df_cliente: pd.DataFrame, umbral_std: float = 2.5) -> Dict:
    """
    Detecta patrones anómalos en el comportamiento transaccional
    
    Args:
        df_cliente: DataFrame con transacciones del cliente
        umbral_std: Número de desviaciones estándar para considerar anomalía
        
    Returns:
        Dict con anomalías detectadas
    """
    anomalias = {
        'total_anomalias': 0,
        'anomalias_monto': [],
        'anomalias_frecuencia': [],
        'anomalias_temporales': [],
        'nivel_alerta': 'Normal'
    }
    
    if df_cliente.empty or 'MONTO (COP)' not in df_cliente.columns:
        return anomalias
    
    # 1. Detección de anomalías por monto
    montos = df_cliente['MONTO (COP)'].dropna()
    if len(montos) > 3:
        media_monto = montos.mean()
        std_monto = montos.std()
        
        if std_monto > 0:
            # Transacciones con montos anómalos
            df_anomalo = df_cliente[
                (df_cliente['MONTO (COP)'] > media_monto + umbral_std * std_monto) |
                (df_cliente['MONTO (COP)'] < media_monto - umbral_std * std_monto)
            ]
            
            if not df_anomalo.empty:
                for _, tx in df_anomalo.iterrows():
                    anomalias['anomalias_monto'].append({
                        'fecha': tx.get('FECHA', 'N/A'),
                        'monto': tx.get('MONTO (COP)', 0),
                        'desviacion': abs(tx.get('MONTO (COP)', 0) - media_monto) / std_monto if std_monto > 0 else 0,
                        'tipo': 'Alto' if tx.get('MONTO (COP)', 0) > media_monto else 'Bajo'
                    })
    
    # 2. Detección de anomalías de frecuencia
    if 'FECHA' in df_cliente.columns:
        df_temp = df_cliente.copy()
        df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
        df_temp = df_temp.dropna(subset=['FECHA'])
        
        if not df_temp.empty:
            # Agrupar por día
            df_temp['fecha_simple'] = df_temp['FECHA'].dt.date
            tx_por_dia = df_temp.groupby('fecha_simple').size()
            
            if len(tx_por_dia) > 3:
                media_diaria = tx_por_dia.mean()
                std_diaria = tx_por_dia.std()
                
                if std_diaria > 0:
                    dias_anomalos = tx_por_dia[tx_por_dia > media_diaria + umbral_std * std_diaria]
                    
                    for fecha, cantidad in dias_anomalos.items():
                        anomalias['anomalias_frecuencia'].append({
                            'fecha': str(fecha),
                            'cantidad_tx': int(cantidad),
                            'promedio_normal': media_diaria,
                            'desviacion': (cantidad - media_diaria) / std_diaria if std_diaria > 0 else 0
                        })
            
            # 3. Detección de transacciones en horarios inusuales
            if df_temp['FECHA'].dt.time.notna().any():
                df_temp['hora'] = df_temp['FECHA'].dt.hour
                
                # Horario inusual: 00:00-05:00 o 22:00-23:59
                tx_horario_inusual = df_temp[
                    (df_temp['hora'] >= 0) & (df_temp['hora'] < 5) |
                    (df_temp['hora'] >= 22)
                ]
                
                if not tx_horario_inusual.empty:
                    anomalias['anomalias_temporales'].append({
                        'tipo': 'Horario inusual',
                        'cantidad': len(tx_horario_inusual),
                        'porcentaje': (len(tx_horario_inusual) / len(df_temp) * 100)
                    })
            
            # 4. Detección de ráfagas de transacciones
            df_temp_sorted = df_temp.sort_values('FECHA')
            if len(df_temp_sorted) > 1:
                df_temp_sorted['tiempo_entre_tx'] = df_temp_sorted['FECHA'].diff().dt.total_seconds() / 60  # minutos
                
                # Más de 5 transacciones en menos de 5 minutos
                rafagas = df_temp_sorted[df_temp_sorted['tiempo_entre_tx'] < 5]
                if len(rafagas) > 5:
                    anomalias['anomalias_temporales'].append({
                        'tipo': 'Ráfaga de transacciones',
                        'cantidad': len(rafagas),
                        'detalle': 'Múltiples TX en corto período'
                    })
    
    # Calcular total de anomalías
    anomalias['total_anomalias'] = (
        len(anomalias['anomalias_monto']) +
        len(anomalias['anomalias_frecuencia']) +
        len(anomalias['anomalias_temporales'])
    )
    
    # Determinar nivel de alerta
    if anomalias['total_anomalias'] >= 10:
        anomalias['nivel_alerta'] = 'Alto'
    elif anomalias['total_anomalias'] >= 5:
        anomalias['nivel_alerta'] = 'Medio'
    else:
        anomalias['nivel_alerta'] = 'Bajo'
    
    return anomalias


def analizar_estacionalidad(df_cliente: pd.DataFrame) -> Dict:
    """
    Analiza patrones estacionales en las transacciones
    
    Args:
        df_cliente: DataFrame con transacciones del cliente
        
    Returns:
        Dict con análisis de estacionalidad
    """
    if 'FECHA' not in df_cliente.columns or df_cliente.empty:
        return {'error': 'Sin datos temporales para analizar'}
    
    df_temp = df_cliente.copy()
    df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
    df_temp = df_temp.dropna(subset=['FECHA'])
    
    if df_temp.empty:
        return {'error': 'Sin fechas válidas'}
    
    estacionalidad = {}
    
    # Análisis por mes
    df_temp['mes'] = df_temp['FECHA'].dt.month
    df_temp['nombre_mes'] = df_temp['FECHA'].dt.month_name()
    
    tx_por_mes = df_temp.groupby('nombre_mes').size()
    monto_por_mes = df_temp.groupby('nombre_mes')['MONTO (COP)'].sum() if 'MONTO (COP)' in df_temp.columns else None
    
    estacionalidad['transacciones_por_mes'] = tx_por_mes.to_dict()
    if monto_por_mes is not None:
        estacionalidad['volumen_por_mes'] = monto_por_mes.to_dict()
    
    # Análisis por trimestre
    df_temp['trimestre'] = df_temp['FECHA'].dt.quarter
    tx_por_trimestre = df_temp.groupby('trimestre').size()
    estacionalidad['transacciones_por_trimestre'] = {f'Q{k}': v for k, v in tx_por_trimestre.to_dict().items()}
    
    # Identificar mes pico
    mes_pico = tx_por_mes.idxmax() if not tx_por_mes.empty else 'N/A'
    mes_bajo = tx_por_mes.idxmin() if not tx_por_mes.empty else 'N/A'
    
    estacionalidad['mes_mayor_actividad'] = mes_pico
    estacionalidad['mes_menor_actividad'] = mes_bajo
    
    # Calcular coeficiente de estacionalidad
    if len(tx_por_mes) > 1:
        cv_estacional = (tx_por_mes.std() / tx_por_mes.mean() * 100) if tx_por_mes.mean() > 0 else 0
        estacionalidad['coeficiente_estacionalidad'] = cv_estacional
        
        if cv_estacional > 50:
            estacionalidad['patron'] = 'Alta estacionalidad'
        elif cv_estacional > 25:
            estacionalidad['patron'] = 'Estacionalidad moderada'
        else:
            estacionalidad['patron'] = 'Actividad constante'
    
    return estacionalidad


def calcular_score_consistencia(metricas: Dict, anomalias: Dict) -> Dict:
    """
    Calcula un score de consistencia comportamental
    
    Args:
        metricas: Diccionario de métricas de comportamiento
        anomalias: Diccionario de anomalías detectadas
        
    Returns:
        Dict con score y clasificación
    """
    score = 100
    factores = []
    
    # Penalizaciones por variabilidad
    cv = metricas.get('coeficiente_variacion', 0)
    if cv > 150:
        score -= 30
        factores.append('Muy alta variabilidad en montos')
    elif cv > 100:
        score -= 20
        factores.append('Alta variabilidad en montos')
    elif cv > 50:
        score -= 10
        factores.append('Moderada variabilidad en montos')
    
    # Penalizaciones por anomalías
    total_anomalias = anomalias.get('total_anomalias', 0)
    if total_anomalias >= 10:
        score -= 25
        factores.append(f'Múltiples anomalías detectadas ({total_anomalias})')
    elif total_anomalias >= 5:
        score -= 15
        factores.append(f'Anomalías moderadas ({total_anomalias})')
    
    # Penalizaciones por baja tasa de éxito
    tasa_exito = metricas.get('tasa_exito', 100)
    if tasa_exito < 70:
        score -= 20
        factores.append(f'Baja tasa de éxito ({tasa_exito:.1f}%)')
    elif tasa_exito < 85:
        score -= 10
        factores.append(f'Tasa de éxito moderada ({tasa_exito:.1f}%)')
    
    # Bonificaciones por estabilidad
    if metricas.get('indice_consistencia', 0) >= 90:
        score += 10
        factores.append('Comportamiento muy consistente')
    
    score = max(0, min(score, 100))
    
    if score >= 80:
        clasificacion = 'Excelente'
        color = '🟢'
    elif score >= 60:
        clasificacion = 'Bueno'
        color = '🟡'
    elif score >= 40:
        clasificacion = 'Regular'
        color = '🟠'
    else:
        clasificacion = 'Deficiente'
        color = '🔴'
    
    return {
        'score': score,
        'clasificacion': clasificacion,
        'color': color,
        'factores': factores
    }
