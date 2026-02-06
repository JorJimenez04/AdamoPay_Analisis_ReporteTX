# AdamoPay - Sistema de Análisis y Reporte Transaccional

Sistema avanzado de análisis de riesgo transaccional con caracterización GAFI, scoring multicapa, alertas automatizadas y visualización profesional de datos.

## 🚀 Características Principales

- **🎯 Sistema Híbrido de Carga de Datos** ⭐ NUEVO
  - 📤 **Subir Archivo**: Carga Excel en producción (hasta 100MB)
  - 🎯 **Datos de Ejemplo**: Demo con datos sintéticos (~470 transacciones, 3 clientes)
  - 📁 **Archivo Local**: Desarrollo sin subir archivos cada vez
- **Caracterización GAFI**: Análisis de perfil de riesgo basado en estándares GAFI
- **Scoring Multicapa**: Sistema de puntuación ponderado (GAFI 40% + UIAF 35% + Operativo 25%)
- **Alertas Automáticas**: Detección de 6 tipos de alertas con 4 niveles de prioridad
- **Matriz de Riesgo**: Análisis inherente vs residual con identificación de gaps de control
- **Dashboard Interactivo**: Visualización profesional con Streamlit y gráficas corporativas
- **Análisis Temporal**: Evolución de transacciones, días pico y patrones semanales
- **Concentración de Operaciones**: Top beneficiarios (PN/PJ) y bancos receptores
- **Análisis de Inactividad**: Beneficiarios inactivos y de baja actividad con métricas avanzadas
- **Reportes Ejecutivos**: Generación automática de reportes individuales y de cartera
- **Deployment-Ready**: Configurado para Streamlit Community Cloud (gratuito)

## 📁 Estructura del Proyecto

```
AdamoPay_Analisis_ReporteTX/
├── 📄 app.py                          # Aplicación Streamlit principal (3335+ líneas)
│                                      # ✅ Sistema híbrido de carga: Upload/Demo/Local
│                                      # ✅ Generador de datos sintéticos para demos
│                                      # ✅ Optimización de memoria y estabilidad
│
├── 📂 .streamlit/                     # Configuración de Streamlit
│   ├── config.toml                    # Configuración optimizada para producción
│   └── secrets.toml.example           # Template para secretos (passwords, API keys)
│
├── 📂 config/                         # Configuración del sistema
│   ├── settings.py                    # Configuración general (umbrales, estados)
│   └── ui_config.py                   # Configuración UI (fuentes, colores, layouts)
│
├── 📂 src/                            # Código fuente
│   ├── characterization/              # 🧭 Módulo de Caracterización GAFI
│   │   ├── base_characterization.py  # Orquestación principal
│   │   ├── gafi_profile.py           # Clasificación de perfiles de riesgo
│   │   ├── behavior_metrics.py       # Métricas comportamentales
│   │   ├── risk_flags.py             # 15+ banderas de riesgo automáticas
│   │   └── contracts.py              # Contratos TypedDict
│   │
│   └── risk_analysis/                 # 🎯 Módulo de Análisis de Riesgo
│       ├── risk_engine.py            # Motor principal (inherente vs residual)
│       ├── risk_scoring.py           # Sistema de scoring ponderado
│       ├── risk_alerts.py            # Generación de alertas (6 tipos, 4 prioridades)
│       ├── risk_reports.py           # Reportes ejecutivos
│       ├── risk_contracts.py         # Schemas TypedDict
│       └── test_risk_module.py       # Tests del módulo
│
├── 📂 data/                           # Datos (opcional en producción)
│   └── Data_Clients&TX.xlsx          # Archivo de ejemplo para desarrollo local
│
├── 📂 assets/                         # Recursos visuales
│   ├── LogoAdamoServices.png         # Logo AdamoServices
│   └── LogoAdamoPay.jpeg             # Logo AdamoPay
│
├── 📄 requirements.txt                # ✅ Dependencias Python (producción)
├── 📄 packages.txt                    # Dependencias del sistema (Linux)
├── 📄 .gitignore                      # ✅ Archivos excluidos de git
│
├── 📄 README.md                       # Este archivo
├── 📄 DEPLOYMENT_CLOUD.md            # 🆕 Guía completa de deployment (Streamlit Cloud)
├── 📄 DEPLOYMENT_CHECKLIST.md        # 🆕 Checklist interactivo de deployment
├── 📄 DEPLOYMENT_GUIDE.md            # Guía técnica de deployment
└── 📄 setup_git.ps1                  # 🆕 Script automatizado para Git setup
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

## 🎨 Dependencias Principales

```python
# Web Framework
streamlit>=1.31.0

