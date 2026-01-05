# AdamoPay - Sistema de Análisis y Reporte Transaccional

Sistema avanzado de análisis de riesgo transaccional con caracterización GAFI, scoring multicapa y alertas automatizadas.

## 🚀 Características Principales

- **Caracterización GAFI**: Análisis de perfil de riesgo basado en estándares GAFI
- **Scoring Multicapa**: Sistema de puntuación ponderado (GAFI 40% + UIAF 35% + Operativo 25%)
- **Alertas Automáticas**: Detección de 6 tipos de alertas con 4 niveles de prioridad
- **Matriz de Riesgo**: Análisis inherente vs residual con identificación de gaps de control
- **Dashboard Interactivo**: Visualización en tiempo real con Streamlit
- **Reportes Ejecutivos**: Generación automática de reportes individuales y de cartera

## 📁 Estructura del Proyecto

```
AdamoPay_Analisis_ReporteTX/
├── app.py                  # 🎯 Aplicación Streamlit (Principal)
├── config/
│   └── settings.py         # Configuración general
├── data/
│   └── Data_Clients&TX.xlsx  # Datos de clientes y transacciones
├── src/
│   ├── characterization/   # 🧭 Módulo de Caracterización GAFI
│   │   ├── base_characterization.py
│   │   ├── gafi_profile.py
│   │   ├── behavior_metrics.py
│   │   ├── risk_flags.py
│   │   └── contracts.py
│   └── risk_analysis/      # 🎯 Módulo de Análisis de Riesgo Integral
│       ├── risk_engine.py          # Motor principal
│       ├── risk_scoring.py         # Sistema de scoring
│       ├── risk_alerts.py          # Generación de alertas
│       ├── risk_reports.py         # Reportes ejecutivos
│       ├── risk_contracts.py       # Contratos TypedDict
│       └── test_risk_module.py     # Tests del módulo
├── assets/                 # Logos e imágenes
│   ├── LogoAdamoServices.png
│   └── Adamopay.png
└── requirements.txt        # Dependencias Python
```

## 📦 Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone <repository-url>
   cd AdamoPay_Analisis_ReporteTX
   ```

2. **Crear entorno virtual**:
   ```bash
   python -m venv .venv
   ```

3. **Activar entorno virtual**:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

4. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Uso

### Ejecutar aplicación Streamlit:
```bash
streamlit run app.py
```

### Ejecutar tests del módulo de riesgo:
```bash
python src/risk_analysis/test_risk_module.py
```

## 📊 Módulos Principales

### 🧭 `characterization/` - Caracterización GAFI
- **base_characterization.py**: Orquestación principal del análisis GAFI
- **gafi_profile.py**: Clasificación de perfiles de riesgo
- **behavior_metrics.py**: Cálculo de métricas comportamentales
- **risk_flags.py**: Evaluación de banderas de riesgo
- **contracts.py**: Contratos TypedDict para validación

### 🎯 `risk_analysis/` - Análisis de Riesgo Integral
- **risk_engine.py**: Motor de análisis (inherente vs residual)
- **risk_scoring.py**: Sistema de scoring ponderado (GAFI + UIAF + Operativo)
- **risk_alerts.py**: Generación automática de alertas (6 tipos, 4 prioridades)
- **risk_reports.py**: Reportes ejecutivos individuales y de cartera
- **risk_contracts.py**: Schemas TypedDict para outputs

## ⚙️ Configuración

Ver `config/settings.py` para ajustar:
- Rutas de datos y archivos
- Umbrales de riesgo (volumen, frecuencia, etc.)
- Pesos del scoring multicapa
- Configuraciones de análisis

## 📈 Métricas y Scoring

### Score Total (0-100)
- **GAFI**: 40% (volumen, frecuencia, diversidad)
- **UIAF**: 35% (fragmentación, rechazo, inconsistencias)
- **Operativo**: 25% (errores, complejidad, volatilidad)

### Niveles de Riesgo
- **Bajo**: 0-30 puntos (Review trimestral)
- **Medio**: 31-50 puntos (Review mensual)
- **Alto**: 51-75 puntos (Review quincenal + DDR)
- **Crítico**: 76-100 puntos (Review semanal + Suspensión)

## 🚨 Sistema de Alertas

### Tipos de Alertas
- 📋 **UIAF**: Cumplimiento normativo
- 🚨 **Fraude**: Detección de patrones sospechosos
- ⚙️ **Operacional**: Riesgos operativos
- 📜 **Compliance**: Incumplimientos regulatorios
- 👁️ **Reputacional**: Riesgos de imagen

### Prioridades
- 🔥 **Crítica**: 1-2 días para acción
- 🚨 **Alta**: 3-7 días para acción
- ⚠️ **Media**: 8-15 días para acción
- ℹ️ **Baja**: 16-30 días para acción

## 📄 Licencia

© 2026 AdamoPay - Sistema de Análisis y Reporte Transaccional

## Contribución

Proyecto interno de AdamoPay.

## Licencia

Propietario - AdamoPay
