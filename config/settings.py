"""
Configuración general del proyecto AdamoPay - Análisis y Reporte Transaccional
"""

# Configuración de rutas
DATA_RAW_PATH = "data/raw"
DATA_PROCESSED_PATH = "data/processed"
OUTPUTS_PATH = "outputs/reports"
TEMPLATES_PATH = "templates/report_templates"

# Configuración de análisis
RISK_THRESHOLDS = {
    "bajo": 0.3,
    "medio": 0.6,
    "alto": 1.0
}

# Configuración de reportes
REPORT_FORMAT = "PDF"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Configuración de base de datos (si aplica)
# DATABASE_CONFIG = {
#     "host": "localhost",
#     "port": 5432,
#     "database": "adamopay_tx"
# }
