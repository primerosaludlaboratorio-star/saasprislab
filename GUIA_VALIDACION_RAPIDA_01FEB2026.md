# 🎯 GUÍA RÁPIDA DE VERIFICACIÓN - PRODUCCIÓN
**URL de Producción:** https://prislab-v5-oswjakz55a-uc.a.run.app

---

## ⚡ ANTES DE EMPEZAR (CRÍTICO)

### 🧹 LIMPIAR CACHÉ DEL NAVEGADOR
**Sin este paso, verás la versión vieja**

**Opción 1 (Rápida):**
- Presiona `CTRL + F5` en cada página

**Opción 2 (Completa):**
1. Presiona `CTRL + SHIFT + DELETE`
2. Selecciona "Imágenes y archivos en caché"
3. Clic en "Borrar datos"

---

## ✅ CHECKLIST DE VALIDACIÓN

### 1️⃣ GEMELO DIGITAL (Consultorio)
**URL:** https://prislab-v5-oswjakz55a-uc.a.run.app/consultorio/nueva/

**Debes ver:**
- [ ] ✅ Título "Nueva Consulta - Gemelo Digital"
- [ ] ✅ Buscador de pacientes con lupa
- [ ] ✅ Selector de planes (Básico/Profesional/Empresarial)
- [ ] ✅ Botón azul con gradiente "Gemelo Digital"
- [ ] ✅ Diseño minimalista y moderno

**Si NO ves esto:** Presiona `CTRL + F5` y recarga

---

### 2️⃣ SMART LAB (Laboratorio)
**URL:** https://prislab-v5-oswjakz55a-uc.a.run.app/laboratorio/captura/resultados/[ORDEN_ID]/

**Debes ver:**
- [ ] ✅ Interfaz de captura inteligente
- [ ] ✅ Campos con validación automática
- [ ] ✅ Diseño optimizado para entrada rápida
- [ ] ✅ Botones de acción claros

**Si NO ves esto:** Presiona `CTRL + F5` y recarga

---

### 3️⃣ TIMELINE (Historial Clínico)
**URL:** https://prislab-v5-oswjakz55a-uc.a.run.app/pacientes/expediente/[PACIENTE_ID]/

**Debes ver:**
- [ ] ✅ Timeline cronológico del paciente
- [ ] ✅ Eventos de consultas, laboratorio, farmacia
- [ ] ✅ Diseño visual con línea de tiempo
- [ ] ✅ Navegación fluida por historial

**Si NO ves esto:** Presiona `CTRL + F5` y recarga

---

### 4️⃣ SIDEBAR RBAC (En todas las páginas)

**Debes ver:**
- [ ] ✅ Menú lateral con módulos según tu rol
- [ ] ✅ Solo aparecen módulos para los que tienes permiso
- [ ] ✅ Diseño limpio y organizado
- [ ] ✅ Navegación intuitiva

**Si NO ves esto:** Presiona `CTRL + F5` y recarga

---

## 🔴 SI ALGO NO FUNCIONA

### Problema: "No veo los cambios"
**Solución:**
1. Presiona `CTRL + SHIFT + DELETE`
2. Borra "Imágenes y archivos en caché"
3. Cierra el navegador completamente
4. Abre de nuevo y ve a la URL

### Problema: "Error 500"
**Solución:**
1. Verifica que estés usando la URL correcta
2. Inicia sesión de nuevo
3. Si persiste, revisa los logs en Google Cloud Console

### Problema: "Página en blanco"
**Solución:**
1. Presiona `CTRL + F5`
2. Abre las herramientas de desarrollador (`F12`)
3. Ve a la pestaña "Console" y busca errores
4. Verifica que no haya bloqueadores de contenido

---

## 📞 INFORMACIÓN TÉCNICA

**URL de Producción:**
```
https://prislab-v5-oswjakz55a-uc.a.run.app
```

**Build ID:**
```
4bdc53ac-b989-46c6-aae4-7efcf789d8c4
```

**Revisión de Cloud Run:**
```
prislab-v5-00058-q9f
```

**Estado:**
```
✅ SUCCESS - Desplegado y funcionando
```

---

## ✅ LISTA DE VALIDACIÓN RÁPIDA

Usa esta lista para verificar con tu equipo:

- [ ] **Servidor activo:** La URL principal carga correctamente
- [ ] **Login funciona:** Puedo iniciar sesión
- [ ] **Gemelo Digital:** Veo la nueva interfaz en Consultorio
- [ ] **Smart Lab:** Veo la captura inteligente en Laboratorio
- [ ] **Timeline:** Veo el historial unificado de pacientes
- [ ] **Sidebar RBAC:** Solo veo módulos según mi rol
- [ ] **Sin errores:** No hay mensajes de error en la consola

---

**¡TODO ESTÁ LISTO PARA VALIDACIÓN!** 🚀
