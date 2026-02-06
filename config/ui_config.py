"""
Configuración de UI - AdamoPay
Edita estos valores para cambiar tamaños de fuente y estilos en toda la app
"""

# ====================================
# CONFIGURACIÓN DE FUENTES
# ====================================

# Títulos principales - Optimizados para navegadores
FUENTES = {
    "h1": 32,           # Título principal de la app (antes: 52)
    "h2": 26,           # Títulos de sección (antes: 44)
    "h3": 22,           # Subtítulos (antes: 36)
    "h4": 19,           # Títulos menores (antes: 28)
    "h5": 17,           # Títulos muy pequeños (antes: 24)
}

# Texto general - Tamaños estándar web
TEXTO = {
    "base": 14,         # Texto normal en toda la app (antes: 20)
    "caption": 12,      # Textos pequeños (captions) (antes: 17)
    "parrafo": 14,      # Párrafos (antes: 20)
}

# Métricas (las cards con números grandes) - Reducidas proporcionalmente
METRICAS = {
    "valor": 17,        # El número grande de la métrica (antes: 18) 
    "label": 13,        # El título de la métrica (antes: 20)
    "delta": 12,        # El texto pequeño debajo (cambio/delta) (antes: 18)
}

# Tarjetas de resumen por cliente (sección "👥 Resumen por Cliente") - Optimizadas para 4 columnas
TARJETAS_CLIENTE = {
    "header": 16,       # Título de la tarjeta (nombre del cliente) - Reducido de 18
    "valor_metrica": 18,    # Números dentro de las tarjetas - Reducido de 20
    "label_metrica": 11,    # Labels dentro de las tarjetas - Reducido de 12
    "delta": 10,        # Deltas dentro de las tarjetas - Reducido de 11
    "texto": 12,        # Texto general en tarjetas - Reducido de 13
    "expander_header": 13,  # Header del expander - Reducido de 14
    "expander_content": 12, # Contenido del expander - Reducido de 13
    "padding": "10px 14px", # Espaciado del header - Reducido de 12px 16px
    "columnas": 4,      # Número de tarjetas por fila - Cambiado de 3 a 4
}

# Componentes interactivos - Reducidos a tamaños estándar
COMPONENTES = {
    "boton": 14,        # Botones (antes: 19)
    "tab": 15,          # Pestañas/tabs (antes: 20)
    "input": 14,        # Inputs y selects (antes: 19)
    "dataframe": 13,    # Tablas de datos (antes: 18)
    "expander": 15,     # Expanders generales (antes: 20)
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
