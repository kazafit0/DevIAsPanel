# Guía de uso · DevIAs Panel

Esta guía explica **cada pantalla del panel** y el camino completo de un video, desde la idea hasta el archivo final. Si todavía no lo instalaste, mira primero el [README](README.md).

---

## 1. La idea general

```
Pides un video  →  Claude lo piensa y arma el BORRADOR (sin voz)  →  tú lo revisas
      →  «Generar voz»  →  el borrador se regraba con la voz  →  «Unir con la voz»
      →  video FINAL (voz + música + efectos)  →  Publicar (título, descripción, etiquetas, miniatura)
```

- **Tú decides** cuándo se genera la voz y cuándo se une el video. Claude nunca los inicia por su cuenta.
- **Claude trabaja** en la conversación de Claude Code. El panel y Claude se hablan con archivos (`pedidos.json`, etc.): el panel deja tu pedido, Claude lo recoge y va avisando su avance en el panel.
- **Los formatos de video son plugins.** Las ideas, las reglas del guion y el diseño dependen del plugin que esté **activo**.

---

## 1b. Qué trae el panel y qué trae cada plugin

| Es del **panel** | Es del **plugin** |
|---|---|
| Pedidos, cola, borrador, voz, grabación, mezcla, unión, publicar, avisos, ajustes | Las **ideas**, las reglas del guion, el diseño del video, la lista de países u otros datos del formato, sus ajustes propios |

- **El panel viene sin plugins y sin configuración.** Al instalarlo no hay ideas ni formatos hasta que instales y actives un plugin.
- **Lo que necesita un plugin lo pone el plugin** en su carpeta `recursos/` (por ejemplo `recursos/paises.json` con la lista de países). El panel lo lee del plugin **activo**; si cambias de plugin, cambia la lista (no hace falta reiniciar).
- **Tus claves son tuyas y no viajan con el panel:** la clave de Freesound se pone en el ajuste del plugin (*Plugins → Configurar*). Queda solo en tu equipo.

---

## 2. La parte de arriba (siempre visible)

| Elemento | Qué significa |
|---|---|
| **Claude escuchando ⏱ mm:ss** (verde) | Claude está conectado. El reloj cuenta el tiempo hasta la próxima señal. |
| **Claude desconectado** (rojo) | Claude no ha mandado señal. Ve a *Ajustes → Sumar minutos* o escríbele a Claude «conéctate». |
| **🚨 Emergencia** | Si Claude no responde: deja el aviso y lo despierta sin que escribas. |
| **Campanita** | Avisos y preguntas de Claude («Marcar leídos» las limpia). |
| **Barra de abajo** | El trabajo que se está ejecutando (voz, grabación, unión) con su porcentaje. |

---

## 3. Las pantallas (menú de la izquierda)

### Inicio
Resumen de tu producción: ideas disponibles, videos en borrador, en proceso y finales, y la lista de tus videos con su estado (*En espera · Borrador · En proceso · Final listo*). Desde aquí abres un video o pulsas **Nuevo video**.

### Ideas
Pide ideas nuevas y elige cuál hacer. **Las ideas las genera el plugin activo.**
- **Pedírselo a Claude:** escribes qué tema quieres y Claude carga ideas variadas.
- Elige **formato**: *16:9 · Largo* o *9:16 · Short*, y la **duración**.
- Cada idea muestra «Cómo sucedería» y su referencia.
- Si una idea te interesa, **la mandas como pedido**; si no, la descartas. «Anteriores / Siguientes» pagina el catálogo.

### Mis videos
Aquí revisas cada video:
- **Vistas del reproductor:** *Borrador sin voz*, *Borrador con voz*, *Final con voz*.
- **Frases del guion** con sus tiempos y escenas: puedes leerlas y pedir cambios.
- **Pedir una mejora a Claude:** escribe qué debe cambiar y pulsa **Enviar mejora**.
- **Generar voz:** genera solo las frases nuevas o cambiadas. Al terminar, el borrador se regraba con los tiempos reales de la voz.
- **Rehacer la voz de una frase** o **Rehacer todas las voces** (cada rehacer da una toma distinta).
- **Unir con la voz:** produce el video final (tarda ~12 min en uno largo). Solo se activa cuando **todas** las frases tienen voz.
- **Rehacer todo:** archiva la versión anterior y manda la idea otra vez por el cerebro: sale una versión **nueva y distinta**.
- **Borrar y empezar de nuevo.**

