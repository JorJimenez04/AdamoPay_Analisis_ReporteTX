# 🚀 Guía de Deployment - Streamlit Cloud (GRATIS)

Esta guía te llevará paso a paso para desplegar la aplicación AdamoPay en Streamlit Community Cloud de forma **completamente gratuita**.

---

## 📋 Pre-requisitos

1. ✅ Cuenta de GitHub (gratuita)
2. ✅ Cuenta de Streamlit Cloud (gratuita) - [share.streamlit.io](https://share.streamlit.io)
3. ✅ El código de la aplicación funcionando localmente

---

## 📦 Fase 1: Preparar el Proyecto (✅ COMPLETADA)

### ✅ Archivos de configuración creados:

- `requirements.txt` - Dependencias Python
- `.streamlit/config.toml` - Configuración de la app
- `.streamlit/secrets.toml.example` - Template para secretos (opcional)
- `.gitignore` - Archivos a excluir de git
- `README.md` - Documentación actualizada

---

## 🔧 Fase 2: Setup en GitHub

### Paso 1: Inicializar Git (si no está inicializado)

```powershell
# Navegar al directorio del proyecto
cd "c:\Python\Analisis y Reporte Transaccional_AdamoPay\AdamoPay_Analisis_ReporteTX"

# Verificar si ya tiene git
git status

# Si no está inicializado:
git init
```

### Paso 2: Configurar usuario Git (si es primera vez)

```powershell
git config --global user.name "Tu Nombre"
git config --global user.email "tu_email@ejemplo.com"
```

### Paso 3: Commit de los cambios

```powershell
# Agregar todos los archivos (respetando .gitignore)
git add .

# Crear el commit inicial
git commit -m "feat: Add file uploader and deployment configuration"
```

### Paso 4: Crear repositorio en GitHub

1. Ve a [github.com](https://github.com)
2. Haz clic en el botón **"+"** (esquina superior derecha) → **"New repository"**
3. Configuración recomendada:
   - **Repository name**: `adamopay-analisis-transaccional`
   - **Description**: "Sistema de Análisis y Reporte Transaccional AdamoPay"
   - **Visibility**: 
     - ✅ **Private** (recomendado para datos empresariales)
     - ⚠️ Public solo si no hay datos sensibles
   - **NO** marcar "Initialize with README" (ya tienes uno)
4. Clic en **"Create repository"**

### Paso 5: Conectar y Push al repositorio

GitHub te mostrará comandos como estos:

```powershell
# Agregar el remote (reemplaza con TU URL de GitHub)
git remote add origin https://github.com/TU_USUARIO/adamopay-analisis-transaccional.git

# Renombrar rama a main (si es necesario)
git branch -M main

# Push inicial
git push -u origin main
```

**💡 Autenticación en GitHub:**
- Si te pide credenciales, usa un **Personal Access Token** (no password)
- Ve a: GitHub → Settings → Developer Settings → Personal Access Tokens → Generate new token
- Permisos necesarios: `repo` (acceso completo)

---

## ☁️ Fase 3: Deployment en Streamlit Cloud

### Paso 1: Acceder a Streamlit Cloud

1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Haz clic en **"Sign in"** o **"Get started"**
3. **Conecta con tu cuenta de GitHub** (autoriza el acceso)

### Paso 2: Deploy Nueva App

1. Clic en **"New app"** o **"Deploy an app"**
2. Completa el formulario:
   - **Repository**: Selecciona `TU_USUARIO/adamopay-analisis-transaccional`
   - **Branch**: `main`
   - **Main file path**: `app.py`
   - **App URL** (opcional): Personaliza la URL (ej: `adamopay-analytics`)
3. Expandir **"Advanced settings"** (opcional):
   - **Python version**: 3.11 (recomendado)
   - **Secrets**: Déjalo vacío por ahora
4. Clic en **"Deploy!"**

### Paso 3: Esperar el Deployment

- ⏱️ El primer deployment toma **5-10 minutos**
- Verás logs en tiempo real mostrando la instalación de dependencias
- Cuando veas "You can now view your Streamlit app in your browser" → **¡Listo!** 🎉

### Paso 4: Probar la Aplicación

1. Tu app estará disponible en: `https://TU-URL.streamlit.app`
2. **Subir archivo**: Usa el widget de carga para subir tu Excel
3. **Verificar**: Todas las funciones deberían trabajar igual que en local

---

## 🔒 Fase 4: Configurar Autenticación (Opcional)

Si quieres proteger tu app con contraseña:

### Paso 1: Crear archivo de autenticación

Agrega al inicio de `app.py` (antes de cargar datos):

```python
# ===== AUTENTICACIÓN =====
def verificar_acceso():
    """Verifica credenciales antes de mostrar la app."""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        st.markdown("## 🔒 Acceso Restringido")
        password = st.text_input("Contraseña", type="password", key="password_input")
        
        if st.button("Ingresar"):
            # Obtener password desde secrets (Streamlit Cloud) o variable local
            password_correcto = st.secrets.get("auth", {}).get("password", "adamopay2026")
            
            if password == password_correcto:
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
        
        st.stop()

# Ejecutar autenticación
verificar_acceso()
# ===== FIN AUTENTICACIÓN =====
```

### Paso 2: Configurar secretos en Streamlit Cloud

1. Ve a tu app en Streamlit Cloud
2. Clic en **"Settings"** (menú ⚙️)
3. Clic en **"Secrets"**
4. Pega este contenido:

```toml
[auth]
password = "TU_PASSWORD_SUPER_SEGURO_AQUI"
```

5. Clic en **"Save"**
6. La app se reiniciará automáticamente

---

## 📊 Recursos de Streamlit Cloud (Plan Gratuito)

| Recurso | Límite Gratuito |
|---------|----------------|
| **RAM** | 1 GB |
| **CPU** | 1 core |
| **Almacenamiento** | Sin límite de archivos subidos por usuario |
| **Apps simultáneas** | 3 apps públicas (ilimitadas privadas si conectas GitHub) |
| **Usuarios concurrentes** | ~10-50 (depende del uso de recursos) |
| **Ancho de banda** | Ilimitado |
| **Tiempo de ejecución** | Sin límite (pero hiberna tras inactividad) |

### ⚠️ Limitaciones a considerar:

- **Hibernación**: La app se "duerme" tras ~7 días de inactividad
  - Se despierta automáticamente cuando alguien la visita
  - Primer acceso tras hibernación toma ~30 segundos
- **Memoria**: Si tu Excel es muy grande (>50MB), puede haber problemas
  - Solución: Filtrar o comprimir datos antes de subir
- **Sin persistencia**: Los archivos subidos NO se guardan permanentemente
  - Cada usuario debe subir su archivo cada vez
  - Considera migrar a base de datos si necesitas persistencia

---

## 🔄 Actualizar la App (Push Updates)

Cada vez que hagas cambios al código:

```powershell
# 1. Guardar cambios en Git
git add .
git commit -m "Descripción de tus cambios"

# 2. Push a GitHub
git push origin main

# 3. Streamlit Cloud se actualiza automáticamente (2-5 min)
```

---

## 📱 Compartir la App

### Opción 1: Compartir URL directamente
```
https://tu-app.streamlit.app
```

### Opción 2: Repositorio privado + invitaciones
1. En Streamlit Cloud, ve a **Settings** → **Sharing**
2. Puedes invitar usuarios por email
3. Solo ellos podrán acceder (incluso si el repo es privado)

---

## 🐛 Troubleshooting

### Problema 1: "ModuleNotFoundError"
**Causa**: Falta una dependencia en `requirements.txt`

**Solución**:
```powershell
# Agregar la dependencia faltante
echo "nombre-paquete>=version" >> requirements.txt
git add requirements.txt
git commit -m "fix: Add missing dependency"
git push
```

### Problema 2: "App is too large" o Memory Error
**Causa**: El Excel cargado es muy grande

**Soluciones**:
- Opción A: Reducir el tamaño del archivo (filtrar datos antiguos)
- Opción B: Dividir en múltiples archivos más pequeños
- Opción C: Migrar a base de datos PostgreSQL (también gratis en Supabase)

### Problema 3: La app está "hibernando"
**Causa**: No se usó en varios días

**Solución**: Simplemente abre la URL, tomará ~30 seg en despertar

### Problema 4: Errores de encoding en Excel
**Causa**: Caracteres especiales en los nombres de hojas

**Solución**: Renombrar hojas del Excel evitando caracteres raros (ñ, ç, etc.)

---

## 🎯 Próximos Pasos (Mejoras Futuras)

1. **Base de Datos**: Migrar de Excel a PostgreSQL (Supabase gratis)
2. **Autenticación OAuth**: Google/Microsoft login
3. **Reportes PDF**: Descarga automática de reportes
4. **Notificaciones**: Alertas por email
5. **API REST**: Integración con otros sistemas

---

## 📞 Soporte y Recursos

- **Documentación Streamlit**: [docs.streamlit.io](https://docs.streamlit.io)
- **Community Forum**: [discuss.streamlit.io](https://discuss.streamlit.io)
- **GitHub Issues**: Para reportar bugs en tu proyecto

---

## ✅ Checklist Final

Antes de considerar el deployment completo:

- [ ] Código funciona localmente con file uploader
- [ ] requirements.txt actualizado
- [ ] .streamlit/config.toml configurado
- [ ] .gitignore previene commit de datos sensibles
- [ ] Repositorio GitHub creado y código pusheado
- [ ] App desplegada en Streamlit Cloud
- [ ] Probado subiendo archivo Excel en producción
- [ ] URL compartida con usuarios autorizados
- [ ] (Opcional) Autenticación con contraseña configurada

---

**🎉 ¡Felicidades! Tu aplicación AdamoPay está en producción de forma gratuita.**

Para cualquier duda o problema durante el deployment, revisa la sección de Troubleshooting o contacta al equipo de desarrollo.
