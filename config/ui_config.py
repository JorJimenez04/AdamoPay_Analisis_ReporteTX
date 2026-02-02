"""
Configuración de UI - AdamoPay
Edita estos valores para cambiar tamaños de fuente y estilos en toda la app
"""

# ====================================
# CONFIGURACIÓN DE FUENTES
# ====================================

# Títulos principales
FUENTES = {
    "h1": 52,           # Título principal de la app
    "h2": 44,           # Títulos de sección
    "h3": 36,           # Subtítulos
    "h4": 28,           # Títulos menores
    "h5": 24,           # Títulos muy pequeños
}

# Texto general
TEXTO = {
    "base": 20,         # Texto normal en toda la app
    "caption": 17,      # Textos pequeños (captions)
    "parrafo": 20,      # Párrafos
}

# Métricas (las cards con números grandes)
METRICAS = {
    "valor": 36,        # El número grande de la métrica
    "label": 20,        # El título de la métrica
    "delta": 18,        # El texto pequeño debajo (cambio/delta)
}

# Tarjetas de resumen por cliente (sección "👥 Resumen por Cliente")
TARJETAS_CLIENTE = {
    "header": 18,       # Título de la tarjeta (nombre del cliente)
    "valor_metrica": 28,    # Números dentro de las tarjetas
    "label_metrica": 14,    # Labels dentro de las tarjetas
    "delta": 13,        # Deltas dentro de las tarjetas
    "texto": 14,        # Texto general en tarjetas
    "expander_header": 14,  # Header del expander
    "expander_content": 13, # Contenido del expander
    "padding": "12px 16px", # Espaciado del header
    "columnas": 3,      # Número de tarjetas por fila (2, 3 o 4)
}

# Componentes interactivos
COMPONENTES = {
    "boton": 19,        # Botones
    "tab": 20,          # Pestañas/tabs
    "input": 19,        # Inputs y selects
    "dataframe": 18,    # Tablas de datos
    "expander": 20,     # Expanders generales
}

# ====================================
# CONFIGURACIÓN DE COLORES
# ====================================

COLORES = {
    "primario": "#667eea",
    "secundario": "#764ba2",
    "exito": "#4CAF50",
    "advertencia": "#FF9800",
    "error": "#f44336",
    "critico": "#9C27B0",
    "info": "#2196F3",
}

# ====================================
# CONFIGURACIÓN DE LAYOUT
# ====================================

LAYOUT = {
    "ancho_sidebar": 300,           # Ancho de la barra lateral
    "padding_contenido": "2rem",    # Espaciado del contenido
    "gap_columnas": "medium",       # Espacio entre columnas (small, medium, large)
}

# ====================================
# TEMAS PREDEFINIDOS (OPCIONAL)
# ====================================

TEMAS = {
    "Compacto": {
        "h1": 42, "h2": 34, "h3": 28, "texto": 16, "metrica_valor": 36,
        "tarjeta_header": 16, "tarjeta_valor": 24,
    },
    "Estándar": {
        "h1": 52, "h2": 44, "h3": 36, "texto": 20, "metrica_valor": 48,
        "tarjeta_header": 18, "tarjeta_valor": 28,
    },
    "Grande": {
        "h1": 62, "h2": 54, "h3": 44, "texto": 24, "metrica_valor": 60,
        "tarjeta_header": 22, "tarjeta_valor": 36,
    },
    "Presentación": {
        "h1": 72, "h2": 64, "h3": 52, "texto": 28, "metrica_valor": 72,
        "tarjeta_header": 26, "tarjeta_valor": 44,
    },
}

# Tema activo (cambiar entre: "Compacto", "Estándar", "Grande", "Presentación" o None para usar valores personalizados arriba)
TEMA_ACTIVO = None  # None = usar valores personalizados, o elige un tema: "Estándar", "Grande", etc.


def obtener_configuracion():
    """Retorna la configuración activa (tema o personalizado)"""
    if TEMA_ACTIVO and TEMA_ACTIVO in TEMAS:
        tema = TEMAS[TEMA_ACTIVO]
        return {
            "fuentes": {
                "h1": tema["h1"],
                "h2": tema["h2"],
                "h3": tema["h3"],
                "h4": tema.get("h4", tema["h3"] - 8),
                "h5": tema.get("h5", tema["h3"] - 12),
            },
            "texto": {
                "base": tema["texto"],
                "caption": tema["texto"] - 3,
                "parrafo": tema["texto"],
            },
            "metricas": {
                "valor": tema["metrica_valor"],
                "label": tema["texto"],
                "delta": tema["texto"] - 2,
            },
            "tarjetas": {
                "header": tema["tarjeta_header"],
                "valor_metrica": tema["tarjeta_valor"],
                "label_metrica": tema["tarjeta_header"] - 4,
                "delta": tema["tarjeta_header"] - 5,
                "texto": tema["tarjeta_header"] - 4,
                "expander_header": tema["tarjeta_header"] - 4,
                "expander_content": tema["tarjeta_header"] - 5,
                "padding": "12px 16px",
                "columnas": 4,
            },
        }
    else:
        # Configuración personalizada
        return {
            "fuentes": FUENTES,
            "texto": TEXTO,
            "metricas": METRICAS,
            "tarjetas": TARJETAS_CLIENTE,
            "componentes": COMPONENTES,
            "colores": COLORES,
            "layout": LAYOUT,
        }
