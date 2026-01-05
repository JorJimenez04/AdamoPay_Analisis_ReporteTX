"""
Caracterización base de clientes según metodología GAFI
Implementa caracterización inicial basada en tres pilares:
- Riesgo inherente
- Perfil transaccional
- Materialidad financiera

📌 CONTRATO:
- Recibe: pandas.DataFrame (df_cliente)
- Devuelve: dict estructurado
- NO usa Streamlit
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from datetime import datetime


def caracterizar_cliente_gafi(df_cliente: pd.DataFrame) -> Dict[str, Any]:
    """
    Caracterización completa basada en enfoque GAFI (riesgo, comportamiento, materialidad)
    OPTIMIZADO: Calcula métricas una sola vez y las reutiliza
    
    Args:
        df_cliente: DataFrame con transacciones del cliente
        
    Returns:
        Dict con estructura:
        {
            "nivel_riesgo_inicial": str,
            "score_riesgo": int,
            "perfil_transaccional": dict,
            "banderas_riesgo": list,
            "metricas_consolidadas": dict,
            "timestamp_analisis": str
        }
    
    Ejemplo de uso:
        >>> df = cargar_datos_cliente("Cliente A")
        >>> resultado = caracterizar_cliente_gafi(df)
        >>> print(resultado['nivel_riesgo_inicial'])
        'Medio'
    """
    
    # Validar entrada
    if df_cliente is None or df_cliente.empty:
        return _crear_respuesta_vacia()
    
    # ====== CÁLCULOS BASE (UNA SOLA VEZ) ======
    total_tx = len(df_cliente)
    
    # Manejo seguro de fechas
    dias_activo = 0
    fecha_primera_tx = None
    fecha_ultima_tx = None
    frecuencia_diaria = 0
    
    if 'FECHA' in df_cliente.columns:
        df_temp = df_cliente.copy()
        df_temp['FECHA'] = pd.to_datetime(df_temp['FECHA'], errors='coerce')
        fechas_validas = df_temp['FECHA'].dropna()
        if len(fechas_validas) > 0:
            fecha_primera_tx = fechas_validas.min()
            fecha_ultima_tx = fechas_validas.max()
            dias_activo = (fecha_ultima_tx - fecha_primera_tx).days
            if dias_activo > 0:
                frecuencia_diaria = total_tx / dias_activo
    
    # Manejo seguro de montos
    monto_total = 0.0
    monto_promedio = 0.0
    monto_mediana = 0.0
    monto_min = 0.0
    monto_max = 0.0
    desviacion_std = 0.0
    
    if 'MONTO (COP)' in df_cliente.columns:
        montos = df_cliente['MONTO (COP)'].dropna()
        if len(montos) > 0:
            monto_total = float(montos.sum())
            monto_promedio = float(montos.mean())
            monto_mediana = float(montos.median())
            monto_min = float(montos.min())
            monto_max = float(montos.max())
            desviacion_std = float(montos.std()) if len(montos) > 1 else 0.0
    
    # Distribuciones (UNA SOLA VEZ)
    tipos_tx = {}
    if 'TIPO DE TRA' in df_cliente.columns:
        tipos_tx = df_cliente['TIPO DE TRA'].value_counts().to_dict()
        tipos_tx = {str(k): int(v) for k, v in tipos_tx.items()}
    
    estados_tx = {}
    tasa_rechazo = 0.0
    tx_exitosas = 0
    if 'ESTADO' in df_cliente.columns:
        estados_tx = df_cliente['ESTADO'].value_counts().to_dict()
        estados_tx = {str(k): int(v) for k, v in estados_tx.items()}
        rechazos = df_cliente['ESTADO'].str.lower().str.contains('rechaz|retor', na=False).sum()
        tasa_rechazo = (rechazos / total_tx * 100) if total_tx > 0 else 0.0
        tx_exitosas = df_cliente['ESTADO'].str.lower().str.contains('pagado|validado', na=False).sum()
    
    tipos_persona = {}
    if 'TIPO_PERSONA' in df_cliente.columns:
        tipos_persona = df_cliente['TIPO_PERSONA'].value_counts().to_dict()
        tipos_persona = {str(k): int(v) for k, v in tipos_persona.items()}
    
    # ====== MÉTRICAS CONSOLIDADAS (REUTILIZABLES) ======
    metricas = {
        'total_transacciones': int(total_tx),
        'tx_exitosas': int(tx_exitosas),
        'dias_activo': int(dias_activo),
        'fecha_primera_tx': fecha_primera_tx.isoformat() if fecha_primera_tx else None,
        'fecha_ultima_tx': fecha_ultima_tx.isoformat() if fecha_ultima_tx else None,
        'frecuencia_diaria': round(frecuencia_diaria, 2),
        'monto_total': monto_total,
        'monto_promedio': monto_promedio,
        'monto_mediana': monto_mediana,
        'monto_minimo': monto_min,
        'monto_maximo': monto_max,
        'desviacion_std': desviacion_std,
        'tasa_rechazo': round(tasa_rechazo, 2),
        'diversidad_tipos': len(tipos_tx)
    }
    
    # ====== SCORE DE RIESGO (REUTILIZA MÉTRICAS) ======
    score = _calcular_score_riesgo_optimizado(metricas)
    
    # ====== BANDERAS DE RIESGO (REUTILIZA MÉTRICAS) ======
    banderas = _detectar_banderas_optimizado(metricas)
    
    # ====== NIVEL DE RIESGO ======
    if score >= 70:
        nivel_riesgo = "Alto"
    elif score >= 40:
        nivel_riesgo = "Medio"
    else:
        nivel_riesgo = "Bajo"
    
    # ====== PERFIL TRANSACCIONAL ======
    perfil = {
        "actividad": {
            "total_transacciones": int(total_tx),
            "tx_exitosas": int(tx_exitosas),
            "dias_activo": int(dias_activo),
            "fecha_primera": fecha_primera_tx.strftime('%Y-%m-%d') if fecha_primera_tx else 'N/A',
            "fecha_ultima": fecha_ultima_tx.strftime('%Y-%m-%d') if fecha_ultima_tx else 'N/A',
            "frecuencia_diaria": round(frecuencia_diaria, 2)
        },
        "materialidad": {
            "monto_total": monto_total,
            "monto_promedio": monto_promedio,
            "monto_mediana": monto_mediana,
            "monto_minimo": monto_min,
            "monto_maximo": monto_max,
            "desviacion_estandar": desviacion_std,
            "coeficiente_variacion": round(desviacion_std / monto_promedio * 100, 2) if monto_promedio > 0 else 0,
            "rango_montos": monto_max - monto_min
        },
        "comportamiento": {
            "tipos_transaccion": tipos_tx,
            "estados": estados_tx,
            "tipo_persona": tipos_persona,
            "tasa_rechazo": round(tasa_rechazo, 2),
            "diversidad_tipos": len(tipos_tx)
        }
    }
    
    return {
        "nivel_riesgo_inicial": nivel_riesgo,
        "score_riesgo": score,
        "perfil_transaccional": perfil,
        "banderas_riesgo": banderas,
        "metricas_consolidadas": metricas,
        "timestamp_analisis": datetime.now().isoformat(),
        "tiene_datos": True,
        "mensaje": "Caracterización completada exitosamente"
    }


def _calcular_score_riesgo_optimizado(metricas: Dict) -> int:
    """
    Calcula score de riesgo reutilizando métricas ya calculadas
    
    Args:
        metricas: Dict con métricas consolidadas
        
    Returns:
        int: Score de 0-100
    """
    score = 0
    
    # Factor 1: Volumen (0-25 puntos)
    if metricas['monto_total'] > 500_000_000:  # > $500M
        score += 25
    elif metricas['monto_total'] > 100_000_000:  # > $100M
        score += 15
    elif metricas['monto_total'] > 10_000_000:  # > $10M
        score += 5
    
    # Factor 2: Frecuencia (0-20 puntos)
    if metricas['frecuencia_diaria'] > 20:
        score += 20
    elif metricas['frecuencia_diaria'] > 10:
        score += 12
    elif metricas['frecuencia_diaria'] > 5:
        score += 5
    
    # Factor 3: Ticket promedio (0-20 puntos)
    if metricas['monto_promedio'] > 20_000_000:  # > $20M
        score += 20
    elif metricas['monto_promedio'] > 5_000_000:  # > $5M
        score += 12
    elif metricas['monto_promedio'] > 1_000_000:  # > $1M
        score += 5
    
    # Factor 4: Diversidad (0-15 puntos)
    if metricas['diversidad_tipos'] >= 4:
        score += 15
    elif metricas['diversidad_tipos'] >= 3:
        score += 10
    elif metricas['diversidad_tipos'] >= 2:
        score += 5
    
    # Factor 5: Tasa de rechazo (0-20 puntos)
    if metricas['tasa_rechazo'] > 15:
        score += 20
    elif metricas['tasa_rechazo'] > 10:
        score += 12
    elif metricas['tasa_rechazo'] > 5:
        score += 5
    
    return min(score, 100)


def _detectar_banderas_optimizado(metricas: Dict) -> list:
    """
    Detecta banderas de riesgo reutilizando métricas ya calculadas
    
    Args:
        metricas: Dict con métricas consolidadas
        
    Returns:
        Lista de banderas detectadas con severidad y acciones
    """
    banderas = []
    
    # Bandera 1: Volumen alto
    if metricas['monto_total'] > 500_000_000:
        banderas.append({
            'tipo': 'Volumen Alto',
            'severidad': 'Alta',
            'descripcion': f'Volumen total de ${metricas["monto_total"]:,.0f} supera umbral de $500M',
            'accion': 'Revisar origen de fondos y justificación de montos',
            'valor': metricas['monto_total'],
            'umbral': 500_000_000
        })
    
    # Bandera 2: Ticket promedio alto
    if metricas['monto_promedio'] > 20_000_000:
        banderas.append({
            'tipo': 'Ticket Alto',
            'severidad': 'Media',
            'descripcion': f'Promedio de ${metricas["monto_promedio"]:,.0f} por TX supera $20M',
            'accion': 'Validar justificación de montos altos recurrentes',
            'valor': metricas['monto_promedio'],
            'umbral': 20_000_000
        })
    
    # Bandera 3: Alta frecuencia
    if metricas['frecuencia_diaria'] > 20:
        banderas.append({
            'tipo': 'Frecuencia Alta',
            'severidad': 'Media',
            'descripcion': f'{metricas["frecuencia_diaria"]:.1f} TX/día supera umbral de 20',
            'accion': 'Revisar patrones de transaccionalidad y horarios',
            'valor': metricas['frecuencia_diaria'],
            'umbral': 20
        })
    
    # Bandera 4: Tasa de rechazo alta
    if metricas['tasa_rechazo'] > 15:
        banderas.append({
            'tipo': 'Rechazos Elevados',
            'severidad': 'Alta',
            'descripcion': f'Tasa de rechazo de {metricas["tasa_rechazo"]:.1f}% supera 15%',
            'accion': 'Investigar causas de rechazos y posible fragmentación',
            'valor': metricas['tasa_rechazo'],
            'umbral': 15
        })
    
    # Bandera 5: Actividad concentrada
    if metricas['dias_activo'] > 0:
        tx_por_dia = metricas['total_transacciones'] / metricas['dias_activo']
        if tx_por_dia > 50:
            banderas.append({
                'tipo': 'Actividad Concentrada',
                'severidad': 'Media',
                'descripcion': 'Actividad transaccional muy concentrada en pocos días',
                'accion': 'Verificar justificación de concentración temporal',
                'valor': tx_por_dia,
                'umbral': 50
            })
    
    # Bandera 6: Alta diversidad de tipos
    if metricas['diversidad_tipos'] >= 4:
        banderas.append({
            'tipo': 'Diversidad de Operaciones',
            'severidad': 'Baja',
            'descripcion': f'{metricas["diversidad_tipos"]} tipos diferentes de transacciones',
            'accion': 'Monitorear coherencia con actividad económica declarada',
            'valor': metricas['diversidad_tipos'],
            'umbral': 4
        })
    
    return banderas


def _crear_respuesta_vacia() -> Dict[str, Any]:
    """
    Respuesta segura cuando no hay datos para caracterizar
    
    Returns:
        Dict con estructura completa pero valores vacíos/cero
    """
    return {
        "nivel_riesgo_inicial": "No Evaluado",
        "score_riesgo": 0,
        "perfil_transaccional": {
            "actividad": {
                "total_transacciones": 0,
                "tx_exitosas": 0,
                "dias_activo": 0,
                "fecha_primera": "N/A",
                "fecha_ultima": "N/A",
                "frecuencia_diaria": 0
            },
            "materialidad": {
                "monto_total": 0,
                "monto_promedio": 0,
                "monto_mediana": 0,
                "monto_minimo": 0,
                "monto_maximo": 0,
                "desviacion_estandar": 0,
                "coeficiente_variacion": 0,
                "rango_montos": 0
            },
            "comportamiento": {
                "tipos_transaccion": {},
                "estados": {},
                "tipo_persona": {},
                "tasa_rechazo": 0,
                "diversidad_tipos": 0
            }
        },
        "banderas_riesgo": [],
        "metricas_consolidadas": {},
        "timestamp_analisis": datetime.now().isoformat(),
        "tiene_datos": False,
        "mensaje": "Sin datos para caracterizar"
    }


def caracterizar_cartera_clientes(df_completo: pd.DataFrame, lista_clientes: list) -> Dict[str, Any]:
    """
    Caracteriza toda la cartera de clientes
    
    Args:
        df_completo: DataFrame con todas las transacciones
        lista_clientes: Lista de nombres de clientes
        
    Returns:
        Dict con caracterización consolidada de la cartera
    """
    if df_completo is None or df_completo.empty or not lista_clientes:
        return {
            "total_clientes": 0,
            "caracterizaciones": [],
            "resumen_riesgos": {},
            "mensaje": "Sin datos para caracterizar"
        }
    
    caracterizaciones = []
    resumen_riesgos = {
        "Alto": 0,
        "Medio": 0,
        "Bajo": 0,
        "No Evaluado": 0
    }
    
    for cliente in lista_clientes:
        df_cliente = df_completo[df_completo['CLIENTE'] == cliente]
        resultado = caracterizar_cliente_gafi(df_cliente)
        
        caracterizaciones.append({
            "cliente": cliente,
            "nivel_riesgo": resultado['nivel_riesgo_inicial'],
            "total_transacciones": resultado['metricas_consolidadas'].get('total_transacciones', 0),
            "volumen_total": resultado['metricas_consolidadas'].get('volumen_total', 0),
            "cantidad_banderas": resultado['metricas_consolidadas'].get('cantidad_banderas', 0)
        })
        
        # Actualizar resumen de riesgos
        nivel = resultado['nivel_riesgo_inicial']
        if nivel in resumen_riesgos:
            resumen_riesgos[nivel] += 1
    
    # Ordenar por nivel de riesgo y volumen
    orden_riesgo = {"Alto": 3, "Medio": 2, "Bajo": 1, "No Evaluado": 0}
    caracterizaciones.sort(
        key=lambda x: (orden_riesgo.get(x['nivel_riesgo'], 0), x['volumen_total']),
        reverse=True
    )
    
    return {
        "total_clientes": len(lista_clientes),
        "caracterizaciones": caracterizaciones,
        "resumen_riesgos": resumen_riesgos,
        "clientes_alto_riesgo": [c['cliente'] for c in caracterizaciones if c['nivel_riesgo'] == 'Alto'],
        "mensaje": "Caracterización de cartera completada"
    }


def obtener_resumen_caracterizacion(resultado_caracterizacion: Dict) -> str:
    """
    Genera un resumen textual de la caracterización
    
    Args:
        resultado_caracterizacion: Dict retornado por caracterizar_cliente_gafi()
        
    Returns:
        str: Resumen en texto plano
    """
    if not resultado_caracterizacion.get('tiene_datos', False):
        return "Sin datos disponibles para generar resumen"
    
    nivel = resultado_caracterizacion['nivel_riesgo_inicial']
    metricas = resultado_caracterizacion['metricas_consolidadas']
    banderas = resultado_caracterizacion['banderas_riesgo']
    
    resumen = f"""
RESUMEN DE CARACTERIZACIÓN GAFI
================================

Nivel de Riesgo Inicial: {nivel}

Actividad Transaccional:
- Total de Transacciones: {metricas['total_transacciones']:,}
- Volumen Total: ${metricas['volumen_total']:,.0f}
- Ticket Promedio: ${metricas['ticket_promedio']:,.0f}
- Días de Operación: {metricas['dias_operacion']}
- Frecuencia: {metricas['frecuencia_operacional']:.2f} TX/día

Banderas de Riesgo Detectadas: {len(banderas)}
"""
    
    if banderas:
        resumen += "\n\nBanderas:\n"
        for i, bandera in enumerate(banderas, 1):
            resumen += f"{i}. [{bandera['severidad']}] {bandera['tipo']}\n"
            resumen += f"   {bandera['descripcion']}\n"
    
    return resumen.strip()
