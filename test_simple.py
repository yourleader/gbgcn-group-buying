#!/usr/bin/env python3
"""
🔍 Test Simple - Verificar que todo funciona
"""

import sys
import os

def test_imports():
    """Probar imports básicos"""
    print("🔍 Probando imports...")
    
    try:
        import fastapi
        print("✅ FastAPI OK")
    except Exception as e:
        print(f"❌ FastAPI Error: {e}")
        return False
    
    try:
        import uvicorn
        print("✅ Uvicorn OK")
    except Exception as e:
        print(f"❌ Uvicorn Error: {e}")
        return False
    
    try:
        import sqlalchemy
        print("✅ SQLAlchemy OK")
    except Exception as e:
        print(f"❌ SQLAlchemy Error: {e}")
        return False
    
    return True

def test_project_imports():
    """Probar imports del proyecto"""
    print("\n🔍 Probando imports del proyecto...")
    
    # Agregar src al path
    sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
    
    try:
        from core.config import settings
        print("✅ Config OK")
    except Exception as e:
        print(f"❌ Config Error: {e}")
        return False
    
    try:
        from database.models import Base
        print("✅ Models OK")
    except Exception as e:
        print(f"❌ Models Error: {e}")
        return False
    
    return True

def main():
    print("🚀 TEST SIMPLE DEL SISTEMA GBGCN")
    print("=" * 40)
    
    # Test 1: Imports básicos
    if not test_imports():
        print("❌ Error en dependencias básicas")
        return
    
    # Test 2: Imports del proyecto
    if not test_project_imports():
        print("❌ Error en imports del proyecto")
        return
    
    print("\n✅ ¡Todos los tests pasaron!")
    print("🎉 El sistema está listo")
    
    print("\n🚀 Para iniciar el servidor:")
    print("   python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000")

if __name__ == "__main__":
    main() 