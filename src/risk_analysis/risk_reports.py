"""
Generación de reportes de riesgo
Crea reportes ejecutivos y matrices de riesgo
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List
from .risk_contracts import AnalisisRiesgo, ResumenEjecutivo, MatrizRiesgo


def generar_reporte_riesgo(analisis: AnalisisRiesgo) -> str:
    """
    Genera reporte textual de análisis de riesgo
    
    Args:
        analisis: AnalisisRiesgo completo
    
    Returns:
        str: Reporte en formato texto
    """
    scoring = analisis['scoring']
    alertas = analisis['alertas']
    
    reporte = f"""
╔═══════════════════════════════════════════════════════════════════╗
║           REPORTE DE ANÁLISIS DE RIESGO TRANSACCIONAL            ║
╚═══════════════════════════════════════════════════════════════════╝

INFORMACIÓN DEL CLIENTE
-----------------------
Cliente: {analisis['cliente']}
Fecha de Análisis: {analisis['timestamp_analisis']}
Próxima Revisión: {analisis['proximo_review']}

EVALUACIÓN DE RIESGO
-------------------
🎯 Nivel de Riesgo: {scoring['nivel_riesgo']}
📊 Score Total: {scoring['score_total']}/100

Desglose de Scores:
  • GAFI:       {scoring['score_gafi']}/100 (40%)
  • UIAF:       {scoring['score_uiaf']}/100 (35%)
  • Operativo:  {scoring['score_operativo']}/100 (25%)

Factores Críticos:
"""
    
    if scoring['factores_criticos']:
        for factor in scoring['factores_criticos']:
            reporte += f"  ⚠️ {factor}\n"
    else:
        reporte += "  ✅ No se detectaron factores críticos\n"
    
    reporte += f"\nALERTAS DETECTADAS\n------------------\n"
    reporte += f"Total de Alertas: {len(alertas)}\n\n"
    
    if alertas:
        for i, alerta in enumerate(alertas[:5], 1):  # Top 5 alertas
            reporte += f"{i}. [{alerta['prioridad']}] {alerta['titulo']}\n"
            reporte += f"   Tipo: {alerta['tipo']}\n"
            reporte += f"   {alerta['descripcion']}\n"
            reporte += f"   Acción: {alerta['accion_requerida']}\n"
            if alerta['requiere_reporte_uiaf']:
                reporte += f"   ⚠️ REQUIERE REPORTE UIAF\n"
            reporte += f"\n"
    else:
        reporte += "✅ No se detectaron alertas\n\n"
    
    reporte += f"ACCIONES REQUERIDAS\n-------------------\n"
    if analisis['requiere_due_diligence_reforzada']:
        reporte += "🔴 Due Diligence Reforzada (DDR) REQUERIDA\n"
    if analisis['requiere_escalamiento']:
        reporte += "🔴 Escalamiento a Oficial de Cumplimiento REQUERIDO\n"
    
    reporte += f"\nRECOMENDACIONES\n---------------\n"
    for rec in analisis['recomendaciones']:
        reporte += f"• {rec}\n"
    
    reporte += f"\n{'='*70}\n"
    reporte += f"Reporte generado automáticamente por Sistema de Análisis de Riesgo\n"
    
    return reporte


def exportar_matriz_riesgo(matriz: MatrizRiesgo) -> pd.DataFrame:
    """
    Exporta matriz de riesgo a DataFrame
    
    Args:
        matriz: MatrizRiesgo dict
    
    Returns:
        DataFrame con matriz estructurada
    """
    # Crear DataFrame con riesgo inherente vs residual
    categorias = list(matriz['riesgo_inherente'].keys())
    
    df_matriz = pd.DataFrame({
        'Categoría': categorias,
        'Riesgo Inherente': [matriz['riesgo_inherente'][cat] for cat in categorias],
        'Riesgo Residual': [matriz['riesgo_residual'][cat] for cat in categorias],
        'Reducción (%)': [
            round((1 - matriz['riesgo_residual'][cat] / matriz['riesgo_inherente'][cat]) * 100, 1)
            if matriz['riesgo_inherente'][cat] > 0 else 0
            for cat in categorias
        ]
    })
    
    return df_matriz


def crear_resumen_ejecutivo(
    analisis_cartera: Dict[str, AnalisisRiesgo]
) -> ResumenEjecutivo:
    """
    Crea resumen ejecutivo de toda la cartera
    
    Args:
        analisis_cartera: Dict con análisis por cliente
    
    Returns:
        ResumenEjecutivo
    """
    total_clientes = len(analisis_cartera)
    
    # Contar clientes por nivel de riesgo
    clientes_por_nivel = {
        'Crítico': 0,
        'Alto': 0,
        'Medio': 0,
        'Bajo': 0,
        'No Evaluado': 0
    }
    
    alertas_criticas = 0
    alertas_pendientes = 0
    reportes_uiaf = 0
    
    for cliente, analisis in analisis_cartera.items():
        nivel = analisis['scoring']['nivel_riesgo']
        clientes_por_nivel[nivel] = clientes_por_nivel.get(nivel, 0) + 1
        
        # Contar alertas críticas
        alertas_criticas += len([a for a in analisis['alertas'] if a['prioridad'] == 'Crítica'])
        alertas_pendientes += len(analisis['alertas'])
        
        # Contar reportes UIAF requeridos
        if any(a['requiere_reporte_uiaf'] for a in analisis['alertas']):
            reportes_uiaf += 1
    
    # Identificar top riesgos
    top_riesgos = sorted(
        [
            {
                'cliente': cliente,
                'score': analisis['scoring']['score_total'],
                'nivel': analisis['scoring']['nivel_riesgo'],
                'alertas': len(analisis['alertas'])
            }
            for cliente, analisis in analisis_cartera.items()
        ],
        key=lambda x: x['score'],
        reverse=True
    )[:10]  # Top 10
    
    # Generar recomendaciones estratégicas
    recomendaciones_estrategicas = []
    
    if clientes_por_nivel['Crítico'] > 0:
        recomendaciones_estrategicas.append(
            f"🚨 URGENTE: {clientes_por_nivel['Crítico']} cliente(s) en nivel CRÍTICO requieren acción inmediata"
        )
    
    if reportes_uiaf > 0:
        recomendaciones_estrategicas.append(
            f"📋 {reportes_uiaf} cliente(s) requieren reporte a UIAF"
        )
    
    if clientes_por_nivel['Alto'] > 5:
        recomendaciones_estrategicas.append(
            f"⚠️ Concentración de riesgo: {clientes_por_nivel['Alto']} clientes en nivel ALTO"
        )
    
    tasa_critico_alto = (clientes_por_nivel['Crítico'] + clientes_por_nivel['Alto']) / total_clientes * 100
    if tasa_critico_alto > 20:
        recomendaciones_estrategicas.append(
            f"📊 {tasa_critico_alto:.1f}% de cartera en riesgo Alto/Crítico supera apetito de riesgo"
        )
    
    if not recomendaciones_estrategicas:
        recomendaciones_estrategicas.append("✅ Cartera dentro de parámetros normales de riesgo")
    
    return {
        'total_clientes': total_clientes,
        'clientes_por_nivel': clientes_por_nivel,
        'alertas_criticas': alertas_criticas,
        'alertas_pendientes': alertas_pendientes,
        'reportes_uiaf_requeridos': reportes_uiaf,
        'top_riesgos': top_riesgos,
        'recomendaciones_estrategicas': recomendaciones_estrategicas,
        'timestamp': datetime.now().isoformat()
    }


def generar_reporte_ejecutivo_texto(resumen: ResumenEjecutivo) -> str:
    """
    Genera reporte ejecutivo en formato texto
    
    Args:
        resumen: ResumenEjecutivo
    
    Returns:
        str: Reporte ejecutivo
    """
    reporte = f"""
