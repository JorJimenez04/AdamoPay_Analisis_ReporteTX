# 📋 Estructura del Proyecto - AdamoPay

## 📁 Árbol de Directorios

```
AdamoPay_Analisis_ReporteTX/
│
├── 📄 app.py                           # Aplicación principal de Streamlit
├── 📄 ESTRUCTURA_PROYECTO.md           # Este archivo - Documentación de estructura
├── 📄 requirements.txt                 # Dependencias del proyecto
├── 📄 .gitignore                       # Archivos ignorados por Git
│
├── 📁 config/                          # Configuración del proyecto
│   └── settings.py                     # Configuraciones base
│
├── 📁 src/                             # Código fuente modular
│   └── utils/                          # Utilidades y funciones auxiliares
│       ├── __init__.py                 # Inicializador del módulo
│       ├── data_loader.py              # Funciones de carga de datos
│       ├── exporters.py                # Funciones de exportación
│       └── calculators.py              # Cálculos y métricas
│
├── 📁 data/                            # Datos del proyecto
│   └── Data_Clients&TX.xlsx           # Archivo Excel principal (gitignored)
│
├── 📁 assets/                          # Recursos estáticos
│   ├── LogoAdamoServices.png          # Logo Adamo Services
│   └── Adamopay.png                   # Logo AdamoPay
│
├── 📁 backups/                         # Respaldos de versiones
│   └── app_v1.0.0_STABLE.py           # Versión estable guardada
│
└── 📁 docs/                            # Documentación adicional
    ├── CHANGELOG.md                    # Registro de cambios
    ├── IDEAS_FUTURAS.md                # Ideas para implementar
    └── MANUAL_USUARIO.md               # Manual de usuario
```

---

## 📄 Descripción de Archivos Principales

### **app.py** (550 líneas)
Aplicación principal de Streamlit que contiene:

**Líneas 1-18:** Imports y configuración inicial
- Librerías: streamlit, pandas, numpy, plotly, io, datetime
- Configuración de rutas y paths

**Líneas 20-35:** Función `clasificar_tipo_persona()`
- Clasifica beneficiarios en Personas Naturales o Jurídicas
- Según tipo de identificación (C, PA, CE, N, NIT)

**Líneas 37-85:** Función `cargar_datos_clientes()`
- Carga datos desde Excel con múltiples sheets
- Limpieza y transformación de datos
- Caché de 60 segundos para optimización
- Clasificación automática de tipo de persona

**Líneas 87-115:** Configuración de página y UI principal
- Configuración de Streamlit (título, icono, layout)
- Header con logos y títulos

**Líneas 117-172:** Vista General del Negocio
- 7 métricas principales en columnas
- Filtrado de transacciones efectivas (Pagadas/Validadas)
- Cálculo de métricas globales
- Segmentación PN vs PJ

**Líneas 174-303:** Resumen por Cliente
- Tarjetas de cliente en layout de 2 columnas
- Métricas por cliente (TX, monto, tipos, estados)
- Visualización de beneficiarios (PN/PJ)
- Estados de transacciones con códigos de color

**Líneas 305-395:** Dashboard Detallado - Exportación
- Botones de exportación (Excel, CSV, TX Efectivas)
- Funciones de conversión de datos
- Generación de hojas de resumen

**Líneas 397-550:** Dashboard Detallado - Tabs por Cliente
- Tabs individuales para cada cliente
- Cards HTML con métricas principales
- Análisis financiero detallado
- Resumen de actividad
- Tabla de últimas 50 transacciones

**Líneas 552-560:** Footer
- Información de copyright
- Versión de la aplicación

---

## 🔧 Configuración y Dependencias

### **requirements.txt**
```txt
streamlit==1.29.0
pandas==2.1.4
numpy==1.24.3
plotly==5.18.0
openpyxl==3.1.2
python-dateutil==2.8.2
```

### **config/settings.py**
Contiene configuraciones base del sistema importadas en app.py

---

## 📊 Flujo de Datos

```
Data_Clients&TX.xlsx (Excel)
        ↓
cargar_datos_clientes()
        ↓
DataFrame completo con TIPO_PERSONA
        ↓
        ├──→ Vista General (métricas globales)
        ├──→ Resumen por Cliente (tarjetas)
        └──→ Dashboard Detallado (tabs)
                ↓
        Exportación (Excel/CSV)
```

