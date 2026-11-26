# DevIAs Panel — instrucciones para Codex (ChatGPT)

Este archivo lo lee Codex CLI al abrirse en esta carpeta. Es el equivalente de `SKILL.md` (que escribió Claude): **el panel no depende de ningún agente**; deja los pedidos en `pedidos.json` y quien los atiende los recoge y reporta con `pedido.py`. Lee `SKILL.md` (secciones «Cómo atender», «Motor del DevIAs Panel» y «Contrato del plugin») para el detalle, **ignorando lo que sea de herramientas de Claude** (Monitor, CronCreate, AskUserQuestion): en Codex se reemplaza como indica abajo.

El usuario es hispanohablante: háblale en español sencillo.

## Instalación guiada (primera vez)
**Solo si falta algo:** si `python instalar.py --estado` ya muestra `paquetes_faltan` vacío, `chromium` en true y `voces.instaladas` en true, y `GET http://localhost:8820/api/senal` dice `primer_uso: false`, **ya está instalado: no reinstales** (puede haberlo instalado el otro agente); pasa directo a «devias».
Si el usuario dice «instala el panel» (o `python instalar.py --estado` muestra paquetes que faltan), sigue este guion, **un paso a la vez**, en español sencillo. Donde Claude usaba preguntas con botones, **pregunta en el chat** y espera la respuesta.
1. **Bienvenida:** «Bienvenido al DevIAs Panel. ¿Estás de acuerdo con instalarlo? (sí/no)». Si dice que no, no hagas nada más.
2. **Dependencias:** `python instalar.py --instalar-paquetes` y luego `python instalar.py --estado` (imprime JSON). Cuenta en una línea qué quedó ✔.
3. **Carpeta de temporales:** pregunta dónde guardar los archivos temporales (grabaciones y uniones de video) o si deja la de por defecto (`_tmp` dentro del panel). Guarda la respuesta con `python instalar.py --temp "RUTA"` (si deja la de por defecto, no pases `--temp`).
4. **Voces:** mira `voces.instaladas` en `--estado`. Si faltan: `python instalar_voces.py` (Kokoro necesita Node.js 22+ y `pip install kokoro-onnx soundfile`; la voz Jorge usa internet). Voice Studio es opcional y lo configura el usuario en Ajustes → Voz.
5. **Abrir el panel:** `iniciar_devpanel.bat` (enciende el servidor y abre el navegador). La primera vez sale un popup de bienvenida: el usuario lo acepta.
6. **Elegir a Codex:** dile al usuario que entre a **Ajustes → «¿Quién atiende los pedidos?» → Codex (ChatGPT)**. (Solo si él te lo pide o lo autoriza, puedes hacerlo tú con `POST http://localhost:8820/api/agente` `{"activo": "codex"}`.) Sin este paso los pedidos van a Claude.
7. **Conectar:** haz lo de «devias» (siguiente sección) y di «Listo, el DevIAs Panel está funcionando con Codex».

## Palabra clave: «devias»
Cuando el usuario escriba **«devias»**, haz esto sin preguntar:
1. Comprueba que el panel responde: `GET http://localhost:8820/api/estado`. Si no, pídele abrir `iniciar_devpanel.bat`.
2. **Mira si el panel está dirigido a ti:** `python pendientes.py --soy codex`.
   - Si dice que el panel está dirigido a «claude» **no tomes ningún pedido** y avísale al usuario: puede cambiarlo en el panel (Ajustes → «¿Quién atiende los pedidos?»).
3. Mantén la luz de conexión del panel: en segundo plano `python escucha.py --latido --agente codex` (sin `--agente codex` el panel no lo cuenta como Codex), y renueva el tiempo con `POST http://localhost:8820/api/vivo_tiempo` `{"min": 120}` cada ~25 min (si no, el panel marca «desconectado»).
4. Atiende lo pendiente (siguiente sección). Responde en una línea: «DevIAs Panel conectado · N pedidos libres».

## Cómo atender un pedido
Codex no recibe avisos automáticos: **consulta tú** cuando el usuario te lo pida o termines uno.
- `python pendientes.py --soy codex` → lista los pedidos libres (y los que ya atiende otro).
- `python pendientes.py --soy codex --esperar 600` → espera hasta 10 min a que llegue uno (código de salida 0 = hay, 2 = ninguno, 3 = el panel está dirigido a otro agente).

Para cada pedido libre:
1. **Márcalo como tuyo** en el primer aviso: `python pedido.py IDEA_ID 5 "Codex empezó" --etapa 1 --yo codex`. Añade **siempre `--yo codex`** a cada `pedido.py` (la marca se renueva y caduca a los 20 min sin avisos; así Claude no lo pisa).
2. Lee `plugins/<plugin>/INSTRUCCIONES.md`, `NO_HACER.md` y `memoria.md` **antes de tocar un video** (el pedido trae el nombre del plugin).
3. Avisa el progreso con `pedido.py` (`--etapa N`, `--archivos a.js,b.py`, `--error`, `--cambio "texto" --proyecto ID`; el uso completo está al inicio de `pedido.py`).
4. **Preguntas al usuario:** en vez de preguntar en el chat, usa `python pedido.py IDEA_ID PCT "msg" --pregunta "texto" --opciones "Sí|No" --yo codex` (sale en el panel con la campanita) y espera su respuesta en `pedidos.json` → `respuesta`.
5. Al terminar: `python pedido.py IDEA_ID 100 "Borrador listo" --etapa 8 --hecho --proyecto ID --yo codex`.

Tipos de pedido: `ideas`, `video`, `mejora`, `plugin_mejora`, `resto`, `escena` (ver `SKILL.md`). Los pedidos de video con el plugin «Mapa desastres» se construyen con `plugins/mapa-desastres/motor_historia/construir.py` (spec → proyecto); para correrlo desde aquí pon `DEVPANEL` apuntando a esta carpeta.

## Reglas que NO se rompen
- **La voz y la unión las inicia solo el usuario** (botones del panel). Tú dejas el borrador listo.
- No cambies la voz elegida ni su configuración (Ajustes → Voz).
- No subas nada a git, no borres videos ni voces, no toques carpetas fuera de esta.
- No inventes cifras: los datos de un guion llevan fuente (ver las reglas del plugin).
- Un solo agente a la vez: si `pendientes.py` dice «lo atiende claude», no toques ese pedido.
