"""
Módulo para evaluación de banderas de riesgo (Red Flags)

Implementa detección de señales de alerta según:
- Regulaciones UIAF (Unidad de Información y Análisis Financiero)
- Recomendaciones GAFI
- Políticas de Prevención de Lavado de Activos (PLA)
- Financiación del Terrorismo (FT)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


# Umbrales de alerta (en COP)
UMBRAL_TRANSACCION_ALTA = 10_000_000  # $10M
UMBRAL_VOLUMEN_DIARIO_ALTO = 50_000_000  # $50M
UMBRAL_VOLUMEN_MENSUAL_ALTO = 500_000_000  # $500M
UMBRAL_FRECUENCIA_DIARIA_ALTA = 20  # 20 TX por día


def evaluar_banderas_riesgo(df_cliente: pd.DataFrame) -> Dict:
    """
    Evalúa todas las banderas de riesgo para un cliente
    
    Args:
        df_cliente: DataFrame con transacciones del cliente
        
    Returns:
        Dict con banderas detectadas y score de riesgo
    """
    if df_cliente.empty:
        return {
            'banderas': [],
            'total_banderas': 0,
            'nivel_alerta': 'Sin datos',
            'score_riesgo': 0
        }
    
    banderas = []
    
    # 1. Transacciones de alto valor
    banderas.extend(_detectar_transacciones_alto_valor(df_cliente))
    
    # 2. Volumen inusual
    banderas.extend(_detectar_volumen_inusual(df_cliente))
    
    # 3. Fragmentación (Structuring/Smurfing)
    banderas.extend(_detectar_fragmentacion(df_cliente))
    
    # 4. Actividad inusual temporal
    banderas.extend(_detectar_patrones_temporales_sospechosos(df_cliente))
    
    # 5. Alta tasa de rechazo
    banderas.extend(_detectar_alta_tasa_rechazo(df_cliente))
    
    # 6. Cambios bruscos en comportamiento
    banderas.extend(_detectar_cambios_comportamiento(df_cliente))
    
    # 7. Transacciones con jurisdicciones de alto riesgo (si aplica)
    banderas.extend(_detectar_transacciones_riesgosas(df_cliente))
    
    # 8. Inconsistencias en datos
    banderas.extend(_detectar_inconsistencias(df_cliente))
    
    total_banderas = len(banderas)
    
    # Calcular score de riesgo
    score = calcular_score_riesgo_interno(banderas)
    
    # Determinar nivel de alerta
    if score >= 70 or total_banderas >= 5:
        nivel = 'Crítico'
    elif score >= 50 or total_banderas >= 3:
        nivel = 'Alto'
    elif score >= 30 or total_banderas >= 1:
        nivel = 'Medio'
    else:
        nivel = 'Bajo'
    
    return {
        'banderas': banderas,
        'total_banderas': total_banderas,
        'nivel_alerta': nivel,
        'score_riesgo': score,
        'requiere_reporte_uiaf': score >= 70,
        'requiere_investigacion': score >= 50
    }


def _detectar_transacciones_alto_valor(df_cliente: pd.DataFrame) -> List[Dict]:
    """Detecta transacciones individuales de alto valor"""
    banderas = []
    
    if 'MONTO (COP)' not in df_cliente.columns:
        return banderas
    
    df_alto_valor = df_cliente[df_cliente['MONTO (COP)'] >= UMBRAL_TRANSACCION_ALTA]
    
    if not df_alto_valor.empty:
        cantidad = len(df_alto_valor)
        monto_total = df_alto_valor['MONTO (COP)'].sum()
        monto_max = df_alto_valor['MONTO (COP)'].max()
        
        banderas.append({
            'tipo': 'Transacciones de Alto Valor',
            'severidad': 'Media' if cantidad < 5 else 'Alta',
            'descripcion': f'{cantidad} transacciones con monto >= ${UMBRAL_TRANSACCION_ALTA:,}',
            'detalles': {
                'cantidad': cantidad,
                'monto_total': monto_total,
                'monto_maximo': monto_max
            },
            'recomendacion': 'Verificar origen y destino de fondos',
            'puntos': 15 if cantidad < 5 else 25
        })
    
    return banderas


def _detectar_volumen_inusual(df_cliente: pd.DataFrame) -> List[Dict]:
    """Detecta volúmenes transaccionales inusuales"""
    banderas = []
    
    if 'MONTO (COP)' not in df_cliente.columns or 'FECHA' not in df_cliente.columns:
        return banderas
    
    df_temp = df_cliente.copy()
    df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
    df_temp = df_temp.dropna(subset=['FECHA'])
    
    if df_temp.empty:
        return banderas
    
    # Volumen diario
    df_temp['fecha_simple'] = df_temp['FECHA'].dt.date
    volumen_diario = df_temp.groupby('fecha_simple')['MONTO (COP)'].sum()
    
    dias_alto_volumen = volumen_diario[volumen_diario >= UMBRAL_VOLUMEN_DIARIO_ALTO]
    
    if not dias_alto_volumen.empty:
        banderas.append({
            'tipo': 'Volumen Diario Inusual',
            'severidad': 'Alta',
            'descripcion': f'{len(dias_alto_volumen)} días con volumen >= ${UMBRAL_VOLUMEN_DIARIO_ALTO:,}',
            'detalles': {
                'dias_afectados': len(dias_alto_volumen),
                'volumen_maximo_dia': dias_alto_volumen.max(),
                'fechas': [str(f) for f in dias_alto_volumen.index.tolist()[:5]]
            },
            'recomendacion': 'Analizar justificación de volúmenes altos',
            'puntos': 20
        })
    
    # Volumen mensual
    df_temp['mes'] = df_temp['FECHA'].dt.to_period('M')
    volumen_mensual = df_temp.groupby('mes')['MONTO (COP)'].sum()
    
    meses_alto_volumen = volumen_mensual[volumen_mensual >= UMBRAL_VOLUMEN_MENSUAL_ALTO]
    
    if not meses_alto_volumen.empty:
        banderas.append({
            'tipo': 'Volumen Mensual Elevado',
            'severidad': 'Media',
            'descripcion': f'{len(meses_alto_volumen)} meses con volumen >= ${UMBRAL_VOLUMEN_MENSUAL_ALTO:,}',
            'detalles': {
                'meses_afectados': len(meses_alto_volumen),
                'volumen_maximo_mes': meses_alto_volumen.max()
            },
            'recomendacion': 'Revisar actividad comercial y operativa',
            'puntos': 15
        })
    
    return banderas


def _detectar_fragmentacion(df_cliente: pd.DataFrame) -> List[Dict]:
    """Detecta posible fragmentación de transacciones (Structuring)"""
    banderas = []
    
    if 'MONTO (COP)' not in df_cliente.columns or 'FECHA' not in df_cliente.columns:
        return banderas
    
    df_temp = df_cliente.copy()
    df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
    df_temp = df_temp.dropna(subset=['FECHA'])
    
    if df_temp.empty:
        return banderas
    
    # Detectar múltiples transacciones en el mismo día con montos similares
    df_temp['fecha_simple'] = df_temp['FECHA'].dt.date
    
    for fecha, grupo in df_temp.groupby('fecha_simple'):
        if len(grupo) >= 5:  # 5 o más TX en un día
            montos = grupo['MONTO (COP)']
            
            # Verificar si los montos son similares (±20%)
            media_monto = montos.mean()
            montos_similares = montos[(montos >= media_monto * 0.8) & (montos <= media_monto * 1.2)]
            
            if len(montos_similares) >= 5:
                banderas.append({
                    'tipo': 'Posible Fragmentación (Structuring)',
                    'severidad': 'Alta',
                    'descripcion': f'{len(montos_similares)} TX con montos similares en {fecha}',
                    'detalles': {
                        'fecha': str(fecha),
                        'cantidad_tx': len(montos_similares),
                        'monto_promedio': media_monto,
                        'monto_total_dia': montos.sum()
                    },
                    'recomendacion': 'Investigar motivo de fragmentación - Posible evasión de controles',
                    'puntos': 30
                })
                break  # Solo reportar una vez
    
    return banderas


def _detectar_patrones_temporales_sospechosos(df_cliente: pd.DataFrame) -> List[Dict]:
    """Detecta patrones temporales sospechosos"""
    banderas = []
    
    if 'FECHA' not in df_cliente.columns:
        return banderas
    
    df_temp = df_cliente.copy()
    df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
    df_temp = df_temp.dropna(subset=['FECHA'])
    
    if df_temp.empty:
        return banderas
    
    # 1. Frecuencia diaria muy alta
    df_temp['fecha_simple'] = df_temp['FECHA'].dt.date
    tx_por_dia = df_temp.groupby('fecha_simple').size()
    
    dias_alta_frecuencia = tx_por_dia[tx_por_dia >= UMBRAL_FRECUENCIA_DIARIA_ALTA]
    
    if not dias_alta_frecuencia.empty:
        banderas.append({
            'tipo': 'Frecuencia Diaria Excesiva',
            'severidad': 'Media',
            'descripcion': f'{len(dias_alta_frecuencia)} días con >= {UMBRAL_FRECUENCIA_DIARIA_ALTA} transacciones',
            'detalles': {
                'dias_afectados': len(dias_alta_frecuencia),
                'max_tx_dia': dias_alta_frecuencia.max()
            },
            'recomendacion': 'Verificar naturaleza de actividad comercial',
            'puntos': 15
        })
    
    # 2. Transacciones en horarios inusuales
    if df_temp['FECHA'].dt.time.notna().any():
        df_temp['hora'] = df_temp['FECHA'].dt.hour
        tx_madrugada = df_temp[(df_temp['hora'] >= 0) & (df_temp['hora'] < 6)]
        
        if len(tx_madrugada) > len(df_temp) * 0.2:  # Más del 20% en madrugada
            banderas.append({
                'tipo': 'Transacciones en Horario Inusual',
                'severidad': 'Baja',
                'descripcion': f'{len(tx_madrugada)} TX entre 00:00 y 06:00',
                'detalles': {
                    'cantidad': len(tx_madrugada),
                    'porcentaje': (len(tx_madrugada) / len(df_temp) * 100)
                },
                'recomendacion': 'Validar motivo de operaciones nocturnas',
                'puntos': 10
            })
    
    # 3. Actividad concentrada en fin de semana
    df_temp['dia_semana'] = df_temp['FECHA'].dt.dayofweek
    tx_fin_semana = df_temp[df_temp['dia_semana'].isin([5, 6])]  # Sábado y Domingo
    
    if len(tx_fin_semana) > len(df_temp) * 0.4:  # Más del 40% en fin de semana
        banderas.append({
            'tipo': 'Alta Actividad en Fin de Semana',
            'severidad': 'Baja',
            'descripcion': f'{len(tx_fin_semana)} TX en sábado/domingo',
            'detalles': {
                'cantidad': len(tx_fin_semana),
                'porcentaje': (len(tx_fin_semana) / len(df_temp) * 100)
            },
            'recomendacion': 'Verificar tipo de negocio y justificación',
            'puntos': 8
        })
    
    return banderas


def _detectar_alta_tasa_rechazo(df_cliente: pd.DataFrame) -> List[Dict]:
    """Detecta alta tasa de transacciones rechazadas"""
    banderas = []
    
    if 'ESTADO' not in df_cliente.columns:
        return banderas
    
    total_tx = len(df_cliente)
    tx_rechazadas = df_cliente['ESTADO'].str.lower().str.contains('rechazado|retornado', na=False).sum()
    
    if total_tx > 0:
        tasa_rechazo = (tx_rechazadas / total_tx * 100)
        
        if tasa_rechazo >= 20:
            banderas.append({
                'tipo': 'Alta Tasa de Rechazo',
                'severidad': 'Media',
                'descripcion': f'{tasa_rechazo:.1f}% de TX rechazadas ({tx_rechazadas} de {total_tx})',
                'detalles': {
                    'tasa_rechazo': tasa_rechazo,
                    'cantidad_rechazadas': tx_rechazadas,
                    'total_tx': total_tx
                },
                'recomendacion': 'Investigar causas de rechazos frecuentes - Posibles intentos fallidos',
                'puntos': 12
            })
    
    return banderas


def _detectar_cambios_comportamiento(df_cliente: pd.DataFrame) -> List[Dict]:
    """Detecta cambios bruscos en el comportamiento transaccional"""
    banderas = []
    
    if 'FECHA' not in df_cliente.columns or 'MONTO (COP)' not in df_cliente.columns:
        return banderas
    
    df_temp = df_cliente.copy()
    df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
    df_temp = df_temp.dropna(subset=['FECHA'])
    
    if df_temp.empty or len(df_temp) < 20:  # Necesitamos suficientes datos
        return banderas
    
    # Ordenar por fecha
    df_temp = df_temp.sort_values('FECHA')
    
    # Dividir en dos mitades
    mitad = len(df_temp) // 2
    df_primera_mitad = df_temp.iloc[:mitad]
    df_segunda_mitad = df_temp.iloc[mitad:]
    
    # Comparar volúmenes
    vol_primera = df_primera_mitad['MONTO (COP)'].sum()
    vol_segunda = df_segunda_mitad['MONTO (COP)'].sum()
    
    if vol_primera > 0:
        variacion = ((vol_segunda - vol_primera) / vol_primera * 100)
        
        if abs(variacion) >= 200:  # Cambio >= 200%
            banderas.append({
                'tipo': 'Cambio Brusco en Volumen',
                'severidad': 'Alta',
                'descripcion': f'Variación de {variacion:+.1f}% en volumen transaccional',
                'detalles': {
                    'variacion_porcentual': variacion,
                    'volumen_anterior': vol_primera,
                    'volumen_reciente': vol_segunda
                },
                'recomendacion': 'Solicitar justificación de cambio en actividad',
                'puntos': 20
            })
    
    # Comparar frecuencias
    freq_primera = len(df_primera_mitad)
    freq_segunda = len(df_segunda_mitad)
    
    if freq_primera > 0:
        variacion_freq = ((freq_segunda - freq_primera) / freq_primera * 100)
        
        if abs(variacion_freq) >= 150:  # Cambio >= 150%
            banderas.append({
                'tipo': 'Cambio Brusco en Frecuencia',
                'severidad': 'Media',
                'descripcion': f'Variación de {variacion_freq:+.1f}% en frecuencia de TX',
                'detalles': {
                    'variacion_porcentual': variacion_freq,
                    'tx_anterior': freq_primera,
                    'tx_reciente': freq_segunda
                },
                'recomendacion': 'Verificar cambios en operación del negocio',
                'puntos': 15
            })
    
    return banderas


def _detectar_transacciones_riesgosas(df_cliente: pd.DataFrame) -> List[Dict]:
    """Detecta transacciones potencialmente riesgosas por características"""
    banderas = []
    
    # Placeholder - aquí podrías agregar lógica específica
    # Por ejemplo, si tuvieras columna de país destino, jurisdicciones de alto riesgo, etc.
    
    return banderas


def _detectar_inconsistencias(df_cliente: pd.DataFrame) -> List[Dict]:
    """Detecta inconsistencias en los datos transaccionales"""
    banderas = []
    
    # Verificar montos en cero o negativos
    if 'MONTO (COP)' in df_cliente.columns:
        montos_invalidos = df_cliente[df_cliente['MONTO (COP)'] <= 0]
        
        if not montos_invalidos.empty:
            banderas.append({
                'tipo': 'Datos Inconsistentes',
                'severidad': 'Baja',
                'descripcion': f'{len(montos_invalidos)} TX con montos <= 0',
                'detalles': {
                    'cantidad': len(montos_invalidos)
                },
                'recomendacion': 'Revisar calidad de datos',
                'puntos': 5
            })
    
    return banderas


def calcular_score_riesgo(evaluacion: Dict) -> int:
    """
    Calcula score de riesgo basado en evaluación de banderas
    
    Args:
        evaluacion: Dict con resultado de evaluar_banderas_riesgo
        
    Returns:
        Score de 0-100
    """
    return evaluacion.get('score_riesgo', 0)


def calcular_score_riesgo_interno(banderas: List[Dict]) -> int:
    """Calcula score interno sumando puntos de banderas"""
    total_puntos = sum(b.get('puntos', 0) for b in banderas)
    return min(total_puntos, 100)


def generar_reporte_banderas(df_completo: pd.DataFrame, clientes: List[str]) -> pd.DataFrame:
    """
    Genera reporte consolidado de banderas de riesgo
    
    Args:
        df_completo: DataFrame con todas las transacciones
        clientes: Lista de clientes
        
    Returns:
        DataFrame con resumen de banderas por cliente
    """
    reportes = []
    
    for cliente in clientes:
        df_cliente = df_completo[df_completo['CLIENTE'] == cliente]
        evaluacion = evaluar_banderas_riesgo(df_cliente)
        
        reportes.append({
            'Cliente': cliente,
            'Total_Banderas': evaluacion['total_banderas'],
            'Nivel_Alerta': evaluacion['nivel_alerta'],
            'Score_Riesgo': evaluacion['score_riesgo'],
            'Requiere_UIAF': 'Sí' if evaluacion['requiere_reporte_uiaf'] else 'No',
            'Requiere_Investigacion': 'Sí' if evaluacion['requiere_investigacion'] else 'No',
            'Banderas_Criticas': sum(1 for b in evaluacion['banderas'] if b.get('severidad') == 'Alta')
        })
    
    df_reporte = pd.DataFrame(reportes)
    df_reporte = df_reporte.sort_values('Score_Riesgo', ascending=False)
    
    return df_reporte


def priorizar_clientes_investigacion(df_reporte: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """
    Prioriza clientes que requieren investigación inmediata
    
    Args:
        df_reporte: DataFrame con reporte de banderas
        top_n: Número de clientes a priorizar
        
    Returns:
        DataFrame con clientes priorizados
    """
    # Filtrar solo clientes que requieren investigación
    df_prioritarios = df_reporte[df_reporte['Requiere_Investigacion'] == 'Sí'].copy()
    
    # Ordenar por score y banderas críticas
    df_prioritarios = df_prioritarios.sort_values(
        ['Banderas_Criticas', 'Score_Riesgo'],
        ascending=[False, False]
    ).head(top_n)
    
    return df_prioritarios
