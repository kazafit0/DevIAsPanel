---
name: devias-panel
description: DevIAs Panel (http://localhost:8820) — el panel de producción de videos con IA. El PANEL es el skill de Claude; los formatos de video (p. ej. «mapas-interactivo») son PLUGINS que se enchufan al panel. Úsalo cuando el usuario diga la PALABRA CLAVE «devias» (o «/devias-panel», «activa devias», «conecta el panel»), «devias panel», «el panel», «plugin», cuando quiera INSTALAR el panel, o cuando lleguen pedidos del panel (escucha.py).
---

# DevIAs Panel = el skill · los plugins se enchufan a él

**El panel es el skill.** Trae el motor común (pedidos, cola, grabador, voces, publicar/títulos, memoria, avisos). **Cada formato de video es un plugin** (`plugins/<id>/` con su `plugin.json`): las IDEAS, el guion, el diseño y las reglas de cada video son del plugin, no del panel. Solo hay una vista del panel (la v2, `static/admin.html`).

## INSTALACIÓN GUIADA (primera vez): sigue EXACTAMENTE este guion
Habla en español sencillo, un paso a la vez, y no avances hasta cumplir el anterior.
1. **Bienvenida (siempre lo primero).** Escribe: «**Bienvenido al DevIAs Panel.** Si estás de acuerdo con instalar este skill, dale clic en «Sí, instalar».» y ofrece las opciones «Sí, instalar» / «No ahora» (usa AskUserQuestion). Si dice que no, no hagas nada más.
2. **Dependencias.** Di «Estoy instalando las dependencias que se necesitan…». Ejecuta `python instalar.py --instalar-paquetes` (instala Python 3.10+ si falta avisando al usuario, los paquetes `playwright pillow numpy imageio-ffmpeg` y Chromium). Cuenta en una línea qué quedó ✔ (usa `python instalar.py --estado`, que imprime JSON).
2b. **Carpeta de temporales (pregúntalo SIEMPRE).** Pregunta: «¿Dónde quieres que el panel guarde sus archivos temporales (grabaciones y uniones de video)? Elige una carpeta con buen espacio libre, o déjalo en la de por defecto (`_tmp` dentro del panel).» Guarda la respuesta con `python instalar.py --temp "RUTA"` (si deja la de por defecto, no pases `--temp`). Dile que después lo puede cambiar en **Ajustes → Carpeta de temporales**.
3. **Voice Studio (lo instala el usuario a mano).** Mira `voice_studio.instalado` en `--estado`. Si falta, di: «**Para instalar Voice Studio necesito que lo hagas manualmente.** Cuando termines, escribe «Instalado».» y ESPERA a que escriba «Instalado» (no lo intentes instalar tú). Luego vuelve a ejecutar `--estado` y confirma. Si ya estaba, dilo y sigue.
4. **Abrir el panel.** Ejecuta `iniciar_devpanel.bat` (enciende el servidor y abre el navegador). La primera vez el panel muestra un **popup de bienvenida** que explica que Claude manda una **señal cada 30 minutos** (el usuario puede elegir otro tiempo; queda en Ajustes → Conexión con Claude). Espera a que el usuario lo acepte (`GET /api/senal` → `primer_uso: false`).
5. **Conectar.** Lee `senal_min` de `GET /api/senal` y arma la conexión (sección siguiente). El panel queda corriendo con un **reloj** (⏱ mm:ss) en el chip «Claude escuchando» de la parte superior. Di «Listo, el DevIAs Panel está funcionando» y termina la instalación.

## PALABRA CLAVE: «devias» (para reactivar el panel cuando se apaga y se prende)
Cuando el usuario escriba **«devias»** (o `/devias-panel`, «activa devias», «conecta el panel»), haz esto sin preguntar:
1. Si el panel no responde en `http://localhost:8820/api/estado`, **enciéndelo** (`iniciar_devpanel.bat`; si el servidor no sube en ~15 s, dile al usuario qué falló) y espera a que responda.
2. Si Voice Studio está cerrado y el usuario va a generar voz, dilo (el panel lo enciende solo al iniciar).
3. Re-arma la conexión: Monitor `python -u escucha.py` + la tarea de señal cada `senal_min` minutos (sección siguiente) y renueva el tiempo (`POST /api/vivo_tiempo`).
4. Lee `pedidos.json` y atiende lo pendiente. Responde en una línea: «DevIAs Panel conectado · señal cada N min · N pedidos pendientes».
Esta palabra sirve igual después de apagar y prender la PC, tras compactar la conversación o cuando el reloj del panel diga «Claude desconectado».

## Al activarte (ARRANQUE AUTOMÁTICO: hazlo tú, sin que el usuario te lo pida)
1. Localiza la carpeta del panel (la que tiene `servidor.py`, `escucha.py`, `pedidos.json`) y trabaja desde ahí.
2. Comprueba `GET http://localhost:8820/api/estado`. Si no responde, pide al usuario abrir `iniciar_devpanel.bat`.
3. **Monitor:** `python -u escucha.py` como Monitor (timeout 1800000).
4. **Señal cada `senal_min` minutos** (el valor de `/api/estado`, por defecto 30; el usuario lo cambia en Ajustes): crea una tarea recurrente (CronCreate, p. ej. `*/10`) que (a) hace `POST /api/vivo_tiempo {"min": senal_min}`, (b) si `claude_monitor.json` tiene el latido viejo (>15 s), re-arma el Monitor. Así el panel nunca marca «desconectado» y el usuario no tiene que pedirte reconectar. Dura mientras la sesión esté abierta (30 días máximo).
5. Lee `pedidos.json`: atiende todo pedido «pendiente».
6. Tras compactar o reanudar la conversación, repite 3 y 4. El panel NO usa ningún id de chat: deja pedidos en `pedidos.json` y tú los recoges.

## Cómo atender
1. Mantén conectado el panel: `python escucha.py --latido` (fondo) + Monitor `python -u escucha.py`. Cada pedido llega con su tipo:
   - `ideas`, `video`, `mejora` → trabajo del panel/plugin activo.
   - `plugin_mejora` (idea `plugin:<id>`) → mejorar **solo** ese plugin: copia en `_backups`, cambiar solo `plugins/<id>/`, `plugin.json` debe seguir cumpliendo el esqueleto y subir `version`.
2. Lee `plugins/<id>/INSTRUCCIONES.md` (reglas del formato) y `NO_HACER.md`/`memoria.md` antes de tocar un video.
3. Informa siempre en el panel: `python pedido.py --etapa/--cambio/--pregunta/--error` (las preguntas y bloqueos salen en la campanita, no solo en el chat).
4. La voz y la unión las inicia **solo el usuario**.

## Motor del DevIAs Panel (voz, mezcla, render, unión) — NO es de los plugins
- `motor/video.py` = biblioteca común de los pipelines (grabar, voz, música, mezclar, unir, registrar, avance). `motor/voz_partes.py` = la voz (config en Ajustes → Voz, `voz_config.json`). `motor/mezcla.py` = la mezcla por escenas (lee `escenas.json`, `sfx_plan.json`, `sfx_cues.json`, `music/`). `grabador/` = el render (GPU + trabajadores en paralelo; `GRAB_MODO=pagina` para escenas con HUD en HTML).
- **Flujo único** (`motor/pipeline.py`, el de Mapas): borrador con tiempos estimados → voz real → regrabar con los tiempos reales → unir por escenas. El pipeline de un plugin es solo una «receta» (`pipeline.correr({archivos, preparar, tras_tiempos, escenas, grabacion})`).
- **Configuración por video** (`plugin.json → config_video`, opcional): lo que el plugin pide en Ideas (modal «Díselo a Claude») para CADA video: `paises` (países que juegan), `interruptor` (p. ej. modo equipos), `equipos` (quién contra quién), `opcion`, `numero`. Llega en la nota del pedido («CONFIGURACIÓN DE ESTE VIDEO…») y en `pedidos.json → config_video`. No repite los ajustes globales del plugin.
- **Regla de tiempos** (`plugin.json → tiempos`, API 2): `guion` = la escena se adapta a los tiempos del guion (Mapas, Carreras); `juego` = el juego marca sus segundos y no se estima ni se regraba (Juegos, por ahora). `pagina` lista los archivos donde la página expone `__ready, __frame, __adv, __sim, __cues, __log`; el verificador lo comprueba.
- Un plugin NO puede traer scripts de voz, mezcla, render o unión (el verificador lo rechaza). Su `pipeline` es solo la «receta» que llama a `motor/video.py`; su `plugin.json` declara `voz.modo` = `json_manda` (cada parte cae en su segundo `t`) o `libre` (partes seguidas, tiempos reales de la voz).
- La música de fondo es un ajuste del plugin (`musica_archivo`, `musica_ganancia`); los efectos son datos del video (`sfx/`, `sfx_plan.json`, `sfx_cues.json`).

## Contrato del plugin (`plugin.json`, esquema 1, API del panel 1)
Campos obligatorios: `esquema`, `api`, `id` (= nombre de carpeta), `nombre`, `version`, `descripcion`, `instrucciones`, `formatos`, `pipeline`, `voz`, `titulos`, `requisitos`, `ajustes` (cada uno con `ayuda`). Opcionales: `ideas`, `plantillas`, `memoria`. El panel pone `short 9:16` / `largo 16:9` y la duración; el plugin no decide eso.
Los scripts del plugin reciben `DEVPANEL`, `PLUGIN_DIR`, `PLUGIN_AJUSTES` (JSON) y `DEVPANEL_TMP`.

## Ciclo de vida (pestaña Plugins)
- **Instalar**: subir un `.zip` con `plugin.json` (`POST /api/plugin_instalar_zip`). Si no cumple el esqueleto se deshace todo. Si ya existe, ofrece **actualizar** (la versión anterior va a `_papelera/`).
- **Activar/Desactivar**: solo uno a la vez (`/api/plugin_activar`).
- **Configurar** (subpanel de ajustes) y **Mejorar este plugin** (llega a Claude como `plugin_mejora`).
- **Desinstalar**: nunca estando activo; va a `_papelera/` (recuperable) (`/api/plugin_desinstalar`).
- **Descargar** el plugin: `/api/plugin_zip?id=…`. **Instalador del panel**: `instalar.bat` genera `iniciar_devpanel.bat` y `detener_devpanel.bat`.

## Reglas
- Trabaja sobre copias y haz backup en `_backups` antes de cambios grandes.
- Todo cambio que llega a un borrador se avisa (campanita) y se anota con `--cambio`.
- **Dos agentes del cerebro** (`plugin.json → agentes.modulo`, opcional): el panel los corre al pedir un video («Díselo a Claude» y «Rehacer todo»). **Agente de formato** = trae el mejor formato para la idea (tipo de inicio, forma, duración, estructura); **agente de diseño** = trae el mejor diseño gráfico del juego (fondo, paleta, estilo, peligro estrella). Recuerdan lo ya usado (`agentes_historial.json`) para no repetirse y evitan lo de la versión anterior. Su propuesta llega en la nota del pedido y en `pedidos.json → agentes`. **Al empezar un video lanza DOS subagentes en paralelo (uno de formato y uno de diseño) para refinarlos** y deja lo que traen con `pedido.py IDEA PCT "msg" --agente formato|diseno "texto" [--estado pensando|listo]`: sale en el cerebro del panel (órbitas y tarjetas). El pipeline del plugin usa sus decisiones cuando los ajustes están en «automático».
- **Rehacer todo** (botón en el video, `/api/rehacer_todo`): archiva la versión anterior en `_papelera/videos`, vuelve el video a EN ESPERA y lo manda otra vez por el cerebro: genera una versión NUEVA y distinta (otro inicio y diseño) con el motor actualizado, conservando la idea y la configuración.
- **Trabajos recientes**: todo lo que se reporta con `pedido.py` (también desde los pipelines de cualquier plugin) aparece solo en la pestaña Trabajos (`/api/trabajo_externo`). Un plugin nuevo debe avisar su avance con `pedido.py IDEA PCT "mensaje" [--proyecto ID] [--hecho|--error]`; los botones del panel (voz, unión, regrabar) ya salen siempre.
- Panel de mapas (8810) y de juegos (8800) siguen intactos; el DevIAs Panel es el nuevo.