---

## 🎨 Componentes de UI

### **Vista General del Negocio**
- **Componente:** `st.metric()` x7
- **Datos:** Métricas globales calculadas de df_relevantes
- **Características:**
  - Clientes Activos
  - TX Pagadas/Validadas
  - Volumen Efectivo
  - Tasa Efectividad
  - Comisiones
  - Personas Naturales (👤)
  - Personas Jurídicas (🏢)

### **Resumen por Cliente**
- **Componente:** `st.markdown()` para cards + `st.metric()` para métricas
- **Layout:** 2 columnas
- **Elementos por tarjeta:**
  - Header gradient con nombre del cliente
  - Métricas de tipos de transacción
  - Métricas de beneficiarios (PN/PJ)
  - Mini cards de estados

### **Dashboard Detallado**
- **Componente:** `st.tabs()` para navegación
- **Elementos:**
  - Botones de exportación (`st.download_button()`)
  - Cards HTML con métricas principales
  - Análisis de actividad y financiero
  - Tabla de datos (`st.dataframe()`)

---

## 🔐 Datos Sensibles (Gitignored)

Los siguientes archivos NO deben subirse a Git:

```gitignore
# Datos
data/*.xlsx
data/*.csv
data/*.json

# Configuración sensible
.env
credentials.json
.streamlit/secrets.toml

# Cache de Python
__pycache__/
*.pyc
```

---

## 📈 Métricas Calculadas

