# 🚀 Script de PowerShell para probar GBGCN en Windows
Write-Host "🚀 GBGCN GROUP BUYING SYSTEM - WINDOWS SETUP" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Yellow

# Configurar variables de entorno
Write-Host "🔧 Configurando entorno..." -ForegroundColor Cyan
$env:PYTHONPATH = "."
$env:DATABASE_URL = "sqlite+aiosqlite:///./test_gbgcn.db"

# Crear archivo .env
Write-Host "📝 Creando archivo de configuración..." -ForegroundColor Cyan
@"
DATABASE_URL=sqlite+aiosqlite:///./test_gbgcn.db
SECRET_KEY=test-secret-key-for-gbgcn
DEBUG=true
ENVIRONMENT=development
"@ | Out-File -FilePath ".env" -Encoding UTF8

Write-Host "✅ Configuración lista" -ForegroundColor Green

# Mostrar información
Write-Host "`n📋 OPCIONES DE PRUEBA:" -ForegroundColor Yellow
Write-Host "=" * 30 -ForegroundColor Yellow

Write-Host "`n1️⃣ PRUEBA RÁPIDA (Solo API):" -ForegroundColor White
Write-Host "   python quick_test.py" -ForegroundColor Gray

Write-Host "`n2️⃣ PRUEBA COMPLETA (Con datos y modelo):" -ForegroundColor White
Write-Host "   python test_gbgcn_complete.py" -ForegroundColor Gray

Write-Host "`n3️⃣ INICIO MANUAL:" -ForegroundColor White
Write-Host "   python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Gray

Write-Host "`n🌐 URLs importantes:" -ForegroundColor Yellow
Write-Host "   • API: http://localhost:8000/api/v1" -ForegroundColor Cyan
Write-Host "   • Docs: http://localhost:8000/docs" -ForegroundColor Cyan

Write-Host "`n🔑 Credenciales de prueba:" -ForegroundColor Yellow
Write-Host "   • Usuario: gbgcn@test.com" -ForegroundColor Cyan
Write-Host "   • Password: test123456" -ForegroundColor Cyan

Write-Host "`n💡 Para Flutter:" -ForegroundColor Yellow
Write-Host "   • Base URL: http://localhost:8000/api/v1" -ForegroundColor Cyan
Write-Host "   • Obtén el token usando POST /auth/login" -ForegroundColor Cyan

Write-Host "`n🎯 ¿Qué opción quieres ejecutar? (1/2/3) o Enter para salir:" -ForegroundColor Green
$choice = Read-Host

switch ($choice) {
    "1" { 
        Write-Host "🚀 Ejecutando prueba rápida..." -ForegroundColor Green
        python quick_test.py 
    }
    "2" { 
        Write-Host "🧪 Ejecutando prueba completa..." -ForegroundColor Green
        python test_gbgcn_complete.py 
    }
    "3" { 
        Write-Host "🌐 Iniciando servidor manualmente..." -ForegroundColor Green
        python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
    }
    default { 
        Write-Host "👋 ¡Hasta luego!" -ForegroundColor Yellow 
    }
} 