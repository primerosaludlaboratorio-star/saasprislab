## 🔴 SOLUCIÓN AL ERROR DE REDIRECCIONES INFINITAS

### **PROBLEMA IDENTIFICADO:**

El bucle de redirección ocurre porque:
1. La ruta `/` → `CustomLoginView`
2. Después del login → redirige a `/home/`
3. `/home/` → `views.pdv_farmacia` (tiene `@login_required`)
4. Si algo falla → redirige a `/login/`
5. **BUCLE INFINITO**

---

### **SOLUCIÓN RÁPIDA:**

**Accede directamente al Admin Panel para hacer login:**

```
http://127.0.0.1:8000/admin/
```

**Credenciales:**
- Usuario: `admin`
- Password: `admin123`

**Después del login en admin, accede a:**
```
http://127.0.0.1:8000/laboratorio/captura/2/
```

---

### **SOLUCIÓN PERMANENTE (Implementar):**

Necesitamos crear una vista `home` sin `@login_required` que redirija según el estado de autenticación:

**Archivo: `core/views/general.py`**

```python
def home_view(request):
    """Vista de inicio que redirecciona según autenticación."""
    if request.user.is_authenticated:
        return redirect(get_redirect_url_by_role(request.user))
    else:
        return redirect('login')
```

**Actualizar `config/urls.py`:**

```python
# Cambiar línea 21 de:
path('home/', views.pdv_farmacia, name='home'),

# A:
path('home/', views.home_view, name='home'),
```

---

### **ALTERNATIVA: Acceso Directo (SIN LOGIN)**

Si quieres ver la interfaz de captura sin autenticación (solo para desarrollo):

1. Comenta temporalmente el decorador `@login_required` en:
   - `core/views/laboratorio_captura_v2.py`

2. Accede directamente a:
   ```
   http://127.0.0.1:8000/laboratorio/captura/2/
   ```

---

### **ACCIÓN INMEDIATA:**

**USA EL ADMIN PANEL PARA LOGIN:**
```
http://127.0.0.1:8000/admin/
```

Este panel tiene su propio sistema de autenticación de Django y no causará bucles.