### **Métricas Globales**
1. **total_transacciones_global**: Total de registros en df_completo
2. **tx_relevantes_global**: Transacciones con ESTADO = 'Pagado' o 'Validado'
3. **monto_total_global**: Suma de MONTO (COP) de TX relevantes
4. **tasa_exito_global**: (tx_relevantes / total_tx) * 100
5. **comision_total_global**: Suma de COMISION ((MONTO TOT) de TX relevantes
6. **promedio_tx_global**: Promedio de MONTO (COP) de TX relevantes
7. **tx_pn / tx_pj**: Conteo de TX por tipo de persona
8. **monto_pn / monto_pj**: Suma de montos por tipo de persona

### **Métricas por Cliente**
1. **total_tx**: Cantidad de transacciones del cliente
2. **total_monto**: Suma de MONTO (COP)
3. **tipos_dict**: Conteo por tipo de transacción (Fondeo/Crédito/Débito)
4. **pn_count / pj_count**: Segmentación de beneficiarios
5. **metricas_estado**: Diccionario con TX y monto por estado

### **Métricas Detalladas (Tabs)**
1. **tx_efectivas_cliente**: TX pagadas/validadas del cliente
2. **monto_total_cliente**: Volumen transaccionado efectivo
3. **monto_promedio_cliente**: Promedio por transacción
4. **tasa_exito_cliente**: % de efectividad del cliente
5. **dias_activo**: Días entre primera y última transacción
6. **monto_min/max/mediana**: Análisis de distribución de montos
7. **comision_total/promedio**: Análisis de comisiones

---

## 🎯 Funciones Clave

### **clasificar_tipo_persona(tipo_id)**
- **Input:** String con tipo de identificación
- **Output:** 'Natural', 'Jurídica' o 'Desconocido'
- **Lógica:**
  - Natural: C, PA, CE, CC, CEDULA
  - Jurídica: N, NIT
  - Resto: Desconocido

### **cargar_datos_clientes()**
- **Input:** None (usa ruta hardcoded)
- **Output:** (df_completo, clientes_info, lista_clientes)
- **Cache:** 60 segundos
- **Transformaciones:**
  1. Lee todas las sheets del Excel
  2. Añade columna 'CLIENTE' con nombre de sheet
  3. Convierte tipos de datos (fecha, montos)
  4. Limpia y formatea valores
  5. Aplica clasificación TIPO_PERSONA

### **convertir_a_excel(df)**
- **Input:** DataFrame
- **Output:** BytesIO con archivo Excel
- **Características:**
  - Sheet 'Datos_Completos' con todos los registros
  - Sheet 'Resumen' con métricas principales

### **convertir_a_csv(df)**
- **Input:** DataFrame
- **Output:** CSV codificado en UTF-8
- **Uso:** Exportación rápida de datos

---

## 🎨 Paleta de Colores

### **Estados de Transacción**
```python
'Pagado': '#4CAF50'      # Verde
'Validado': '#2196F3'    # Azul
'Retornado': '#FF9800'   # Naranja
'Rechazado': '#f44336'   # Rojo
'Aprobado': '#9C27B0'    # Morado
```

### **Gradientes**
- **Cards de Cliente:** `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
- **Fondo general:** Blanco/Gris claro (#f8f9fa)

### **Iconos**
- 👥 Clientes
- 💳 Transacciones
- 💰 Dinero/Fondeo
- ✅ Éxito/Pagado
- 📊 Métricas/Datos
- 👤 Persona Natural
- 🏢 Persona Jurídica
- 🔵 Validado
- 🔄 Retornado
- ❌ Rechazado
- 👍 Aprobado

---

## 🔄 Versiones

### **v1.0.0** (2025-01-03) - VERSIÓN ESTABLE ACTUAL
- ✅ Vista General del Negocio
- ✅ Clasificación Personas Naturales vs Jurídicas
- ✅ Resumen por Cliente con tarjetas interactivas
- ✅ Dashboard Detallado por cliente
- ✅ Exportación a Excel, CSV y TX Efectivas
- ✅ Sistema de tabs por cliente
- ✅ Análisis financiero detallado

---

## 📚 Documentación de Columnas del Excel

### **Columnas Requeridas**
| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| FECHA | datetime | Fecha de la transacción | 2025-01-01 |
| CLIENTE | string | Nombre del cliente (sheet) | CM Group |
| TIPO DE IDENTIFICACION | string | Tipo de ID del beneficiario | C, N, PA, CE, NIT |
| MONTO (COP) | numeric | Monto en pesos colombianos | 1500000 |
| COMISION ((MONTO TOT | numeric | Comisión cobrada | 15000 |
| ESTADO | string | Estado de la transacción | Pagado, Validado, etc. |
| TIPO DE TRA | string | Tipo de transacción | Fondeo, Crédito, Débito |
| SALDO (COP) | numeric | Saldo después de la TX | 2000000 |

### **Columnas Generadas**
| Columna | Tipo | Descripción | Valores |
|---------|------|-------------|---------|
| TIPO_PERSONA | string | Clasificación del beneficiario | Natural, Jurídica, Desconocido |

---

## 🚀 Instrucciones de Uso

### **Instalación**
```bash
# Crear entorno virtual
python -m venv .venv

# Activar entorno
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### **Ejecución**
```bash
# Desarrollo (con hot-reload)
streamlit run app.py --server.runOnSave=true

# Producción
streamlit run app.py
```

### **Configuración de Puerto**
```bash
# Puerto personalizado
streamlit run app.py --server.port=8502
```

---

## 🔍 Troubleshooting

### **Error: No se encuentra el archivo Excel**
- Verificar que `data/Data_Clients&TX.xlsx` existe
- Verificar permisos de lectura
- Verificar que el archivo no está abierto en Excel

### **Error: ModuleNotFoundError**
- Ejecutar `pip install -r requirements.txt`
- Verificar que el entorno virtual está activado

### **Error: Cache warnings**
- Reiniciar aplicación
- Limpiar cache: `streamlit cache clear`

### **Datos no se actualizan**
- El cache está configurado a 60 segundos
- Esperar o recargar manualmente la página (R)

---

## 📞 Soporte

**Proyecto:** AdamoPay - Sistema de Análisis y Reporte Transaccional  
**Versión:** 1.0.0  
**Fecha:** Enero 2025  
**Equipo:** AdamoPay  

---

## 📝 Notas Importantes

1. **NUNCA modificar app.py directamente** - Crear backup antes de cambios
2. **Mantener datos sensibles fuera de Git** - Usar .gitignore
3. **Documentar cambios en CHANGELOG.md** - Registro de versiones
4. **Probar con datos de prueba primero** - Antes de usar datos reales
5. **Mantener estructura modular** - Facilita mantenimiento

---

*Última actualización: 2025-01-03*
