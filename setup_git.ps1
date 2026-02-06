# ====================================
# SCRIPT DE SETUP PARA GIT Y GITHUB
# ====================================
# 
# Este script te ayuda a configurar Git y preparar el proyecto
# para deployment en Streamlit Cloud
#
# USO:
#   .\setup_git.ps1

Write-Host "🚀 AdamoPay - Setup de Git y GitHub" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Git está instalado
try {
    $gitVersion = git --version
    Write-Host "✅ Git encontrado: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git no está instalado. Por favor instala Git desde: https://git-scm.com" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Verificar si ya es un repositorio git
if (Test-Path ".git") {
    Write-Host "ℹ️  Este directorio ya es un repositorio Git" -ForegroundColor Yellow
    
    # Mostrar estado
    Write-Host "`n📊 Estado actual:" -ForegroundColor Cyan
    git status --short
    
    $continuar = Read-Host "`n¿Deseas continuar con commit y push? (s/n)"
    if ($continuar -ne 's') {
        Write-Host "❌ Operación cancelada" -ForegroundColor Red
        exit 0
    }
} else {
    Write-Host "📁 Inicializando nuevo repositorio Git..." -ForegroundColor Cyan
    git init
    Write-Host "✅ Repositorio inicializado" -ForegroundColor Green
}

Write-Host ""

# Verificar configuración de usuario
$userName = git config user.name
$userEmail = git config user.email

if ([string]::IsNullOrEmpty($userName) -or [string]::IsNullOrEmpty($userEmail)) {
    Write-Host "⚙️  Configurar usuario de Git" -ForegroundColor Yellow
    Write-Host ""
    
    $userName = Read-Host "Nombre completo"
    $userEmail = Read-Host "Email"
    
    git config --global user.name "$userName"
    git config --global user.email "$userEmail"
    
    Write-Host "✅ Configuración guardada" -ForegroundColor Green
} else {
    Write-Host "✅ Usuario configurado: $userName <$userEmail>" -ForegroundColor Green
}

Write-Host ""

# Agregar archivos
Write-Host "📦 Agregando archivos al staging..." -ForegroundColor Cyan
git add .

# Mostrar qué se va a commitear
Write-Host "`n📋 Archivos para commit:" -ForegroundColor Cyan
git status --short

Write-Host ""

# Crear commit
$commitMsg = Read-Host "Mensaje del commit (Enter para default)"
if ([string]::IsNullOrEmpty($commitMsg)) {
    $commitMsg = "feat: Add file uploader and deployment configuration"
}

git commit -m "$commitMsg"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Commit creado exitosamente" -ForegroundColor Green
} else {
    Write-Host "⚠️  No hay cambios para commitear o hubo un error" -ForegroundColor Yellow
}

Write-Host ""

# Verificar si hay remote configurado
$remoteUrl = git remote get-url origin 2>$null

if ([string]::IsNullOrEmpty($remoteUrl)) {
    Write-Host "🌐 Configurar repositorio remoto en GitHub" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "PASOS PARA CREAR REPOSITORIO EN GITHUB:" -ForegroundColor Cyan
    Write-Host "1. Ve a https://github.com/new" -ForegroundColor White
    Write-Host "2. Repository name: adamopay-analisis-transaccional" -ForegroundColor White
    Write-Host "3. Visibility: Private (recomendado)" -ForegroundColor White
    Write-Host "4. NO marcar 'Initialize with README'" -ForegroundColor White
    Write-Host "5. Clic en 'Create repository'" -ForegroundColor White
    Write-Host ""
    
    $githubUrl = Read-Host "Pega la URL del repositorio (https://github.com/usuario/repo.git)"
    
    if (-not [string]::IsNullOrEmpty($githubUrl)) {
        git remote add origin $githubUrl
        git branch -M main
        
        Write-Host "✅ Remote configurado: $githubUrl" -ForegroundColor Green
        Write-Host ""
        Write-Host "🚀 Haciendo push a GitHub..." -ForegroundColor Cyan
        
        git push -u origin main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Push exitoso!" -ForegroundColor Green
            Write-Host ""
            Write-Host "🎉 SIGUIENTE PASO:" -ForegroundColor Green
            Write-Host "   Ve a https://share.streamlit.io para deployar la app" -ForegroundColor White
        } else {
            Write-Host "❌ Error en el push. Verifica tus credenciales de GitHub" -ForegroundColor Red
            Write-Host "   Tip: Usa un Personal Access Token en lugar de password" -ForegroundColor Yellow
            Write-Host "   https://github.com/settings/tokens" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  URL no proporcionada. Configura el remote manualmente:" -ForegroundColor Yellow
        Write-Host "   git remote add origin https://github.com/usuario/repo.git" -ForegroundColor White
        Write-Host "   git branch -M main" -ForegroundColor White
        Write-Host "   git push -u origin main" -ForegroundColor White
    }
} else {
    Write-Host "✅ Remote configurado: $remoteUrl" -ForegroundColor Green
    Write-Host ""
    Write-Host "🚀 Haciendo push a GitHub..." -ForegroundColor Cyan
    
    git push
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Push exitoso!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No se pudo hacer push. Intenta manualmente:" -ForegroundColor Yellow
        Write-Host "   git push origin main" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "✅ Setup completado!" -ForegroundColor Green
Write-Host ""
Write-Host "📖 Para deployar en Streamlit Cloud, sigue la guía:" -ForegroundColor Cyan
Write-Host "   DEPLOYMENT_CLOUD.md" -ForegroundColor White
Write-Host ""