# Análisis de datos
pandas>=2.2.0
numpy>=1.26.0

# Visualización
plotly>=5.18.0

# Procesamiento de Excel
openpyxl>=3.1.2

# Utilidades
python-dateutil>=2.8.2

# Generación de reportes (opcional)
reportlab>=4.0.0
fpdf2>=2.7.0
```

**Nota:** Las versiones usan `>=` para compatibilidad con Streamlit Cloud

## 🚀 Uso

### Desarrollo Local:

1. **Ejecutar aplicación Streamlit**:
   ```bash
   streamlit run app.py
   ```
   La aplicación se abrirá en `http://localhost:8501`

2. **Seleccionar método de carga de datos** (en el sidebar):
   
   **📤 Opción 1: Subir Archivo** (Producción)
   - Sube tu archivo Excel con datos reales
   - Límite: 100MB por archivo
   - Ideal para análisis de datos reales
   
   **🎯 Opción 2: Datos de Ejemplo** (Demo) ⭐ RECOMENDADO PARA PRUEBAS
   - Genera automáticamente datos sintéticos
   - 3 clientes ficticios (TechCorp, RetailMax, FinServ)
   - ~470 transacciones realistas con:
     - 85% transacciones efectivas
     - 70% Personas Naturales / 30% Jurídicas
     - Montos y fechas realistas
     - 8 bancos colombianos
   - Perfecto para:
     - Demos y presentaciones
     - Pruebas sin exponer datos reales
     - Entender funcionalidades
   
   **📁 Opción 3: Archivo Local** (Desarrollo)
   - Coloca `Data_Clients&TX.xlsx` en la carpeta `data/`
   - Sin necesidad de subir archivos cada vez
   - Ideal para desarrollo continuo

3. **Ejecutar tests del módulo de riesgo**:
   ```bash
   python src/risk_analysis/test_risk_module.py
   ```

### 🌐 Deployment en Producción:

Para desplegar la aplicación en **Streamlit Community Cloud (GRATIS)**:

📖 **Ver guía completa**: [DEPLOYMENT_CLOUD.md](DEPLOYMENT_CLOUD.md)

