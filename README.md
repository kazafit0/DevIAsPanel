# DevIAs Panel

Panel local para **producir videos con IA**: pides un video, tu agente (Claude o Codex) lo piensa y lo arma, tú revisas el borrador, se genera la voz, se graba, se mezcla y se prepara para publicar. Todo corre en tu PC.

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
| [Claude Code](https://claude.com/claude-code) **o** [Codex CLI](https://developers.openai.com/codex/cli) | Atiende tus pedidos desde el panel (eliges cuál en Ajustes) | Sí, uno de los dos |
| Paquetes de Python: `playwright`, `pillow`, `numpy`, `imageio-ffmpeg` | Grabar, imágenes, audio | Sí (el instalador los pone) |
| Chromium de Playwright | Grabar las escenas | Sí (el instalador lo pone) |
| Tarjeta NVIDIA con 6 GB o más | Grabación rápida por GPU y voz local | Recomendado |
| Voces (Piper y Kokoro locales; Jorge por edge-tts) | Generar la voz de los videos | Sí (`python instalar_voces.py` las descarga) |
| Voice Studio (programa aparte) | Usar tus propios perfiles de voz | No, es opcional (se activa en Ajustes → Voz) |

Sin tarjeta NVIDIA el panel funciona igual: graba con el procesador (más lento). Las voces Piper y Kokoro corren en el procesador. En **Ajustes → Tu PC** ves qué detectó tu equipo.

---

## Instalación recomendada: con Claude (guiada)

1. Descarga o clona este repositorio en una carpeta de tu PC (la que prefieras).
2. Abre **Claude Code** en esa carpeta: lee `CLAUDE.md` solo y sigue `SKILL.md` (el skill `devias-panel`); no hace falta activar nada a mano.
3. Claude te recibe con *«Bienvenido al DevIAs Panel…»*. Si aceptas, hace esto, paso a paso:
   1. **Instala las dependencias** (paquetes de Python y Chromium).
   2. **Voces:** ejecuta `python instalar_voces.py`: instala Piper (`es_MX-claude-high`) y Kokoro (`em_alex`, `em_santa`; necesita Node.js 22+) y la voz Jorge de edge-tts (`es-MX-JorgeNeural`), que va por internet y envía el texto a Microsoft. Cada una sale como tarjeta en *Ajustes → Voz*.
   3. **Abre el panel** (`iniciar_devpanel.bat`). La primera vez sale un popup que explica que *Claude manda una señal cada 30 minutos* para mantener el panel conectado; **tú eliges cada cuánto** (queda también en Ajustes).
   4. Al aceptar, el panel queda corriendo y arriba, en **«Claude escuchando»**, ves un reloj ⏱ con el tiempo.

## Instalar y usar con Codex (ChatGPT)
1. Abre **Codex CLI** en la carpeta del panel: lee solo `AGENTS.md`.
2. Escríbele «instala el DevIAs Panel» (instalación guiada).
3. En el panel: **Ajustes → ¿Quién atiende los pedidos? → Codex (ChatGPT)**, y escríbele `devias`.

Para pasar de Claude a Codex (o volver) cuando a uno se le acaba el uso, mira **[GUIA_AGENTES.md](GUIA_AGENTES.md)**.

## Instalación manual (sin Claude)

```bat
python instalar.py --instalar-paquetes
iniciar_devpanel.bat
```

- `python instalar.py --estado` imprime en JSON qué está instalado y qué falta (Python, paquetes, Chromium, voces).
- `python instalar.py --acceso-directo` crea un acceso directo «DevIAs Panel» en el escritorio.
- `detener_devpanel.bat` apaga el panel.
- El puerto por defecto es **8820**; se puede cambiar con `python instalar.py --puerto 8830`.

## Instalar un plugin

1. En el panel: **Plugins → Instalar un plugin** y sube el `.zip` del plugin (o copia su carpeta en `plugins/`).
2. El panel comprueba que cumple el esqueleto (`plugin.json`). Si no cumple, no lo instala.
3. Pulsa **Activar** (solo uno a la vez).

Un plugin trae: ideas, reglas del formato, plantillas, ajustes y su receta de pipeline. Los motores de voz, mezcla y grabación **son del panel**, no del plugin.

---

## La voz de los videos
En **Ajustes → Voz** eliges el motor y la voz (una sola para todos los videos de todos los plugins). Se usa **un motor a la vez**:
- **Voces del panel:** Piper (`es_MX-claude-high`) y Kokoro (`em_alex`, `em_santa`) corren en tu PC; Jorge (edge-tts) va por internet. Cada voz tiene **Escuchar** y **Usar esta voz**; las que subiste se pueden **borrar** (van a `_papelera/voces`).
- **Voice Studio (opcional):** si ya lo usas, pulsa «Voice Studio» → *Activar*, indica su carpeta («Buscar en el PC», lo intenta solo la primera vez) y usa tus perfiles: **se detectan solos** los que ya tienes en Voice Studio, y el botón «Detectar perfiles de voz» vuelve a leerlos si creas uno nuevo. Se enciende y se apaga desde el panel, y se enciende solo al generar voz. Un perfil con audio de referencia de más de 20 s necesita el modelo de voz a texto (Whisper) de Voice Studio; si lo rechaza, el panel muestra el motivo.
- **Configuración general** (velocidad y pausa) al final de la tarjeta, con un solo botón **Guardar configuración**.

## Quién atiende los pedidos (Claude o Codex)
En **Ajustes → ¿Quién atiende los pedidos?** eliges a quién le llegan; el otro queda desactivado. La barra superior muestra siempre «Atiende: Claude» o «Atiende: Codex (ChatGPT)». Para usar Codex o pasar de uno a otro, mira **[GUIA_AGENTES.md](GUIA_AGENTES.md)**.

## Carpeta de temporales

El panel guarda archivos de trabajo (grabación y unión de videos) en una carpeta de temporales. Por defecto es `_tmp` dentro del panel; la eliges en la instalación (`python instalar.py --temp "RUTA"`) y la cambias en **Ajustes → Carpeta de temporales** (se aplica al reiniciar).

## Reconectar: la palabra clave «devias»

Si apagas la PC, cierras el panel o la conversación con Claude se reinicia, escribe **«devias»** en Claude Code: enciende el panel si hace falta, rearma la conexión y atiende los pedidos pendientes.

## Qué es del panel y qué del plugin

El panel **no trae plugins, ideas, listas de países ni claves tuyas**. Cada plugin trae lo suyo (ideas, reglas, diseño y datos en `recursos/`) y el panel lo lee del plugin **activo**. Tus claves (Freesound en el ajuste del plugin) se guardan solo en tu equipo. Voces: Piper y Kokoro, en la carpeta `voces_tts` de tu usuario (o la de `VOCES_TTS_DIR`); la voz por defecto es `es_MX-claude-high` (cámbiala en *Ajustes → Voz*).

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

- **El panel dice «Claude desconectado» (o «Codex desconectado»):** pulsa *Sumar minutos* en Ajustes o escríbele `devias` a tu agente. Si elegiste uno en Ajustes, el otro se muestra desconectado a propósito.
- **«Falta la voz Piper»:** ejecuta `python instalar_voces.py` y vuelve a ejecutar `python instalar.py --estado`.
- **Voice Studio dice que el audio de referencia es muy largo:** ese perfil dura más de 20 s. Recorta el audio a 3-10 s en Voice Studio, o usa otro perfil.
- **Voice Studio dice que no hay modelo de voz a texto:** el panel ya lo enciende con la carpeta `models` de tu Voice Studio; si sigue, instala Whisper desde su Catálogo de modelos.
- **«Escuchar» de Voice Studio tarda:** Voice Studio genera de a una frase; el panel espera y reintenta solo.
- **La grabación va lenta o falla por memoria:** cierra otros programas que usen la tarjeta de video antes de grabar un video largo.
- **No abre en el puerto 8820:** otro programa lo usa; reinstala con otro puerto (`--puerto`).
