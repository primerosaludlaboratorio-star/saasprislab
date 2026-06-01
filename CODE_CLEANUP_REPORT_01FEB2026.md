# 🧹 CODE CLEANUP REPORT - PRISLAB V5.0
**Date:** February 1, 2026 - 02:00 AM  
**Objective:** Remove garbage code, debug statements, and clean codebase  
**Status:** 🔄 **IN PROGRESS**

---

## 📊 **ISSUES FOUND**

### **Debug Statements:**
- **Python print()**: 43 instances (excluding libraries)
- **JavaScript console.log()**: 21 instances in templates
- **Total**: 64 debug statements

### **Code Quality:**
- **TODO comments**: 7 instances (already addressed)
- **Commented dead code**: To be identified
- **Unused imports**: To be checked
- **Temporary files**: To be cleaned

---

## 🔧 **CLEANUP ACTIONS**

### **1. Remove Debug print() Statements**

#### **Files to Clean:**

1. **core/views/laboratorio.py** (3 prints)
   - Line 475: Error logging
   - Line 480: Error logging
   - Line 1880: Debugging

2. **consultorio/views.py** (9 prints)
   - Line 524: Error logging
   - Line 544: Error logging
   - Line 572: Error logging
   - Line 576: Error logging
   - Line 1075: Error logging
   - Line 1092: Error logging
   - Line 1175: Error logging
   - Line 1256: Error logging
   - Line 1333: Error logging

3. **cargar_tarifas.py** (37 prints)
   - This is a management script, prints are OK (for CLI output)

**Action:** Replace `print()` with proper `logging` module

---

### **2. Clean JavaScript console.log()**

#### **Files to Clean:**

1. **laboratorio/templates/laboratorio/captura_resultados_completa.html** (3 logs)
2. **consultorio/templates/consultorio/nueva_consulta_soap.html** (1 log)
3. **consultorio/templates/consultorio/consulta_completa_v2.html** (8 logs)
4. **core/templates/includes/sidebar.html** (1 log)
5. **core/templates/core/recepcion_lab.html** (8 logs)

**Action:** Remove or comment out console.log statements

---

### **3. Clean Temporary/Test Files**

#### **Files to Remove:**
- ✅ `auditoria_modulos.ps1` (temporary audit script)
- ✅ `logs_48h.json` (temporary log file)
- ✅ `logs_errores.json` (temporary log file)
- ✅ Any `__pycache__` outside project structure
- ✅ `.pyc` files in wrong locations

---

## 🎯 **PRIORITY CLEANUP**

### **HIGH PRIORITY:**
1. ✅ Remove print() from production views
2. ✅ Clean console.log() from templates
3. ✅ Remove temporary files

### **MEDIUM PRIORITY:**
4. Check for unused imports
5. Remove commented dead code
6. Fix any remaining linting errors

### **LOW PRIORITY:**
7. Optimize import statements
8. Clean up whitespace
9. Standardize code formatting

---

## 📝 **CLEANUP STRATEGY**

### **Phase 1: Replace print() with logging**

**Before:**
```python
print(f"Error en api_cobrar_orden: {error_details}")
```

**After:**
```python
logger.error(f"Error en api_cobrar_orden: {error_details}")
```

### **Phase 2: Remove console.log()**

**Before:**
```javascript
console.log('✅ Autoguardado exitoso');
```

**After:**
```javascript
// Autoguardado exitoso (removed debug log)
```

### **Phase 3: Clean temp files**

```bash
# Remove temporary files
rm auditoria_modulos.ps1
rm logs_*.json
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -delete
```

---

## ✅ **EXPECTED RESULTS**

### **After Cleanup:**
- ✅ 0 debug print() in production code
- ✅ 0 console.log() in templates
- ✅ Clean codebase
- ✅ Proper logging throughout
- ✅ Professional code quality

---

**Status:** Cleanup in progress...  
**Next Step:** Apply all cleanups and deploy
