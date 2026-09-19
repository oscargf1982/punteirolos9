# Punteirolos 9.0 — FPL Stats 2026/27 ⚽

Web automática de estadísticas para la liga fantasy privada Punteirolos, temporada 2026/27.

**Liga FPL:** #42303

---

## 📁 Archivos del repo

| Archivo | Para qué sirve |
|---------|---------------|
| `template.html` | Plantilla de la web (no editar) |
| `generate_9.py` | Script Python que genera el index.html |
| `splash.png` | Imagen que aparece al abrir la web (opcional) |
| `.github/workflows/update.yml` | Automatización semanal |
| `index.html` | Generado automáticamente, no subir |

---

## 🚀 Configuración inicial

### 1. Crear el repo en GitHub
- Nombre: `punteirolos9` (o el que quieras)
- Visibilidad: **Public**

### 2. Subir estos archivos
- `template.html`
- `generate_9.py`
- `splash.png` (la imagen que aparece al abrir)
- `README.md`
- `.github/workflows/update.yml` ← ojo con la carpeta oculta

### 3. Permisos de Actions
Settings → Actions → General → **Read and write permissions** → Save

### 4. Primera ejecución
Actions → "Actualizar Punteirolos 9.0" → **Run workflow**
Espera 2-3 minutos ✅

### 5. Activar GitHub Pages
Settings → Pages → Branch: **gh-pages** → Save

### 6. Tu URL
```
https://oscargf1982.github.io/punteirolos9/
```

---

## 🔄 Actualización automática

Cada **lunes a las 10:00 UTC** el script:
1. Llama a la API de FPL y descarga resultados
2. Regenera el `index.html`
3. Lo publica en GitHub Pages

También puedes ejecutarlo manualmente desde Actions → Run workflow.

---

## ⚠️ Si el workflow falla

La API de FPL a veces tiene restricciones temporales.
Vuelve a ejecutarlo más tarde desde Actions → Run workflow.
