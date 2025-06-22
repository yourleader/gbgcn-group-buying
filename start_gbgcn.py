#!/usr/bin/env python3
"""
🚀 Script Simple para Iniciar GBGCN
"""

import os
import subprocess
import sys
import time

def main():
    print("🚀 INICIANDO GBGCN - MODELO DE RECOMENDACIONES")
    print("=" * 50)
    
    # Configurar entorno
    print("🔧 Configurando...")
    os.environ['PYTHONPATH'] = '.'
    
    # Crear archivo .env
    with open('.env', 'w') as f:
        f.write('DATABASE_URL=sqlite+aiosqlite:///./gbgcn_test.db\n')
        f.write('SECRET_KEY=test-secret-key\n')
        f.write('DEBUG=true\n')
    
    print("✅ Configuración lista")
    
    # Mostrar información
    print("\n📋 INFORMACIÓN IMPORTANTE:")
    print("🌐 Servidor: http://localhost:8000")
    print("📖 Documentación: http://localhost:8000/docs")
    print("🔑 Usuario: test@example.com")
    print("🔐 Password: testpassword123")
    
    print("\n🚀 Iniciando servidor...")
    print("⏳ Espera unos segundos...")
    
    # Iniciar servidor
    try:
        subprocess.run([
            sys.executable, '-m', 'uvicorn',
            'src.api.main:app',
            '--host', '0.0.0.0',
            '--port', '8000',
            '--reload'
        ])
    except KeyboardInterrupt:
        print("\n👋 Servidor detenido")

if __name__ == "__main__":
    main() 