# free · plugins gratis

Aquí se publicarán, más adelante, los **plugins gratuitos** del DevIAs Panel.

## Cómo se usará
1. Descarga el plugin que quieras de esta carpeta (cada plugin es una carpeta con su `plugin.json`, o un `.zip`).
2. En el panel: **Plugins → Instalar un plugin** y sube el `.zip` (o copia la carpeta dentro de `plugins/`).
3. Pulsa **Activar**. El panel comprueba que cumple el esqueleto antes de instalarlo.

## Qué trae cada plugin
Sus ideas, sus reglas de guion, su diseño y sus datos (`recursos/`). Los motores de voz, mezcla y grabación son del panel.

## Disponibles
| Archivo | Qué es |
|---|---|
| **DevIAs Religion Pluggin v1.1.zip** | Plugin de reels bíblicos 9:16 «¿Sabías que…?» (datos exactos con cita, siluetas con borde dorado, contadores, barra de suma, subtítulo con caja azul). La voz la pone el panel (Piper/Kokoro). |
| **DevIAs Esqueleto Pluggin.zip** | **No es un plugin y no se instala.** Es la base para construir plugins nuevos, con su guía para crearlos y mejorarlos (`GUIA_CREAR_Y_MEJORAR_PLUGIN.md`), un generador y un verificador. |

Para instalar el de Religión: **Plugins → Instalar un plugin** y sube el `.zip`. Para el esqueleto: descomprímelo dentro de la carpeta del panel y sigue su `LEEME.md`.

---

## Cómo usar el esqueleto para crear tu propio plugin
> El esqueleto **no es un plugin y no se instala**: es la base de la que se parte. La guía completa está en [`GUIA_CREAR_Y_MEJORAR_PLUGIN.md`](GUIA_CREAR_Y_MEJORAR_PLUGIN.md) (también viene dentro del zip).

**Necesitas:** el DevIAs Panel **encendido** (puerto 8820) y Python. Todos los comandos se ejecutan **desde la carpeta del panel** (donde está `servidor.py`).

1. **Descomprime** `DevIAs Esqueleto Pluggin.zip` dentro de la carpeta del panel: aparece `esqueleto-plugin/`.
2. **Crea tu plugin** (id en minúsculas, números y guiones; luego el nombre que verá el usuario):
   ```
   python esqueleto-plugin/crear_plugin.py mi-plugin "Mi plugin"
   ```
   Crea `plugins/mi-plugin/` **ya válido**, lo verifica con el panel y construye un video de ejemplo que puedes ver en `http://localhost:8820/series/zz_mi_plugin_prueba/index.html?play=1` (bórralo después: `series/zz_mi_plugin_prueba`).
3. **Hazlo tuyo:** rellena `INSTRUCCIONES.md`, `DISENO.md`, `NO_HACER.md` y `referencia.md` (todo lo que está entre `‹ ›`), cambia `motor/motor.js` por tu estilo real, escribe ideas reales en `ideas/` y una ficha de ejemplo en `specs/`.
4. **Verifica** hasta que diga **✔ LISTO**:
   ```
   python esqueleto-plugin/verificar_plugin.py mi-plugin
   ```
5. **Empaqueta** el zip para compartirlo o instalarlo:
   ```
   python esqueleto-plugin/verificar_plugin.py mi-plugin --zip
   ```
6. **Instálalo** en el panel: **Plugins → Instalar un plugin** y sube `mi-plugin-v0.1.0.zip`.

**Para mejorarlo después:** corrige en el plugin (no solo en un video), anota la regla en `NO_HACER.md`, y sube la versión y empaqueta:
```
python esqueleto-plugin/verificar_plugin.py mi-plugin --subir patch --nota "qué cambió" --zip
```
(`patch` = arreglo, `minor` = función nueva compatible, `major` = rompe fichas anteriores).

**Qué hace cada pieza**
| Pieza | Para qué |
|---|---|
| `crear_plugin.py` | Genera el plugin desde la plantilla y lo deja válido |
| `verificar_plugin.py` | Verifica (panel + revisión propia), sube la versión y empaqueta |
| `plantilla/` | El plugin de demostración con marcadores que se reemplazan al crear |
| `GUIA_CREAR_Y_MEJORAR_PLUGIN.md` | Anatomía, `plugin.json` campo por campo, contratos, método, checklist y errores típicos |

**Reglas que conviene saber desde el principio**
- El plugin aporta la **escena, el guion, las ideas y los títulos**; la **voz (Piper/Kokoro), la mezcla y el render son del panel**. Un plugin con `voz_*.py`, `mix*.py`, `grab*.py` o `unir.py` se rechaza.
- La voz solo se genera cuando el usuario dice **«Estoy conforme»**.
- **Windows:** no dejes tu terminal con la carpeta de un plugin como carpeta actual (impide que el panel lo mueva y lo deja vacío). Usa rutas absolutas.
- Nunca pongas claves, tokens ni rutas de tu equipo dentro de un plugin: se comparte como `.zip`.
