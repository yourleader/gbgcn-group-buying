#!/usr/bin/env python3
"""
🚀 Prueba Rápida del Modelo GBGCN
Script simple para probar el sistema en 3 minutos
"""

import os
import subprocess
import time
import requests

def main():
    print("⚡ GBGCN - PRUEBA RÁPIDA (3 MINUTOS)")
    print("=" * 50)
    
    # 1. Configurar variables de entorno
    print("🔧 Configurando entorno...")
    os.environ['PYTHONPATH'] = '.'
    os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./test_gbgcn.db'
    
    # 2. Instalar dependencias básicas
    print("📦 Verificando dependencias...")
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        print("✅ Dependencias OK")
    except ImportError:
        print("❌ Instalando dependencias...")
        subprocess.run(['pip', 'install', 'fastapi', 'uvicorn', 'sqlalchemy', 'aiosqlite'])
    
    # 3. Crear archivo .env
    with open('.env', 'w') as f:
        f.write('DATABASE_URL=sqlite+aiosqlite:///./test_gbgcn.db\n')
        f.write('SECRET_KEY=test-key-123\n')
    
    print("✅ Configuración lista")
    
    # 4. Iniciar servidor
    print("🚀 Iniciando servidor API...")
    print("⏳ El servidor se iniciará en http://localhost:8000")
    print("📖 Documentación: http://localhost:8000/docs")
    print("\n💡 Para probar completamente, ejecuta:")
    print("   python test_gbgcn_complete.py")
    
    # Iniciar servidor
    subprocess.run([
        'python', '-m', 'uvicorn',
        'src.api.main:app',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--reload'
    ])

if __name__ == "__main__":
    main() 