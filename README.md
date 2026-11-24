# DevIAs Panel

Panel local para **producir videos con IA**: pides un video, Claude lo piensa y lo arma, tú revisas el borrador, se genera la voz, se graba, se mezcla y se prepara para publicar. Todo corre en tu PC.

- El **panel** pone el motor: pedidos, ideas, borrador, voz, grabación, mezcla, publicación, memoria y avisos.
- Cada **formato de video es un plugin** (`plugins/<id>/`): trae sus propias ideas, reglas de guion y diseño. Sin plugin no hay formato de video que producir.
- Solo hay **una vista** (la v2) en `http://localhost:8820`.

> 📖 Cómo se usa cada pantalla: **[GUIA_DE_USO.md](GUIA_DE_USO.md)** (también está dentro del panel, en el menú **Guía**).

---

## Requisitos

| Qué | Para qué | Obligatorio |
|---|---|---|
| Windows 10 u 11 | El panel y sus `.bat` están hechos para Windows | Sí |
| Python 3.10 o superior | Servidor del panel y motor de video | Sí |
| [Claude Code](https://claude.com/claude-code) | Claude atiende tus pedidos desde el panel | Sí |
| Paquetes de Python: `playwright`, `pillow`, `numpy`, `imageio-ffmpeg` | Grabar, imágenes, audio | Sí (el instalador los pone) |
| Chromium de Playwright | Grabar las escenas | Sí (el instalador lo pone) |
| Tarjeta NVIDIA con 6 GB o más | Grabación rápida por GPU y voz local | Recomendado |
| Voice Studio (voz local) | Generar la voz con tu perfil | Recomendado (se instala **a mano**) |

Sin tarjeta NVIDIA el panel funciona igual: graba con el procesador y usa la voz de Hugging Face (más lento). En **Ajustes → Tu PC** ves qué detectó tu equipo.

---

## Instalación recomendada: con Claude (guiada)

1. Descarga o clona este repositorio en una carpeta de tu PC (la que prefieras).
2. Abre **Claude Code** en esa carpeta y activa el skill **`devias-panel`** (el archivo `SKILL.md`).
3. Claude te recibe con *«Bienvenido al DevIAs Panel…»*. Si aceptas, hace esto, paso a paso:
   1. **Instala las dependencias** (paquetes de Python y Chromium).
   2. **Voice Studio:** si no lo tienes, te pide que lo instales **manualmente**. Cuando termines escríbele **«Instalado»** y sigue.
   3. **Abre el panel** (`iniciar_devpanel.bat`). La primera vez sale un popup que explica que *Claude manda una señal cada 30 minutos* para mantener el panel conectado; **tú eliges cada cuánto** (queda también en Ajustes).
   4. Al aceptar, el panel queda corriendo y arriba, en **«Claude escuchando»**, ves un reloj ⏱ con el tiempo.

## Instalación manual (sin Claude)

```bat
python instalar.py --instalar-paquetes
iniciar_devpanel.bat
```

- `python instalar.py --estado` imprime en JSON qué está instalado y qué falta (Python, paquetes, Chromium, Voice Studio).
- `python instalar.py --acceso-directo` crea un acceso directo «DevIAs Panel» en el escritorio.
- `detener_devpanel.bat` apaga el panel.
- El puerto por defecto es **8820**; se puede cambiar con `python instalar.py --puerto 8830`.

## Instalar un plugin

1. En el panel: **Plugins → Instalar un plugin** y sube el `.zip` del plugin (o copia su carpeta en `plugins/`).
2. El panel comprueba que cumple el esqueleto (`plugin.json`). Si no cumple, no lo instala.
3. Pulsa **Activar** (solo uno a la vez).

Un plugin trae: ideas, reglas del formato, plantillas, ajustes y su receta de pipeline. Los motores de voz, mezcla y grabación **son del panel**, no del plugin.

---

## Carpeta de temporales

El panel guarda archivos de trabajo (grabación y unión de videos) en una carpeta de temporales. Por defecto es `_tmp` dentro del panel; la eliges en la instalación (`python instalar.py --temp "RUTA"`) y la cambias en **Ajustes → Carpeta de temporales** (se aplica al reiniciar).

## Reconectar: la palabra clave «devias»

Si apagas la PC, cierras el panel o la conversación con Claude se reinicia, escribe **«devias»** en Claude Code: enciende el panel si hace falta, rearma la conexión y atiende los pedidos pendientes.

## Qué es del panel y qué del plugin

El panel **no trae plugins, ideas, listas de países ni claves tuyas**. Cada plugin trae lo suyo (ideas, reglas, diseño y datos en `recursos/`) y el panel lo lee del plugin **activo**. Tus claves (Freesound en el ajuste del plugin, token de Hugging Face en *Ajustes → Voz*) se guardan solo en tu equipo. Voice Studio: se detecta solo o con `VOICESTUDIO_DIR` / `voice_studio_dir` en `devpanel.json`; el perfil de voz por defecto es `MI VOZ` (cámbialo en *Ajustes → Voz*).

## Estructura del repositorio

```
servidor.py            servidor del panel (API + vista v2)
static/                vista del panel (admin.html, admin_nuevo.js, guía)
motor/                 voz, mezcla, grabación, flujo único de producción
grabador/              grabación por GPU en paralelo
plugins/               formatos de video instalados (cada uno con plugin.json)
free/                  plugins gratuitos para descargar (se irán publicando aquí)
escucha.py pedido.py   cómo hablan el panel y Claude (archivos JSON)
instalar.py            instalador (+ --estado)
SKILL.md               skill de Claude: instalación guiada y atención de pedidos
GUIA_DE_USO.md         guía de uso de todo el panel
```

Los datos de trabajo (`series/`, `catalogo.json`, `pedidos.json`, claves, copias) **no se suben** a Git (ver `.gitignore`).

## Problemas frecuentes

- **El panel dice «Claude desconectado»:** pulsa *Sumar minutos* en Ajustes o dile a Claude «conéctate». Si usas el skill, Claude renueva la señal solo.
- **«Falta Voice Studio»:** instálalo a mano y vuelve a ejecutar `python instalar.py --estado`.
- **La grabación va lenta o falla por memoria:** en Ajustes → *Memoria para grabar* pulsa **Liberar memoria** (apaga Voice Studio) antes de grabar un video largo.
- **No abre en el puerto 8820:** otro programa lo usa; reinstala con otro puerto (`--puerto`).