### Voces
Estado de la voz de cada video (cuántas frases tienen audio) y acceso para abrir el video y generarla.

### Publicar
Prepara la publicación de un video: **título, descripción y etiquetas** (los generan los plugins con generadores de títulos de alto CTR), con botones **Copiar título / descripción / etiquetas**; y **miniatura**: *Generar capturas* del video, elegir una y guardar los cambios.

### Trabajos
Todo lo que el panel está generando o generó: voz, grabación, mezcla, unión, y lo que Claude reporta (porcentaje y mensajes). **Trabajos recientes** guarda el historial.

### Actividad
Lo que Claude va haciendo y el código que genera (útil para saber en qué paso va un pedido).

### Pedidos
Lo que le pediste a Claude y su estado. Si Claude te hace una pregunta, aparece aquí y en la campanita; la respondes con los botones.

### Referencias
Canales o videos que te inspiran. **Nueva referencia:** pega el enlace y pulsa *Agregar y generar ejemplos*. Los ejemplos se pueden **Pasar a ideas** o **Descartar**; también puedes **Pedir mejores ejemplos a Claude**.

### Plugins
Cada formato de video. Aquí:
- **Instalar un plugin** (`.zip` con `plugin.json`). Si ya existe, ofrece actualizar (la versión anterior va a `_papelera/`).
- **Activar / Desactivar** (solo uno activo a la vez; uno desactivado no ejecuta nada).
- **Ver archivos**, **configurar** sus ajustes (música, estilo…) y **Mejorar este plugin** (llega a Claude).
- **Desinstalar** (solo si no está activo; se guarda en `_papelera/`).

### Guía
Esta misma guía, dentro del panel.

### Ajustes (todo lo de tu equipo y tu conexión)
- **Conexión con tu agente (Claude o Codex):** estado, reloj, **Sumar minutos** y la **señal de conexión** (cada cuántos minutos manda la señal: 15 a 120 min; por defecto 30).
- **¿Quién atiende los pedidos?:** elige **Claude** o **Codex (ChatGPT)**; los pedidos llegan solo al elegido y el otro queda desactivado. La barra superior muestra siempre cuál atiende y si está conectado. Guía completa: `GUIA_AGENTES.md`.
- **Memoria para grabar:** tarjeta de video y RAM libres. Piper y Kokoro no se quedan en memoria; **Voice Studio** (si lo usas) sí ocupa unos 5 GB mientras está encendido: aquí está **Liberar memoria (apagar Voice Studio)** y **Encender Voice Studio (solo API)**.
- **Carpeta de temporales:** dónde guarda el panel sus archivos de trabajo (grabaciones, uniones). Vacío = `_tmp` dentro del panel. Cámbiala escribiendo tu ruta y **Guardar** (se aplica al reiniciar el panel).
- **Tu PC:** Windows y su versión, equipo, procesador, RAM total y libre, tarjeta(s) de video con su memoria, y **cómo graba el panel** (con tarjeta de video o solo procesador y RAM).
- **Voz del DevIAs Panel:** tres pasos: ver con qué voz hablan tus videos, **elegir el motor** (Voces del panel o Voice Studio) y **elegir la voz** (Escuchar / Usar esta voz). Abajo, **Configuración general** (velocidad y pausa; por defecto 1.1 y 400 ms, con el botón **Valores predeterminados**) y un solo botón **Guardar configuración**. Vale para todos los videos de todos los plugins.

---

## 4. Paso a paso: tu primer video

1. **Plugins** → instala y **activa** un plugin.
2. **Ideas** → pide ideas, elige formato y duración, y **envía el pedido**.
3. En **Trabajos / Pedidos** ves cómo Claude avanza (campanita si te pregunta algo).
4. Cuando el video aparezca como **Borrador**, ábrelo en **Mis videos** y míralo **sin voz**.
5. ¿Algo no te gusta? **Pedir una mejora**. Claude lo corrige y el borrador se actualiza.
6. ¿Todo bien? **Generar voz**. Se regraba el borrador con la voz.
7. Revisa el **borrador con voz**. Si una frase suena mal, **rehaz esa voz**.
8. **Unir con la voz** → sale el **video final**.
9. **Publicar** → copia título, descripción, etiquetas y elige la miniatura.

---

## 5. La señal de conexión (por qué dice «Claude escuchando»)