╔═══════════════════════════════════════════════════════════════════╗
║                RESUMEN EJECUTIVO - ANÁLISIS DE CARTERA           ║
╚═══════════════════════════════════════════════════════════════════╝

INDICADORES CLAVE
-----------------
📊 Total de Clientes: {resumen['total_clientes']:,}
🚨 Alertas Críticas: {resumen['alertas_criticas']}
⏳ Alertas Pendientes: {resumen['alertas_pendientes']}
📋 Reportes UIAF Requeridos: {resumen['reportes_uiaf_requeridos']}

DISTRIBUCIÓN DE RIESGO
----------------------
🔴 Crítico:      {resumen['clientes_por_nivel']['Crítico']:3d} clientes ({resumen['clientes_por_nivel']['Crítico']/resumen['total_clientes']*100:5.1f}%)
🟠 Alto:         {resumen['clientes_por_nivel']['Alto']:3d} clientes ({resumen['clientes_por_nivel']['Alto']/resumen['total_clientes']*100:5.1f}%)
🟡 Medio:        {resumen['clientes_por_nivel']['Medio']:3d} clientes ({resumen['clientes_por_nivel']['Medio']/resumen['total_clientes']*100:5.1f}%)
🟢 Bajo:         {resumen['clientes_por_nivel']['Bajo']:3d} clientes ({resumen['clientes_por_nivel']['Bajo']/resumen['total_clientes']*100:5.1f}%)

TOP 10 CLIENTES DE MAYOR RIESGO
--------------------------------
"""
    
    for i, cliente_info in enumerate(resumen['top_riesgos'][:10], 1):
        emoji = {'Crítico': '🔴', 'Alto': '🟠', 'Medio': '🟡', 'Bajo': '🟢'}.get(cliente_info['nivel'], '⚪')
        reporte += f"{i:2d}. {emoji} {cliente_info['cliente']:30s} | Score: {cliente_info['score']:3d} | Alertas: {cliente_info['alertas']}\n"
    
    reporte += f"\nRECOMENDACIONES ESTRATÉGICAS\n----------------------------\n"
    for rec in resumen['recomendaciones_estrategicas']:
        reporte += f"• {rec}\n"
    
    reporte += f"\n{'='*70}\n"
    reporte += f"Generado: {resumen['timestamp']}\n"
    
    return reporte
