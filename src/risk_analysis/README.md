# Módulo de Análisis de Riesgo Transaccional

Módulo independiente para análisis integral de riesgo basado en scoring multicapa, alertas automatizadas y reportes ejecutivos.

## 📁 Estructura

```
src/risk_analysis/
├── __init__.py              # Punto de entrada del módulo
├── risk_contracts.py        # TypedDict schemas y validadores
├── risk_engine.py           # Motor principal de análisis
├── risk_scoring.py          # Sistema de scoring (GAFI, UIAF, Operativo)
├── risk_alerts.py           # Generación y priorización de alertas
├── risk_reports.py          # Reportes ejecutivos y matrices
└── test_risk_module.py      # Tests del módulo
```

## 🎯 Características Principales

### 1. **Scoring Multicapa**
- **Score GAFI**: Basado en perfil de caracterización (40%)
- **Score UIAF**: Señales de alerta según Circular 55/2016 (35%)
- **Score Operativo**: Errores, complejidad, volatilidad (25%)
- **Score Total**: 0-100 con clasificación automática

### 2. **Clasificación de Riesgo**
- **Bajo**: 0-30 puntos
- **Medio**: 31-50 puntos
- **Alto**: 51-75 puntos
- **Crítico**: 76-100 puntos

### 3. **Sistema de Alertas**
- Detección automática de patrones sospechosos
- Priorización por criticidad (Crítica > Alta > Media > Baja)
- Clasificación por tipo: UIAF, Operacional, Compliance, Fraude, Reputacional
- Acciones recomendadas y plazos de respuesta

### 4. **Matriz de Riesgo**
- Riesgo inherente vs residual
- Evaluación de efectividad de controles
- Identificación de gaps de control
- Apetito de riesgo

### 5. **Reportes Ejecutivos**
- Reporte individual por cliente
- Resumen consolidado de cartera
- Top 10 clientes de mayor riesgo
- Recomendaciones estratégicas

## 🚀 Uso Básico

```python
from src.risk_analysis import (
    analizar_riesgo_cliente,
    generar_reporte_riesgo,
    crear_resumen_ejecutivo
)

# Análisis individual
resultado = analizar_riesgo_cliente(
    df_cliente=df,
    perfil_gafi=perfil,  # Opcional
    cliente_nombre="Cliente A"
)

print(f"Nivel de Riesgo: {resultado['scoring']['nivel_riesgo']}")
print(f"Score: {resultado['scoring']['score_total']}/100")
print(f"Alertas: {len(resultado['alertas'])}")

# Generar reporte
reporte = generar_reporte_riesgo(resultado)
print(reporte)

# Análisis de cartera
from src.risk_analysis import analizar_riesgo_cartera

analisis_cartera = analizar_riesgo_cartera(df_completo, lista_clientes)
resumen = crear_resumen_ejecutivo(analisis_cartera)
```

## 📊 Estructura de Datos

### AnalisisRiesgo
```python
{
    'cliente': str,
    'timestamp_analisis': str,
    'scoring': ScoreRiesgo,
    'alertas': List[AlertaRiesgo],
    'matriz_riesgo': MatrizRiesgo,
    'recomendaciones': List[str],
    'requiere_due_diligence_reforzada': bool,
    'requiere_escalamiento': bool,
    'proximo_review': str
}
```

### ScoreRiesgo
```python
{
    'score_total': int,  # 0-100
    'score_gafi': int,
    'score_uiaf': int,
    'score_operativo': int,
    'nivel_riesgo': Literal['Bajo', 'Medio', 'Alto', 'Crítico'],
    'factores_criticos': List[str],
    'ponderacion': Dict[str, float]
}
```

### AlertaRiesgo
```python
{
    'id_alerta': str,
    'tipo': Literal['Operacional', 'UIAF', 'Compliance', 'Fraude', 'Reputacional'],
    'prioridad': Literal['Baja', 'Media', 'Alta', 'Crítica'],
    'titulo': str,
    'descripcion': str,
    'valor_detectado': float,
    'umbral': float,
    'accion_requerida': str,
    'fecha_deteccion': str,
    'requiere_reporte_uiaf': bool,
    'dias_para_accion': int
}
```