Claude no está «siempre conectado»: la conexión es una **señal que se renueva cada cierto tiempo**.
- El panel muestra un **reloj** con el tiempo que queda hasta la próxima señal.
- Eliges el intervalo en el **popup de bienvenida** (primera vez) o en **Ajustes → Señal de conexión**.
- Si usas el skill `devias-panel`, Claude crea una tarea que renueva la señal sola y vuelve a armar el monitor de pedidos si se apaga. Mientras la conversación de Claude Code esté abierta, no tienes que pedirle que se reconecte.
- Si la sesión se cierra, el reloj llega a 0 y dice **«Claude desconectado»**: abre Claude Code en la carpeta del panel y activa el skill.

### Palabra clave: «devias»
Si el panel se apagó, apagaste la PC o la conversación con Claude se reinició, escribe **«devias»** (o `/devias-panel`, «activa devias», «conecta el panel»). Claude enciende el panel si estaba apagado, vuelve a armar la conexión y la señal, y atiende los pedidos pendientes. Te responde en una línea: *«DevIAs Panel conectado · señal cada N min · N pedidos pendientes»*.

---

## 6. Voz

- **Piper (local):** voz `es_MX-claude-high`; rápida y sin internet. Se instala con `python instalar_voces.py`.
- **Kokoro (local):** voces `em_alex` (neutra) y `em_santa` (cálida); necesita Node.js 22+. Es más lenta que Piper porque carga su modelo en cada frase. Suena con acento más «de inglés» que Piper.
- **Jorge (edge-tts):** voz neuronal de México; va por **internet** (el texto se envía a Microsoft).
- **Voice Studio (opcional):** tus propios perfiles. Pulsa «Voice Studio»: busca su carpeta solo (o usa *Buscar en el PC*) y **detecta tus perfiles de voz** automáticamente; si creas uno nuevo en Voice Studio, pulsa **Detectar perfiles de voz**. Usa el botón de encendido (se enciende solo al generar voz). Un perfil cuyo audio de referencia dura más de 20 s necesita el modelo de voz a texto (Whisper) de Voice Studio.
- **Voces subidas:** las clonadas y las Piper que agregaste a `voces_tts` se pueden **borrar** desde su tarjeta (van a `_papelera/voces`, recuperables).
- La voz se genera **por frases** y cada frase cae en su segundo del guion. Solo se regeneran las frases cambiadas.
- *Rehacer* una frase siempre da **otra toma** (otra semilla).

---

## 7. Grabación y memoria

- Con **tarjeta NVIDIA ≥ 6 GB** se graba por GPU con varios trabajadores en paralelo.
- Sin ella se graba con el procesador (más lento).
- Si la grabación falla por memoria, el panel reintenta con menos trabajadores; cierra otros programas que usen la tarjeta antes de grabar.
- Los videos se guardan en `series/<id>/` (`salida_mudo/` = borradores, `salida/` = final).

---

## 8. Si algo falla

| Síntoma | Qué hacer |
|---|---|
| «Claude desconectado» | Escribe **«devias»** en Claude Code, o *Ajustes → Sumar minutos*. |
| Claude no responde a un pedido | Botón **🚨 Emergencia**. |
| «Faltan voces» al unir | Pulsa **Generar voz** y espera a que terminen todas. |
| La voz suena mal en una frase | **Rehacer la voz de esa frase** (otra toma). |
| «Falta la voz» | Ejecuta `python instalar_voces.py`. |
| Grabación lenta o sin memoria | **Ajustes → Liberar memoria** y reintenta. |
| El plugin no se instala | El panel muestra el informe: le falta algo del esqueleto `plugin.json`. |

---

## 9. Para quien crea plugins

Un plugin es una carpeta en `plugins/<id>/` con un `plugin.json` (campos: `esquema`, `api`, `id`, `nombre`, `version`, `descripcion`, `instrucciones`, `formatos`, `pipeline`, `voz`, `titulos`, `requisitos`, `ajustes`; opcionales: `ideas`, `plantillas`, `memoria`, `agentes`).
- El plugin define **ideas, reglas, diseño y su receta de pipeline**; **no** trae motor de voz, mezcla ni grabación (son del panel).
- Los scripts del plugin reciben `DEVPANEL`, `PLUGIN_DIR`, `PLUGIN_AJUSTES` y `DEVPANEL_TMP`.
- Reglas y límites completos: `SKILL.md` (sección «Contrato del plugin»).
