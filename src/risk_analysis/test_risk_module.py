"""
Test básico del módulo de análisis de riesgo
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datetime import datetime

# Test de imports
print("Testing imports...")
try:
    from risk_analysis import (
        analizar_riesgo_cliente,
        calcular_score_integral,
        generar_alertas_automaticas,
        generar_reporte_riesgo
    )
    print("✅ Imports exitosos")
except Exception as e:
    print(f"❌ Error en imports: {e}")
    sys.exit(1)

# Test de funcionalidad básica
print("\nTesting funcionalidad básica...")

# Crear datos de prueba
df_test = pd.DataFrame({
    'CLIENTE': ['Test Cliente'] * 10,
    'FECHA': pd.date_range('2025-01-01', periods=10),
    'MONTO (COP)': [15_000_000] * 10,
    'TIPO DE TRA': ['Fondeo'] * 10,
    'ESTADO': ['Pagado'] * 8 + ['Rechazado'] * 2,
    'TIPO_PERSONA': ['Natural'] * 10
})

try:
    # Test 1: Análisis completo
    print("\n1. Probando analizar_riesgo_cliente...")
    resultado = analizar_riesgo_cliente(df_test, cliente_nombre="Test Cliente")
    
    print(f"   Cliente: {resultado['cliente']}")
    print(f"   Score Total: {resultado['scoring']['score_total']}")
    print(f"   Nivel de Riesgo: {resultado['scoring']['nivel_riesgo']}")
    print(f"   Alertas: {len(resultado['alertas'])}")
    print(f"   ✅ Análisis completado")
    
    # Test 2: Generar reporte
    print("\n2. Probando generar_reporte_riesgo...")
    reporte = generar_reporte_riesgo(resultado)
    print(f"   Reporte generado: {len(reporte)} caracteres")
    print(f"   ✅ Reporte generado")
    
    # Test 3: Scoring individual
    print("\n3. Probando calcular_score_integral...")
    scoring = calcular_score_integral(df_test)
    print(f"   Score GAFI: {scoring['score_gafi']}")
    print(f"   Score UIAF: {scoring['score_uiaf']}")
    print(f"   Score Operativo: {scoring['score_operativo']}")
    print(f"   ✅ Scoring calculado")
    
    print("\n" + "="*70)
    print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
    print("="*70)
    
except Exception as e:
    print(f"\n❌ Error en test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
