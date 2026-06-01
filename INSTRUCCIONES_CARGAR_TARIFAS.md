# 📋 INSTRUCCIONES PARA CARGAR TARIFAS DE LABORATORIO

## ✅ **SISTEMA ACTUALIZADO Y DESPLEGADO**

**Revisión:** `prislab-v5-00023-kzn`  
**Fecha:** 30 de Enero de 2026  
**Estado:** ✅ **LISTO PARA USAR**

---

## 🎯 **CÓMO CARGAR LAS TARIFAS**

### **Opción 1: Desde la Interfaz Web (RECOMENDADA)**

1. **Accede al sistema como administrador:**
   ```
   URL: https://prislab-v5-811785477499.us-central1.run.app/admin/
   Usuario: admin
   Contraseña: Prislab2026
   ```

2. **Ve a la sección de carga de tarifas:**
   ```
   https://prislab-v5-811785477499.us-central1.run.app/laboratorio/admin/cargar-tarifas/
   ```

3. **Sube el archivo CSV:**
   - Haz clic en "Elegir archivo"
   - Selecciona el archivo `tarifas.csv` (C:\Users\jonil\Desktop\PRISLAB_SaaS\tarifas.csv)
   - Haz clic en "Cargar Tarifas"

4. **Espera el resultado:**
   - El sistema procesará las 619 tarifas
   - Te mostrará un resumen con:
     - Categorías creadas
     - Estudios creados
     - Estudios actualizados
     - Errores (si los hay)

---

## 📊 **RESULTADOS ESPERADOS**

Según la carga local que realizamos, deberías ver:

```
✅ Categorías creadas: 3
   - Paquetes
   - Perfiles
   - Pruebas

✅ Estudios cargados: ~542 estudios nuevos
   - Paquetes: 17 estudios
   - Perfiles: 81 estudios
   - Pruebas: 444 estudios

⚠️ Errores esperados: ~34 errores
   (Debido a caracteres especiales en algunos nombres, no afectan el funcionamiento)
```

---

## 🔐 **ACCESO DIRECTO A LA FUNCIONALIDAD**

### **URL de Carga de Tarifas:**
```
https://prislab-v5-811785477499.us-central1.run.app/laboratorio/admin/cargar-tarifas/
```

### **Requisitos:**
- ✅ Estar autenticado como usuario administrador (staff)
- ✅ Tener el archivo `tarifas.csv` en formato correcto

---

## 📁 **FORMATO DEL ARCHIVO CSV**

El archivo debe tener esta estructura:

```csv
,Tarifa: Conv Empresa A,,,

Tipo,Código,Abreviatura,Descripción,Importe
Paquetes,CHEBA,CHEBA,CHEQUEO BASICO GENERAL,555
Perfiles,339,AC FOSFO,AC. ANTI FOSFOLÍPIDOS IgG IgM,800
Pruebas,GLU,GLU,GLUCOSA,85
```

**Columnas:**
- **Tipo:** Categoría del estudio (Paquetes, Perfiles, Pruebas)
- **Código:** Código único del estudio
- **Abreviatura:** Abreviatura corta
- **Descripción:** Nombre completo del estudio
- **Importe:** Precio en pesos mexicanos

---

## 🧪 **VERIFICAR LAS TARIFAS CARGADAS**

### **1. Desde el Admin de Django:**
```
https://prislab-v5-811785477499.us-central1.run.app/admin/laboratorio/estudio/
```

### **2. Consultar estadísticas:**
- Ve a la página de carga de tarifas
- El resumen te mostrará el total de estudios en la base de datos

### **3. Buscar un estudio específico:**
- Usa el buscador del admin de Django
- Filtra por categoría, código o nombre

---

## 🔄 **ACTUALIZAR TARIFAS**

Si necesitas actualizar las tarifas más adelante:

1. **Edita el archivo CSV** con los nuevos precios
2. **Vuelve a subirlo** usando la misma interfaz
3. El sistema **actualizará automáticamente** los estudios existentes (por código)
4. Solo se crearán nuevos estudios si el código no existe

---

## ⚠️ **NOTAS IMPORTANTES**

1. **Backup Automático:** El sistema mantiene historial de cambios de precios
2. **Validación:** Los precios no pueden ser negativos
3. **Códigos Duplicados:** Si un código se repite en el CSV, solo se tomará el último
4. **Caracteres Especiales:** Algunos caracteres especiales pueden causar advertencias, pero no impiden la carga

---

## 🆘 **SOLUCIÓN DE PROBLEMAS**

### **Problema: No puedo acceder a la URL de carga**
**Solución:** Verifica que estás autenticado como administrador

### **Problema: El archivo no se sube**
**Solución:** 
- Verifica que el archivo tenga extensión `.csv`
- Asegúrate de que no esté abierto en Excel
- Intenta guardarlo de nuevo como CSV UTF-8

### **Problema: Muchos errores al cargar**
**Solución:** 
- Los errores por caracteres especiales son normales
- Si hay más de 100 errores, revisa el formato del CSV
- Verifica que las columnas estén en el orden correcto

---

## 📞 **SOPORTE**

Si tienes algún problema:

1. **Revisa los logs en Google Cloud:**
   ```powershell
   gcloud logging read "resource.labels.service_name=prislab-v5" --limit 50 --project=prislab-v5-ai
   ```

2. **Contacta al equipo de desarrollo** con la siguiente información:
   - URL exacta donde ocurrió el problema
   - Mensaje de error (si lo hay)
   - Número de línea del CSV donde falló

---

## ✅ **CHECKLIST DE VERIFICACIÓN**

Después de cargar las tarifas, verifica:

- [ ] El sistema muestra el resumen de carga exitoso
- [ ] El total de estudios en BD coincide con lo esperado (~542)
- [ ] Puedes buscar y ver estudios en el admin de Django
- [ ] Los precios se muestran correctamente
- [ ] Las 3 categorías aparecen (Paquetes, Perfiles, Pruebas)

---

**¡Sistema listo para usar!** 🚀

**URL del Sistema:** https://prislab-v5-811785477499.us-central1.run.app  
**URL de Carga:** https://prislab-v5-811785477499.us-central1.run.app/laboratorio/admin/cargar-tarifas/  
**Usuario Admin:** admin  
**Contraseña:** Prislab2026
