# 🚀 Guía de Despliegue - Streamlit Community Cloud

## ✅ Archivos Preparados

Tu proyecto ya está listo para despliegue. Se han creado/actualizado:

- ✅ [`requirements.txt`](requirements.txt) - Versiones específicas de dependencias
- ✅ [`.streamlit/config.toml`](.streamlit/config.toml) - Configuración corporativa
- ✅ [`.gitignore`](.gitignore) - Protección de archivos sensibles
- ✅ [`packages.txt`](packages.txt) - Dependencias del sistema (vacío por ahora)

## 📋 Pasos para Desplegar

### Paso 1: Crear Repositorio en GitHub

#### Opción A: Desde GitHub Web (Recomendado)

1. Ve a [github.com](https://github.com) e inicia sesión
2. Haz clic en el botón **"+"** → **"New repository"**
3. Configura:
   - **Repository name**: `adamopay-analisis-transaccional`
   - **Description**: "Sistema avanzado de análisis de riesgo transaccional AdamoPay"
   - **Visibility**: 
     - 🔓 **Public** (para usar Streamlit Cloud GRATIS)
     - 🔒 **Private** (requiere Streamlit Cloud Enterprise)
   - **NO** marcar "Initialize with README" (ya tienes uno)
4. Haz clic en **"Create repository"**

#### Opción B: Desde VSCode Terminal

```powershell
# Ya estás en el directorio correcto, solo verifica
Get-Location
# Debe mostrar: C:\Python\Analisis y Reporte Transaccional_AdamoPay\AdamoPay_Analisis_ReporteTX
```

### Paso 2: Preparar Git (si no lo has hecho)

```powershell
# Verificar si git está inicializado
git status

# Si NO está inicializado, ejecuta:
git init
git branch -M main

# Configurar tu identidad (solo primera vez)
git config user.name "Tu Nombre"
git config user.email "tu-email@ejemplo.com"
```

### Paso 3: Agregar Archivos al Repositorio

```powershell
# Ver qué archivos se subirán (verifica que NO haya datos sensibles)
git status

# Agregar todos los archivos (respetando .gitignore)
git add .

# Ver qué se agregó
git status

# Crear commit
git commit -m "Preparar proyecto para despliegue en Streamlit Cloud"
```

### Paso 4: Conectar con GitHub

```powershell
# Reemplaza TU_USUARIO con tu usuario de GitHub
git remote add origin https://github.com/TU_USUARIO/adamopay-analisis-transaccional.git

# Verificar conexión
git remote -v
```

### Paso 5: Subir a GitHub

```powershell
# Subir código
git push -u origin main

# Si te pide credenciales, usa:
# - Usuario: tu nombre de usuario de GitHub
# - Password: Personal Access Token (NO tu password regular)
```

#### 🔑 Crear Personal Access Token (si es necesario)

1. Ve a GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Genera nuevo token con permisos: `repo` (todos)
3. Copia el token (solo se muestra una vez)
4. Úsalo como password cuando Git lo pida

### Paso 6: Desplegar en Streamlit Cloud

1. **Ve a** [share.streamlit.io](https://share.streamlit.io)

2. **Inicia sesión** con tu cuenta de GitHub

3. **Haz clic en** "New app" (botón azul)

4. **Configura el despliegue**:
   ```
   Repository: TU_USUARIO/adamopay-analisis-transaccional
   Branch: main
   Main file path: app.py
   App URL (optional): adamopay-analisis
   ```

5. **Configuración avanzada** (opcional):
   - Python version: 3.11
   - (Deja el resto por defecto)

6. **Haz clic en** "Deploy!"

### Paso 7: Esperar Despliegue

El proceso toma 2-5 minutos:

```
[✓] Cloning repository...
[✓] Installing dependencies from requirements.txt...
[✓] Starting Streamlit app...
[✓] Your app is live!
```

Tu app estará disponible en:
```
https://TU_USUARIO-adamopay-analisis.streamlit.app
```

## 🎯 Después del Despliegue

### Ver Logs en Tiempo Real

1. En Streamlit Cloud, haz clic en tu app
2. Verás los logs en la parte inferior
3. Cualquier error aparecerá ahí

### Actualizar la Aplicación

Cada vez que hagas cambios locales:

```powershell
# 1. Guardar cambios
git add .
git commit -m "Descripción del cambio"

# 2. Subir a GitHub
git push

# 3. Streamlit Cloud se actualiza AUTOMÁTICAMENTE
# (toma 1-2 minutos)
```

### Configurar Secrets (Datos Sensibles)

Si necesitas variables de entorno o secrets:

1. En Streamlit Cloud → Tu app → Settings
2. Ve a la sección "Secrets"
3. Agrega en formato TOML:

```toml
# Ejemplo de secrets
[passwords]
admin = "tu_password_seguro"

[database]
connection_string = "postgresql://..."

[api_keys]
api_key = "tu_api_key"
```

4. En tu código, accede con:
```python
import streamlit as st
password = st.secrets["passwords"]["admin"]
```

## ⚠️ Verificaciones Pre-Despliegue

Antes de subir a GitHub, verifica:

### 1. Datos Sensibles

```powershell
# Buscar archivos grandes (más de 50MB no se subirán)
Get-ChildItem -Recurse | Where-Object {$_.Length -gt 50MB} | Select-Object FullName, @{Name="Size(MB)";Expression={[math]::Round($_.Length/1MB,2)}}

# Ver qué se incluirá en Git
git status

# Ver qué NO se incluirá (debe incluir .venv/, logs/, etc.)
git status --ignored
```

### 2. Archivo de Datos

¿Tu archivo `data/Data_Clients&TX.xlsx` contiene datos reales o de prueba?

- **Datos de PRUEBA**: Déjalo, se subirá a GitHub
- **Datos REALES**: Comenta la línea en `.gitignore`:
  ```gitignore
  # Descomentar si tienes datos sensibles:
  data/Data_Clients&TX.xlsx
  ```

### 3. Probar Localmente

```powershell
# Ejecutar app localmente una última vez
streamlit run app.py

# Verificar que TODO funciona:
# ✅ Carga de datos
# ✅ Visualizaciones
# ✅ Cálculos de riesgo
# ✅ Alertas
```

## 🆘 Solución de Problemas

### Error: "No module named 'X'"

**Causa**: Falta dependencia en `requirements.txt`

**Solución**:
```powershell
# Ver módulos instalados localmente
pip list

# Agregar a requirements.txt y subir cambios
git add requirements.txt
git commit -m "Agregar dependencia faltante"
git push
```

### Error: "File not found: data/Data_Clients&TX.xlsx"

**Causa**: Archivo no está en GitHub (probablemente en `.gitignore`)

**Solución 1** (Si son datos de prueba):
```powershell
# Verificar .gitignore
Get-Content .gitignore | Select-String "xlsx"

# Si está bloqueado, descomentarlo
# Luego subir:
git add data/Data_Clients&TX.xlsx
git commit -m "Agregar datos de prueba"
git push
```

**Solución 2** (Si son datos reales):
- Crea un archivo de datos de prueba fake
- O usa Streamlit secrets para conectar a una base de datos

### Error: "Memory limit exceeded"

**Causa**: App consume mucha RAM (límite gratuito: 1GB)

**Solución**:
- Reduce el tamaño del archivo de datos
- Usa muestreo de datos en producción
- Considera actualizar a Streamlit Cloud Pro

### App muy lenta

**Causa**: Cálculos pesados en cada interacción

**Solución**: Usa `@st.cache_data` en funciones pesadas:

```python
@st.cache_data(ttl=3600)  # Cache por 1 hora
def cargar_y_procesar_datos(archivo):
    # ...existing code...
    return df_procesado
```

## 📊 Monitoreo

### Métricas Disponibles

En Streamlit Cloud → Analytics:
- **Viewers**: Usuarios únicos
- **Views**: Páginas vistas
- **Resource usage**: CPU, RAM, ancho de banda

### Límites del Plan Gratuito

- ✅ **Apps**: 1 app privada + ilimitadas públicas
- ✅ **RAM**: 1 GB
- ✅ **CPU**: Compartido
- ✅ **Storage**: 1 GB
- ✅ **Viewers**: Ilimitados
- ✅ **Uptime**: 24/7

## 🎉 ¡Listo!

Una vez desplegado, comparte el link:
```
https://TU_USUARIO-adamopay-analisis.streamlit.app
```

Tu aplicación estará disponible 24/7 para cualquier persona con el link.

---

## 🔄 Comandos Rápidos de Referencia

```powershell
# Estado del repositorio
git status

# Ver cambios
git diff

# Agregar cambios
git add .

# Commit
git commit -m "Mensaje descriptivo"

# Subir a GitHub (actualiza Streamlit automáticamente)
git push

# Ver historial
git log --oneline -10

# Ver archivos ignorados
git status --ignored
```

## 📞 Soporte

- **Streamlit Docs**: https://docs.streamlit.io/
- **Streamlit Cloud**: https://docs.streamlit.io/streamlit-community-cloud
- **GitHub Docs**: https://docs.github.com/

---

**¿Listo para empezar?** Ejecuta los comandos del Paso 3 en adelante. 🚀