**Resumen rápido**:
1. Sube el código a GitHub
2. Conecta tu repositorio en [share.streamlit.io](https://share.streamlit.io)
3. Deploy automático en 5-10 minutos
4. **Características gratuitas**: 1GB RAM, SSL/HTTPS, ~10-50 usuarios concurrentes

**Archivos de configuración incluidos**:
- ✅ `requirements.txt` - Dependencias
- ✅ `.streamlit/config.toml` - Configuración
- ✅ `.gitignore` - Exclusiones git
- ✅ `.streamlit/secrets.toml.example` - Template de secretos

## 📊 Módulos Principales

### 🧭 `characterization/` - Caracterización GAFI
- **base_characterization.py**: Orquestación principal del análisis GAFI
- **gafi_profile.py**: Clasificación de perfiles de riesgo (Bajo/Medio/Alto/Crítico)
- **behavior_metrics.py**: Cálculo de métricas comportamentales (velocidad, diversidad, patrones)
- **risk_flags.py**: Evaluación de 15+ banderas de riesgo automáticas
- **contracts.py**: Contratos TypedDict para validación de datos

### 🎯 `risk_analysis/` - Análisis de Riesgo Integral
- **risk_engine.py**: Motor de análisis (riesgo inherente vs residual)
- **risk_scoring.py**: Sistema de scoring ponderado multinivel
- **risk_alerts.py**: Generación automática de alertas (6 tipos, 4 prioridades)
- **risk_reports.py**: Reportes ejecutivos individuales y consolidados de cartera
- **risk_contracts.py**: Schemas TypedDict para outputs estructurados

### 🎨 `config/` - Configuración
- **settings.py**: Configuración de negocio (umbrales, estados, tipos de persona)
- **ui_config.py**: Configuración de interfaz (fuentes, colores, tamaños, temas)

## 🎨 Sistema de Visualización

### Diseño Corporativo
- **Paleta de colores**: Azul (#1c2a38, #4a90e2) y Verde (#2ecc71, #27ae60)
- **Tipografía**: Arial, sans-serif con jerarquía visual clara
- **Gráficas profesionales**: Plotly con diseño corporativo y tooltips interactivos
- **Layout responsive**: Sistema de columnas adaptable (2×4, 3 columnas, etc.)

### Secciones del Dashboard

#### 📊 Indicadores Principales
- **Métricas del Negocio** (2 filas × 4 columnas):
  - Fila 1: Volumen Total, TX Efectivas, Ticket Promedio, Mes Pico
  - Fila 2: Día Más TX, Día Mayor Volumen, Día Menos TX, Día Menor Volumen
- **Segmentación y Desempeño**: TX por tipo de persona (Natural/Jurídica)

#### 💰 Distribución por Cliente
- **Gráfica de Montos**: Barras horizontales con gradiente azul corporativo
- **Gráfica de Transacciones**: Barras horizontales con gradiente verde
- **Formato abreviado**: $X.XM (millones), X.XK (miles)

#### 👥 Información General de Clientes (Tabs por cliente)

**🟦 Capa 1: Datos Transaccionales**

1. **Métricas Principales** (2 filas × 4 columnas):
   - Fila 1: TX Efectivas, Monto Total, Promedio TX, Efectividad
   - Fila 2: Días Activo, Primera TX, Última TX, Comisiones

2. **📅 Distribución Temporal**:
   - Métricas: Día más/menos activo, Tendencia mensual, Promedio mensual
   - **Gráfica "Días más Representativos"**: Top 10 días con mayor volumen
     - Formato: Barras con colores corporativos, etiquetas internas, análisis automático
   - **Gráfica "Evolución en el Tiempo"**: Dual axis (TX + Volumen)
     - Barras azules para transacciones
     - Línea verde para volumen en COP
     - Hover interactivo con fechas formateadas

3. **🎯 Concentración de Operaciones** (3 columnas):
   - **Top 5 Personas Naturales**: Monto, % participación, cantidad TX
   - **Top 5 Personas Jurídicas**: Monto, % participación, cantidad TX
   - **Top 5 Bancos Receptores**: Monto, % participación, cantidad TX

4. **💰 Análisis de Montos y Eficiencia** (4 columnas):
   - Monto Mínimo, Monto Máximo, Mediana
   - Tasa de Rechazo (con indicador inverso)
   - Beneficiarios Únicos, Bancos Únicos

5. **📋 Tipos de Transacciones**: Distribución con porcentajes

6. **📋 Últimas 50 Transacciones**: Tabla interactiva ancho completo

7. **🎯 Análisis de Participación**: Top beneficiarios y bancos (tablas detalladas)

**🟥 Capa 2: Evaluación de Riesgo y Cumplimiento**
- **Scoring de Riesgo**: Score total, GAFI, UIAF, Operativo
- **Nivel de Riesgo**: Visualización con código de colores (Verde/Naranja/Rojo/Morado)
- **Alertas de Riesgo**: Sistema de priorización (Crítica/Alta/Media/Baja)
- **Recomendaciones**: Acciones sugeridas automáticamente
- **Matriz de Riesgo**: Inherente vs Residual, Controles aplicados, Gaps identificados

## ⚙️ Configuración

### `config/settings.py`
```python
ESTADOS_EFECTIVOS = ["PAGADO", "VALIDADO"]
TIPOS_PERSONA_NATURAL = ["Natural", "Persona Natural", ...]
TIPOS_PERSONA_JURIDICA = ["Jurídica", "Empresa", ...]
```

### `config/ui_config.py`
```python
FUENTES = {
    'h1': 32,  # Reducido de 52 para mejor visualización
    'h2': 26,  # Reducido de 44
    'h3': 22,  # Reducido de 36
    'base': 14  # Reducido de 20
}

METRICAS = {
    'valor': 24,    # Reducido de 36
    'label': 13,    # Reducido de 20
    'delta': 14     # Reducido de 18
}

TARJETAS_CLIENTE = {
    'columnas': 4,           # Cambiado de 3 a 4
    'header': 16,            # Reducido de 18
    'valor_metrica': 18,     # Reducido de 20
    'label_metrica': 11,     # Reducido de 12
    'padding': '10px 14px'   # Reducido de '12px 16px'
}
```

## 📈 Métricas y Scoring

### Score Total (0-100)
- **GAFI (40%)**: Volumen, frecuencia, diversidad, patrones geográficos
- **UIAF (35%)**: Fragmentación, rechazo, inconsistencias, señales de alerta
- **Operativo (25%)**: Errores, complejidad, volatilidad, eficiencia

### Niveles de Riesgo
- 🟢 **Bajo** (0-30): Review trimestral, due diligence estándar
- 🟠 **Medio** (31-50): Review mensual, monitoreo reforzado
- 🔴 **Alto** (51-75): Review quincenal, DDR requerida
- 🟣 **Crítico** (76-100): Review semanal, escalamiento inmediato

## 🚨 Sistema de Alertas

### Tipos de Alertas
- 📋 **UIAF**: Cumplimiento normativo, reportes obligatorios
- 🚨 **Fraude**: Detección de patrones sospechosos
- ⚙️ **Operacional**: Riesgos operativos y eficiencia
- 📜 **Compliance**: Incumplimientos regulatorios
- 👁️ **Reputacional**: Riesgos de imagen corporativa
- 🎯 **KYC/AML**: Conocimiento del cliente y prevención de lavado

### Prioridades
- 🔥 **Crítica**: 1-2 días para acción, requiere reporte UIAF
- 🚨 **Alta**: 3-7 días para acción, escalamiento necesario
- ⚠️ **Media**: 8-15 días para acción, monitoreo reforzado
- ℹ️ **Baja**: 16-30 días para acción, seguimiento rutinario

## 🎯 Flujo de Análisis

```
1. Carga de Datos (Sistema Híbrido)
   ├── 🎯 Selector de método en sidebar:
   │   ├── 📤 Subir Archivo (Excel hasta 100MB)
   │   ├── 🎯 Datos de Ejemplo (generación sintética)
   │   └── 📁 Archivo Local (modo desarrollo)
   ├── Validación de tamaño y formato
   ├── Validación de columnas requeridas
   ├── Normalización de beneficiarios (reduce duplicados)
   ├── Normalización de bancos (estandarización)
   └── Filtrado de fechas (>= 2000-01-01)

2. Procesamiento Global
   ├── Filtro de rango de fechas (inicio/fin)
   ├── Cálculo de métricas de negocio (15+ indicadores)
   ├── Segmentación por tipo de persona (Natural/Jurídica)
   └── Pre-cálculo de resúmenes por cliente (caché)

3. Caracterización GAFI
   ├── Perfil de comportamiento
   ├── Métricas de riesgo
   └── Banderas automáticas

4. Análisis de Riesgo Integral
   ├── Scoring multicapa (GAFI + UIAF + Operativo)
   ├── Generación de alertas (6 tipos, 4 prioridades)
   ├── Evaluación de controles
   └── Determinación de nivel de riesgo

5. Visualización y Reportes
   ├── Dashboard interactivo
   ├── Gráficas corporativas (Plotly)
   ├── Tablas detalladas con dataframes
   ├── 🆕 Análisis de beneficiarios inactivos
   └── Recomendaciones accionables
```

## 📊 Normas de Visualización Aplicadas

### Principios de Data Visualization
- ✅ **Ratio tinta-datos optimizado**: Eliminar elementos innecesarios
- ✅ **Jerarquía visual clara**: Títulos → Datos → Ejes → Grid
- ✅ **Coherencia cromática**: Colores con significado consistente
- ✅ **Legibilidad**: Tamaños de fuente adecuados (11-18px según contexto)
- ✅ **Interactividad**: Tooltips informativos con formato profesional
- ✅ **Accesibilidad**: Contraste WCAG AA, responsive design

### Paleta Corporativa
```
Azul Primario:  #1c2a38, #2d4263, #4a90e2
Verde Acento:   #2ecc71, #27ae60, #58d68d
Grises:         #333, #666, #e0e0e0
Fondos:         #f8f9fa, rgba(248, 249, 250, 0.5)
```

## 🔒 Seguridad y Cumplimiento

- ✅ **File uploader seguro**: Archivos procesados en memoria (no se guardan en disco)
- ✅ **Validación de tamaño**: Límite de 100MB por archivo para prevenir abusos
- ✅ **Validación de datos**: Entrada robusta con manejo de errores
- ✅ **Logging completo**: Operaciones críticas registradas (carga, errores, procesamiento)
- ✅ **Escape HTML**: Prevención de XSS en visualizaciones
- ✅ **Normalización avanzada**: Beneficiarios y bancos (reduce duplicados por variaciones)
- ✅ **Filtrado de fechas**: Validación de rangos (>= 2000-01-01)
- ✅ **Datos sintéticos seguros**: Generador de datos de ejemplo sin información real
- ✅ **Gestión de memoria**: Garbage collection y límites de cache para estabilidad
- ✅ **Cumplimiento GAFI/UIAF**: Análisis según estándares internacionales
- ✅ **Auditoría**: Alertas y riesgos rastreables
- 🔐 **Autenticación opcional**: Protección con password (configuración secrets.toml)

## 📝 Versión e Historial

**v2.2.0** - Febrero 2026 🆕
- ✅ **Sistema Híbrido de Carga**: 3 métodos (Subir/Demo/Local) con selector en sidebar
- ✅ **Generador de Datos Sintéticos**: Datos de ejemplo para demos sin archivos reales
  - 3 clientes ficticios con perfiles variados
  - 470 transacciones con distribución realista
  - Beneficiarios PN/PJ, bancos colombianos, montos lognormales
- ✅ **Optimización de Memoria**: Mejoras para Streamlit Cloud (plan gratuito 1GB)
  - Límite de carga: 100MB por archivo
  - Garbage collection automático
  - Validación de tamaño de archivo
  - Cache con límite de entradas (max_entries=10)
- ✅ **Corrección de Errores**: Fix lectura de Excel desde objeto UploadedFile
- ✅ **UX Mejorada**: Mensajes informativos, warnings para datasets grandes

**v2.1.0** - Febrero 2026
- ✅ **File uploader implementado**: Carga dinámica sin hardcoding
- ✅ **Deployment ready**: Configuración completa para Streamlit Cloud
- ✅ **Normalización avanzada**: Beneficiarios y bancos con reducción de duplicados
- ✅ **Filtro de fechas global**: Rango de fechas aplicado a todos los clientes
- ✅ **Análisis de inactividad**: Beneficiarios inactivos (90+ días), baja actividad (≤3 TX), montos bajos
- ✅ **Métricas ampliadas**: 15+ indicadores (mediana, volatilidad, frecuencia, tendencias, concentración)
- ✅ **UI optimizada**: Fuentes reducidas 20-30%, layout 4 columnas
- ✅ **Documentación completa**: Guías de deployment, checklist, scripts automatizados

**v2.0.0** - Enero 2026
- Dashboard mejorado con visualización profesional
- Gráficas corporativas con Plotly
- Sistema de análisis temporal completo
- Concentración de operaciones por tipo de persona
- Análisis de días pico con insights automáticos
- UI responsive y configurable

## 📄 Licencia

© 2026 AdamoPay - Sistema de Análisis y Reporte Transaccional

## 👥 Contribución

Proyecto interno de AdamoPay. Para contribuciones o sugerencias, contactar al equipo de desarrollo.

## 📞 Soporte

Para soporte técnico o consultas, contactar:
- Email: tech@adamopay.com
- Documentación interna: Wiki de AdamoPay

---

**Desarrollado con ❤️ por el equipo de AdamoPay**
