# Guía de instalación del DevIAs Panel

El DevIAs Panel es el panel de producción de videos. Se instala en este orden; **no abras el panel hasta que el paso 3 diga que todo está en orden**.

## 1. Qué necesita el equipo
| Qué | Para qué | Cómo se resuelve |
|---|---|---|
| **Python 3.10 o superior** | Corre el panel | Descárgalo de python.org y marca «Add Python to PATH». |
| **Paquetes de Python** (playwright, pillow, numpy, imageio-ffmpeg) | Grabar, imágenes, ffmpeg | `python instalar.py --instalar-paquetes` (lo hace solo). |
| **Chromium del grabador** | Graba los juegos y mapas | Lo instala el comando anterior, o `python -m playwright install chromium`. |
| **Tarjeta de video NVIDIA** (≈6 GB) | La voz y la grabación rápida | Instala los drivers de NVIDIA. Sin ella el panel abre, pero la voz no funciona. |
| **Voces locales (Piper y Kokoro)** | Generan la voz de los videos | Ejecuta `python instalar_voces.py`. Kokoro necesita además Node.js 22+ y `python -m pip install kokoro-onnx soundfile`. |
| **Voice Studio** (opcional) | Usar tus propios perfiles de voz | Programa aparte. Se activa en Ajustes → Voz → Voice Studio; el panel lo enciende y apaga. |
| **Música de fondo** (opcional) | Música bajo la voz | Un mp3 en `musica_fondo/`; se elige en Plugins → Ajustes. |

## 2. Instalar
1. Descomprime el instalador del DevIAs Panel donde quieras (la que prefieras).
2. Doble clic en **`instalar.bat`**. Crea las carpetas, genera `iniciar_devpanel.bat` y `detener_devpanel.bat` y, al terminar, **comprueba los requisitos**.
3. Si falta algo, arréglalo y vuelve a ejecutar `python requisitos.py` hasta que diga **«TODO EN ORDEN»**. Si solo falta lo de voz/video, el panel abre pero no podrás generar voz ni grabar.

## 3. Abrir el panel = activar todo
Doble clic en **`iniciar_devpanel.bat`** (abre `http://localhost:8820/static/admin.html`). Al encender el panel se activa todo lo que depende de él:
- **El servidor del panel** y su vista.
- **Voces**: no hay nada que encender; Piper y Kokoro se ejecutan solo cuando generas la voz de un video. Voice Studio (opcional) se enciende solo al generar con él.
- **El grabador** (Chromium) queda listo para usarse; arranca cuando grabas un borrador.
- **Lo único que no arranca solo es la conexión con tu agente (Claude o Codex)**: se hace una vez por conversación escribiendo `/devpanel` (paso 4).

Para apagarlo todo: `detener_devpanel.bat`. El panel arranca **sin plugins**: instala los formatos de video desde la pestaña **Plugins** (un `.zip` por formato); el panel revisa que cumplan su estructura y no instala los que no.

## 4. Conectar con Claude
Con el skill **`devpanel`** activado en la conversación, Claude se conecta solo (latido + escucha) y atiende los pedidos que mandes desde el panel. Si la conversación se reinicia, vuelve a escribir `/devpanel`.