## 🔍 Detecciones Automáticas

### Señales UIAF
- ✅ Transacciones >$10M en efectivo
- ✅ Fragmentación (smurfing)
- ✅ Alta tasa de rechazo (>25%)
- ✅ Patrones de lavado de activos

### Riesgos Operacionales
- ✅ Volumen transaccional >1000 TX
- ✅ Alta volatilidad de montos (CV >1.5)
- ✅ Concentración temporal anómala
- ✅ Alta diversidad de tipos de TX (>6)

### Alertas Críticas
- ✅ Score total ≥76
- ✅ Volumen >$1,000M
- ✅ Detección de fragmentación
- ✅ Tasa de rechazo >25%

## 📈 Umbrales Configurados

| Categoría | Umbral | Acción |
|-----------|--------|--------|
| Volumen Total | $1,000M | Alerta Alta + UIAF |
| Ticket Promedio | $50M | Alerta Media |
| Frecuencia Diaria | 20 TX/día | Monitoreo |
| Tasa de Rechazo | 25% | Alerta Alta |
| Score Total | 76+ | Crítico + Suspensión |
| Score Total | 51-75 | Alto + DDR |
| Score Total | 31-50 | Medio + Monitoreo |

## 🔄 Calendario de Revisiones

| Nivel de Riesgo | Frecuencia de Review |
|------------------|---------------------|
| Crítico | Semanal (7 días) |
| Alto | Quincenal (15 días) |
| Medio | Mensual (30 días) |
| Bajo | Trimestral (90 días) |

## 🎯 Recomendaciones Automáticas

### Nivel Crítico
- 🚨 Suspender operaciones inmediatamente
- 📋 Reporte UIAF en 24 horas
- 👥 Escalar a Oficial de Cumplimiento

### Nivel Alto
- ⚠️ Due Diligence Reforzada (DDR)
- 📊 Revisión quincenal
- 🔍 Validar origen de fondos (72h)

### Nivel Medio
- 📌 Monitoreo mensual
- ✅ Alertas automáticas activas
- 📄 Actualizar KYC si >1 año

### Nivel Bajo
- ✅ Monitoreo estándar
- 📅 Revisión anual

## 🔧 Tests

Ejecutar tests del módulo:

```bash
cd src/risk_analysis
python test_risk_module.py
```

Resultado esperado:
```
✅ Imports exitosos
✅ Análisis completado
✅ Reporte generado
✅ Scoring calculado
✅ TODOS LOS TESTS PASARON EXITOSAMENTE
```

## 📝 Notas Importantes

1. **Independencia**: Este módulo es completamente independiente de characterization/
2. **Complementariedad**: Puede usar perfil GAFI como input pero funciona sin él
3. **Sin UI**: No usa Streamlit, solo procesamiento puro de datos
4. **Exportable**: Todos los outputs son dicts/DataFrames exportables
5. **Auditabilidad**: Timestamps y trazabilidad completa

## 🔗 Integración con characterization/

```python
# Opción 1: Análisis completo (GAFI + Risk)
from src.characterization import caracterizar_cliente_gafi
from src.risk_analysis import analizar_riesgo_cliente

perfil_gafi = caracterizar_cliente_gafi(df_cliente)
analisis_riesgo = analizar_riesgo_cliente(df_cliente, perfil_gafi)

# Opción 2: Solo análisis de riesgo (independiente)
analisis_riesgo = analizar_riesgo_cliente(df_cliente)
```

## ✅ Estado

- ✅ Módulo creado y funcional
- ✅ Tests pasando exitosamente
- ✅ Contracts definidos
- ✅ Documentación completa
- ⏳ Integración con app.py (pendiente)
- ⏳ Visualización UI (pendiente)

---

**Versión**: 1.0.0  
**Última actualización**: 2026-01-03  
**Autor**: Sistema de Análisis AdamoPay
