# AdamoPay - Sistema de Análisis y Reporte Transaccional

Sistema para el análisis, scoring de riesgo y generación de reportes de transacciones de AdamoPay.

## Estructura del Proyecto

```
AdamoPay_Analisis_ReporteTX/
│
├── data/
│   ├── raw/                # Datos originales
│   └── processed/          # Datos limpios / analizados
│
├── src/
│   ├── analysis/           # Lógica de análisis transaccional
│   ├── risk/               # Scoring y categorización de riesgo
│   ├── monitoring/         # Reglas de monitoreo
│   └── reports/            # Generación de reportes (PDF)
│
├── templates/
│   └── report_templates/   # Plantillas de reportes
│
├── outputs/
│   └── reports/            # Reportes finales generados
│
├── config/
│   └── settings.py         # Configuraciones generales
│
├── main.py                 # Punto de entrada del proyecto
├── requirements.txt        # Dependencias
└── README.md               # Documentación
```

## Instalación

1. Clonar o descargar el proyecto
2. Crear un entorno virtual:
   ```bash
   python -m venv venv
   ```
3. Activar el entorno virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Uso

Ejecutar el script principal:
```bash
python main.py
```

## Módulos

### `src/analysis/`
Contiene la lógica para el análisis de transacciones.

### `src/risk/`
Implementa el sistema de scoring y categorización de riesgo.

### `src/monitoring/`
Define e implementa las reglas de monitoreo transaccional.

### `src/reports/`
Genera reportes en formato PDF con los resultados del análisis.

## Configuración

Editar `config/settings.py` para ajustar:
- Rutas de datos
- Umbrales de riesgo
- Formato de reportes
- Configuraciones de base de datos

## Contribución

Proyecto interno de AdamoPay.

## Licencia

Propietario - AdamoPay
