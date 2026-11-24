# Guía para CREAR y MEJORAR un plugin del DevIAs Panel

> Esta guía acompaña al **esqueleto de plugins** (`esqueleto-plugin/`). El esqueleto **no es un plugin y no se instala**: es la base de la que se parte para construir plugins nuevos. Está pensada para una persona o para Claude: todo lo que hay que saber está aquí o en los archivos de la plantilla.

## Índice
1. [Qué es un plugin y qué hace el panel por él](#1-qué-es-un-plugin-y-qué-hace-el-panel-por-él)
2. [Inicio rápido (5 pasos)](#2-inicio-rápido-5-pasos)
3. [Anatomía de un plugin](#3-anatomía-de-un-plugin)
4. [`plugin.json` campo por campo](#4-pluginjson-campo-por-campo)
5. [Los contratos: página, constructor, pipeline, ideas, títulos, ajustes](#5-los-contratos)
6. [Cómo llega un pedido y cómo se contesta](#6-cómo-llega-un-pedido-y-cómo-se-contesta)
7. [CREAR un plugin (método paso a paso)](#7-crear-un-plugin-método-paso-a-paso)
8. [MEJORAR un plugin (ciclo y reglas)](#8-mejorar-un-plugin-ciclo-y-reglas)
9. [Lista de verificación antes de entregar](#9-lista-de-verificación-antes-de-entregar)
10. [Instalar, actualizar y desinstalar](#10-instalar-actualizar-y-desinstalar)
11. [Errores típicos y su solución](#11-errores-típicos-y-su-solución)
12. [Lecciones aprendidas](#12-lecciones-aprendidas)

---

## 1. Qué es un plugin y qué hace el panel por él
Un **plugin** es una carpeta dentro de `plugins/` que enseña al DevIAs Panel a producir **un tipo de video** (un estilo: mapas, juegos, óleo, reels bíblicos…). Se distribuye como `.zip`.

| Lo hace el PLUGIN | Lo hace el PANEL (el plugin NO lo trae) |
|---|---|
| La **escena**: la página (canvas) que se graba y su estilo visual | **Grabar** (GPU, trabajadores en paralelo, borrador 20 fps, final 30 fps, regrabar un tramo) |
| El **guion** (reglas, estructura, tono) y la **ficha** de cada video | **Voz** (Voice Studio), partes, tiempos reales |
| Las **ideas** que se ofrecen al usuario | **Mezcla**, música de fondo, efectos, unión |
| Los **títulos, descripciones y etiquetas** | **Registro** del video, progreso, pestañas, cola de pedidos |
| Los **ajustes** del subpanel y sus reglas (`INSTRUCCIONES.md`, `NO_HACER.md`…) | **Verificar** el plugin y decidir si se puede instalar |

Por eso el verificador **rechaza** un plugin que traiga `voz_*.py`, `mix*.py`, `grab*.py`, `unir.py`… y una carpeta `voz/`.

## 2. Inicio rápido (5 pasos)
1. **Crear:** `python esqueleto-plugin/crear_plugin.py mi-plugin "Mi plugin"` → crea `plugins/mi-plugin/` ya válido y construye un video de ejemplo.
2. **Mirar el ejemplo:** `http://localhost:8820/series/zz_mi_plugin_prueba/index.html?play=1` (después bórralo: `series/zz_mi_plugin_prueba`).
3. **Rellenar** `INSTRUCCIONES.md`, `DISENO.md`, `NO_HACER.md`, `referencia.md` (todo lo que está entre `‹ ›`) y **cambiar** `motor/motor.js` por el estilo real.
4. **Verificar:** `python esqueleto-plugin/verificar_plugin.py mi-plugin` (repite hasta que diga ✔ LISTO).
5. **Empaquetar:** `python esqueleto-plugin/verificar_plugin.py mi-plugin --zip` → `plugins/mi-plugin-v0.1.0.zip`, listo para instalar desde la pestaña **Plugins**.

> **Windows:** no dejes tu terminal con la carpeta de un plugin como carpeta actual. Eso impide que el panel mueva o desinstale el plugin (copia los archivos a la papelera y **deja la carpeta vacía**, y el panel dice «falta plugin.json»). Usa siempre rutas absolutas.

## 3. Anatomía de un plugin
```
plugins/mi-plugin/
├─ plugin.json                 ← la FICHA (obligatoria): lo que el panel lee para todo
├─ INSTRUCCIONES.md            ← método y reglas para Claude (obligatoria, la declara plugin.json)
├─ DISENO.md · NO_HACER.md · memoria.md · referencia.md     ← reglas, lo que no se hace, memoria, referencias
├─ base/                       ← la PÁGINA que se graba
│   ├─ index.html              ← canvas #cv (2D) y/o #gl (WebGL); __W__ y __H__ los rellena el constructor
│   ├─ game_head.js            ← lienzo, reloj VT, carga de tiempos
│   └─ game_tail.js            ← dibuja cada fotograma + los ganchos __ready/__frame/__adv/__sim/__cues/__log
├─ motor/motor.js              ← TODO lo que se dibuja (el estilo del plugin)
├─ motor_<id>/construir.py     ← CONSTRUCTOR: ficha .json → carpeta series/ID lista para el panel
├─ pipeline/pipeline_<id>.py   ← RECETA del flujo (qué archivos dibujan, cómo armar game.js)
├─ ideas/ideas_<id>.py         ← mas_ideas() e ideas_de()
├─ titulos/titulos_<id>.py     ← generar()
├─ specs/ejemplo.json          ← una ficha de ejemplo que SIEMPRE debe construir
└─ (opcional) agentes/agentes_<id>.py · imagen.png (portada)
```
**Cómo se arma un video:** `construir.py` junta `motor/motor.js + game_head.js + la ficha (SPEC) + game_tail.js` en `series/ID/game.js`, escribe `index.html`, `guion/1.json` (cada frase con su segundo estimado) y `proyecto.json`. El panel graba esa página.

## 4. `plugin.json` campo por campo
Todos los campos marcados «obligatorio» los comprueba el verificador (`/api/plugin_verificar`). **No admite comentarios** (es JSON).

| Campo | ¿Obl.? | Qué va |
|---|---|---|
| `esquema` | sí | `1` |
| `api` | sí | `2` (la versión de la API de plugins que ofrece este panel; si el panel sube de versión, el plugin debe actualizarse) |
| `id` | sí | = nombre de la carpeta; minúsculas, números y guiones |
| `nombre` · `version` · `descripcion` | sí | lo que ve el usuario; `version` = `x.y.z` |
| `autor` · `licencia` | recomendado | y atribución de todo lo que reutilices |
| `instrucciones` | sí | `INSTRUCCIONES.md` (debe existir) |
| `reglas` · `referencias` · `memoria` | recomendado | archivos `.md` (todos los declarados deben existir) |
| `formatos` | sí | `["short"]`, `["largo"]` o ambos. **El panel define aspecto y duraciones:** short 9:16 = 30·45·60·80·105·120 s; largo 16:9 = 210·240·300 s |
| `tiempos` | sí | `"guion"` (la escena se adapta a los tiempos del guion: borrador estimado → voz real → regrabar; **el flujo recomendado**) o `"juego"` (el juego marca sus segundos y el guion se escribe desde sus eventos) |
| `pagina` | sí | lista de archivos donde la página expone los ganchos (`base/game_head.js`, `base/game_tail.js`, `base/index.html`) |
| `voz` | sí | `{"modo": "json_manda"}` (cada frase del guion cae en su segundo) o `"libre"`. **Nada de `voz.script`** |
| `pipeline` | sí | `{borrador, voz, unir, tramo, script}`; `borrador` es obligatorio y `script` apunta al `.py` (debe compilar) |
| `ideas` | sí | `{modulo, tipos[]}` → el módulo define `mas_ideas` e `ideas_de` |
| `titulos` | sí | `{dir, tipos: {tipo: modulo}}` → cada módulo define `generar(pid, f, lote, usados, largo)` |
| `guion` | recomendado | `{gancho_segundos, sin_decir[], publico, formato, tono, modos}` |
| `plantillas` | recomendado | `{dir, motor, base}` (rutas que deben existir) |
| `requisitos` | sí | `{python[], servicios[], archivos[]}`: los paquetes, servicios (`voice-studio`) y **archivos que el plugin necesita (todos deben existir)** |
| `ajustes` | sí | lista del subpanel (sección 5.6) |
| `config_video` | opcional | campos que se piden EN IDEAS para cada video (sección 5.7) |
| `agentes` | opcional | `{"modulo": "agentes/agentes_<id>.py"}` con `formato(ctx)` y `diseno(ctx)` |
| `imagen` | opcional | portada (si no, el panel dibuja una) |

## 5. Los contratos

### 5.1 La página (lo que graba el panel)
`game_tail.js` debe exponer, **como mínimo**:
| Gancho | Qué hace |
|---|---|
| `window.__ready = true` | cuando terminó de cargar (fuentes, imágenes, tiempos) |
| `window.__frame(dt)` | avanza `dt` segundos y **dibuja** ese fotograma |
| `window.__adv(n)` | salta `n/30` s **sin dibujar** (el grabador salta tramos) |
| `window.__sim(seed)` | devuelve `{V: duración_en_segundos, …}` |
| `window.__done()` · `__cues` · `__log` | fin del video · lista de sucesos `{v, k, …}` · mensajes de depuración |

Reglas de dibujo:
- **Cada fotograma se calcula desde el tiempo `t`**, sin depender del fotograma anterior (así `?t=SEG`, `__adv` y la grabación dan el mismo resultado). Nada de `Math.random()` dentro del dibujo: usa un ruido determinista (`hash(n)`).
- **Lienzo:** short 1080×1920, largo 1920×1080 (lo fija `construir.py` con `__W__`/`__H__`). El grabador **copia primero el canvas `#gl` (WebGL, si existe) y luego `#cv` (2D)**: respeta esos ids.
- **Tiempos** (`tiempos: "guion"`): leer `audiolibro/tiempos.json` → `{tags: {clave: [inicio, fin]}, dur}` (lo escribe el panel: estimado en el borrador y **real** con la voz); si no existe, `guion/1.json`. Cada toma usa la `key` de su frase para encontrar su segundo.
- **Cues** (`cue('pop')`, `'whoosh'`, `'ding'`…): sucesos que la mezcla del panel puede convertir en sonido.
- **Probar sin grabar:** `index.html?play=1` reproduce; `?t=12.5` muestra un fotograma; `?seed=3` cambia la semilla.
- Fuentes web: cárgalas con `document.fonts.load(...)` y un límite de espera (sin internet debe seguir funcionando con una tipografía de reserva).

### 5.2 La ficha y el constructor
La **ficha** (`specs/ID.json`) describe UN video: `titulo`, `seg` (duración pedida), `formato`, `seo`, `ajustes` y `escenas` (una por frase/toma: `{key, texto, tipo, …}`). `construir.py` **valida** y, si todo cumple, escribe `series/ID/`. **Si no cumple, NO construye y dice qué corregir** (así Claude no entrega algo roto). Comprobaciones mínimas que debe tener:
- ≥ 3 tomas y claves únicas; tipos conocidos.
- Una idea por frase, **≤ 26 palabras**; el cierre es una frase completa.
- **Tiempo estimado entre el 75 % y el 104 %** de `seg`, con `RITMO = 0.0775 s/carácter` y `PAUSA = 0.25 s` (**el mismo ritmo con que el panel estima el borrador**; si lo cambias, el borrador no coincidirá).
- Las reglas propias del plugin (p. ej. «≥ 3 citas con versículo», «la primera frase empieza con…», rango de palabras según la duración).

El bloque `seo` (`tipo, sujeto, hecho, pregunta, gancho, momentos[], datos[], hashtags[], tags_tema[]`) alimenta los títulos, la descripción y las etiquetas de la pestaña Publicar. Los **datos** que se digan llevan su **fuente** en `seo.datos`.

### 5.3 El pipeline (la receta)
`pipeline/pipeline_<id>.py` **no** graba ni mezcla: declara una receta y llama a `pipeline.correr(receta)` del panel. La receta es un diccionario con:
`archivos` (los que dibujan el video: si no cambian, el panel no regraba) · `preparar(P)` (armar `game.js`) · `tras_tiempos(P)` (opcional) · `escenas(P, fin)` (para la mezcla por escenas) · `grabacion` (`"pagina"` si la escena lleva HUD en HTML).
El panel lo lanza con las variables de entorno `DEVPANEL` (carpeta del panel), `PLUGIN_DIR` (carpeta del plugin) y `PLUGIN_AJUSTES` (JSON con los ajustes). **Etapas:** `borrador` (video mudo con tiempos estimados) → el usuario revisa → **«Estoy conforme»** → `voz`/`conforme` (voz real + regrabar + mezcla + unión) · `tramo DESDE HASTA` (regraba solo un tramo).

A mano: `set DEVPANEL=...`, `set PLUGIN_DIR=...` y `python plugins/ID/pipeline/pipeline_ID.py D:\ruta\series\VIDEO borrador`.

### 5.4 Ideas (`ideas/ideas_<id>.py`)
- `mas_ideas(formato, n, usados)` → `n` ideas nuevas para `short`/`largo`, sin repetir los títulos de `usados`.
- `ideas_de(texto, formato)` → ideas para un pedido libre del usuario (suelen ser 6 formas de contarlo).
- Cada idea: `{"formato", "titulo", "desc", "modo"}` (`modo` ∈ `ideas.tipos` de `plugin.json`).
- **Siempre se debe poder pedir otro lote** (error real: con pocas ideas el 2.º lote salía vacío). Mínimo recomendado: 12 temas reales **con sus datos verificados**.

### 5.5 Títulos (`titulos/titulos_<id>.py`)
`generar(pid, f, lote, usados=(), largo=False)` → hasta **100** diccionarios `{titulo, descripcion, etiquetas[], score, motivo[], largo, hook_3s, comentario_fijado, hashtags[]}`. Gancho primero, 30–75 caracteres, hablar de lo que **muestra** el video, 5 hashtags (`#Shorts` primero), etiquetas ≤ 500 caracteres. Tantas combinaciones que `lote` 1, 2, 3… no salgan vacíos ni repetidos.

### 5.6 Ajustes del subpanel (`plugin.json → ajustes`)
Cada ajuste: `id`, `tipo`, `etiqueta`, `ayuda` (**qué hace**, obligatoria y no vacía) y opcionales `grupo`, `defecto`, `min`, `max`, `opciones`.
| `tipo` | Reglas que valida el panel |
|---|---|
| `interruptor` | `defecto`: `true`/`false` |
| `numero` | `defecto` numérico y `min ≤ defecto ≤ max` |
| `opcion` | `opciones` no vacía y `defecto` ∈ `opciones` |
| `texto` | cadena libre |
`id` sin repetir. El constructor los lee de `PLUGIN_AJUSTES` si la ficha no los trae. Nunca pongas aquí claves ni rutas personales.

### 5.7 Opcionales: `config_video` y `agentes`
- `config_video`: campos que el plugin pide **en Ideas** para cada video (`id, tipo, etiqueta, ayuda`; `tipo` ∈ `paises|interruptor|opcion|numero|equipos|ganador|comentario`). No repitas ahí lo que ya es un ajuste.
- `agentes`: módulo con `formato(ctx)` (mejor formato para la idea) y `diseno(ctx)` (mejor diseño); devuelven `{resumen, detalle, config, uso}`.

## 6. Cómo llega un pedido y cómo se contesta
1. El usuario pide un video en el panel → queda en `pedidos.json` y un monitor (`escucha.py`) avisa a Claude: `PEDIDO NUEVO [video] título :: nota (formato · segundos · plugin · ajustes)`.
2. Claude lee `plugins/ID/INSTRUCCIONES.md` + `memoria.md`, escribe el **guion** y la **ficha**, **construye** (`construir.py`) y **mira los fotogramas**.
3. Avisa el avance: `python pedido.py IDEA_ID PORCENTAJE "mensaje" --etapa N` (1 Entender el pedido · 2 Guion · 3 Datos/mapa · 4 Personajes y escenas · 5 Gráficos · 6 Voz y tiempos · 7 Verificación · 8 Borrador listo). `--error` avisa de un fallo; `--pregunta "…" --opciones "Sí|No"` pide una decisión.
4. Lanza el **borrador** con el pipeline (video mudo + subtítulos en el panel). **Nunca genera la voz por su cuenta**: espera «Estoy conforme».
5. Mantener la conexión viva: `POST /api/vivo_tiempo {"min":30}` y el monitor armado.

## 7. CREAR un plugin (método paso a paso)
1. **Define el tipo de video** en una frase y busca sus **referencias** (capturas, un repositorio, un reel). Anótalas en `referencia.md` con su licencia.
2. **Si existe un código o estilo original, ÚSALO** (con su licencia y atribución) en vez de inventar un motor «parecido»: el plugin solo añade lo que falta para el panel (ganchos, tiempos, formatos, texto). *Error real: un motor propio hecho «desde la descripción» salió feo; el mismo estilo con el código original salió bien.*
3. **Diseña primero en papel** (`DISENO.md`): paleta en hex, tipografías, tamaños, zonas, movimientos. Mientras más concreto, menos adivina Claude.
4. **Crea el plugin** con `crear_plugin.py`, cambia `motor/motor.js` por tu estilo y añade las clases de toma que necesites (`MOTOR.tipos.<nombre>`).
5. **Escribe `INSTRUCCIONES.md`** como si fuera para alguien que no conoce el proyecto: pasos, ficha, reglas de guion, ajustes.
6. **Escribe ≥ 12 ideas reales con datos verificados** y una **ficha de ejemplo completa** (`specs/ejemplo.json`) que construya en todos los formatos.
7. **Mira cada toma en cada formato** (`?t=`) en el navegador del panel y **en un frame del video grabado**: la vista previa y la grabación pueden diferir (fuentes, GPU).
8. **Verifica** (`verificar_plugin.py`), **empaqueta** (`--zip`), **instala** el zip en un panel limpio y construye un video de punta a punta.

## 8. MEJORAR un plugin (ciclo y reglas)
**Ciclo:** reproducir el problema → **corregir en el plugin** (no solo en ese video) → documentar la regla → regresión (construir el ejemplo en todos los formatos y mirar fotogramas) → subir versión → empaquetar.

- **Todo lo que el usuario critica se convierte en una regla escrita** (`NO_HACER.md` o `DISENO.md` con su porqué) y, si se puede, en una comprobación de `construir.py`. Así no vuelve a pasar en el próximo video.
- **Versiones (`x.y.z`):** `patch` = arreglo sin cambiar fichas; `minor` = función nueva compatible (un tipo de toma, un ajuste); `major` = cambia el formato de la ficha o rompe videos anteriores. Súbela con `verificar_plugin.py ID --subir patch --nota "qué cambió"` (la anota en `memoria.md → Versiones`).
- **Compatibilidad:** una ficha escrita para la versión anterior debe seguir construyendo; si no, es `major` y se explica en `memoria.md` cómo migrar. No cambies `RITMO` ni los nombres de los ganchos sin necesidad.
- **No toques el código del panel:** si falta algo, se añade en el plugin (un adaptador) o se propone al panel. Si reutilizas código de un tercero, **no lo modifiques**: añade tu adaptador aparte (así se puede actualizar).
- **Un cambio, un motivo:** no mezcles un arreglo visual con una función nueva en la misma versión.
- **Regresión mínima antes de entregar:** `verificar_plugin.py` en verde + un fotograma de cada toma del ejemplo en cada formato + un borrador completo.
- **Rendimiento:** mide el tiempo de carga y de grabación; si una toma tarda demasiado, simplifica o precalcula en `build()`.

## 9. Lista de verificación antes de entregar
- [ ] `plugin.json` válido, `id` = carpeta, `version` `x.y.z`, `licencia` y atribuciones.
- [ ] `verificar_plugin.py` → **✔ LISTO** (el verificador del panel y la revisión propia).
- [ ] Ningún marcador `‹ ›` ni `{{ }}` sin rellenar; `INSTRUCCIONES.md` completa.
- [ ] `specs/ejemplo.json` construye en **todos** los formatos declarados.
- [ ] Miré **un fotograma de cada toma en cada formato**; sin texto cortado, sin nada bajo el subtítulo, sin tomas quietas ni vacías.
- [ ] Sin voz/mezcla/render propios; sin claves, tokens ni rutas personales.
- [ ] Datos con fuente en `seo.datos`; las ideas traen datos verificados.
- [ ] El zip se instala en el panel (`/api/plugin_revisar` dice «cumple la estructura») y un video se construye de punta a punta.
- [ ] `memoria.md` con la versión y lo aprendido.

## 10. Instalar, actualizar y desinstalar
- **Instalar:** pestaña **Plugins → instalar .zip**. El zip debe traer **la carpeta del plugin en la raíz** (`mi-plugin/plugin.json`, …); `verificar_plugin.py --zip` ya lo hace así. Solo se instala si **cumple el esqueleto**; si no, no se instala nada y el panel dice qué falla.
- **Actualizar:** si el plugin ya existe, el panel ofrece actualizar a la versión nueva; la **anterior se guarda en `_papelera/`** (recuperable).
- **Desinstalar:** se mueve a `_papelera/` (recuperable). **Un plugin activo no se puede desinstalar** (desactívalo primero).
- **Qué carpetas ignora el panel:** las que empiezan con `_` o `.` dentro de `plugins/`. Úsalo para guardar un borrador sin que aparezca (`plugins/_borrador-x/`).
- **Este esqueleto no se instala:** vive fuera de `plugins/` y no trae `plugin.json` (trae `plugin.plantilla.json`). Si lo comprimes e intentas instalarlo, el panel responde «no es un plugin».
- **Cuidado en Windows:** una terminal (o cualquier programa) con su carpeta actual dentro del plugin impide moverlo: se copia a la papelera pero queda una carpeta vacía y el panel muestra «falta plugin.json». Cierra esa terminal o bórrala a mano.

## 11. Errores típicos y su solución
| Síntoma | Causa | Solución |
|---|---|---|
| «No cumple el esqueleto: falta plugin.json» con 0 archivos | carpeta vacía (se desinstaló con una terminal dentro) | borrar la carpeta vacía y reinstalar el zip (la copia está en `_papelera/`) |
| «el id no coincide con la carpeta» | `id` ≠ nombre de la carpeta | igualarlos |
| «la página expone `__frame`» falla | los ganchos no están literalmente en los archivos de `pagina` | declararlos en `game_tail.js` y listar ese archivo en `pagina` |
| «requisito: no existe …» | `requisitos.archivos` lista un archivo que no está | quitarlo de la lista o crearlo |
| «trae su propio motor de voz/mezcla/render» | un `.py` con nombre `voz_*`, `mix*`, `grab*`, `unir` o carpeta `voz/` | quitarlo: lo hace el panel |
| «`generar` recibe pid, f, lote y usados» | firma con menos de 4 parámetros | `generar(pid, f, lote, usados=(), largo=False)` |
| El borrador sale pero con tiempos raros | `RITMO`/`PAUSA` distintos a los del panel | volver a `0.0775` y `0.25` |
| Pantalla negra al grabar | el canvas no es `#cv`/`#gl`, o `__ready` nunca llega (error en `build()`) | mirar `window.__log` y la consola; envolver `build()` en `.catch` |
| La vista previa se ve bien y el video no | fuentes que no cargaron en la grabación, WebGL sin GPU | `document.fonts.load` con límite + tipografía de reserva; comprobar un frame del video |
| La ficha «no construye» | una regla de `construir.py` | leer el mensaje: dice exactamente qué corregir |
| Salió el mismo error en el siguiente video | la corrección solo se hizo en ese video | escribir la regla en `NO_HACER.md` y una comprobación en `construir.py` |

## 12. Lecciones aprendidas (de los plugins ya hechos)
- **El plugin es el motor:** cada plugin trae su propio estilo, interfaz y reglas; **no se copia el de otro** (cada juego con su marco, ranking y pausa; cada estilo con su paleta).
- **No inventes un motor «parecido»: reutiliza el original** (con licencia) y añade solo el adaptador al panel.
- **Mira siempre los fotogramas** (cada toma, cada formato) antes de decir «listo»; no te fíes del código.
- **Todo video tiene una historia con fuentes** (no un quiz de verdad/mito), un cierre completo y **no es un bucle** salvo que se pida.
- **La voz no se genera sin «Estoy conforme»**, y no se graba ni se renderiza sin un pedido nuevo del panel.
- **Datos exactos:** cada cifra y cita verificada; lo discutido se dice «hay quien traduce…» / «muchos creen…».
- **Que el 2.º lote nunca salga vacío** (ideas y títulos).
- **Tiempos por guion:** deja que el panel calcule los tiempos (estimados → reales) y que los elementos aparezcan en **la palabra** que se dice, no en segundos fijos.
- **Nada personal dentro del plugin:** ni claves, ni tokens, ni rutas de tu equipo.
- **Documenta lo que cuesta descubrir** en `memoria.md`; la próxima vez alguien (o Claude) lo agradecerá.
