# Usar el DevIAs Panel con Claude, con Codex (ChatGPT) o con los dos por turnos

**Idea clave:** el panel es independiente. Los agentes (Claude o Codex) son solo *quien atiende los pedidos*. Todo (videos, voces, pedidos, configuración) vive en la carpeta del panel, así que **cambiar de agente no pierde nada**.

En la barra superior del panel siempre ves quién atiende: **«Atiende: Claude»** o **«Atiende: Codex (ChatGPT)»**.

## Qué necesitas
- Windows, Python 3.10 o superior y la carpeta del panel (`git clone https://github.com/kazafit0/DevIAsPanel`).
- **Claude Code** y/o **Codex CLI** (viene con los planes de ChatGPT; guía de instalación: https://developers.openai.com/codex/cli).

## A) Instalar y usar con Claude
1. Abre **Claude Code** en la carpeta del panel y activa el skill **`devias-panel`** (el archivo `SKILL.md`).
2. Claude te recibe con «Bienvenido al DevIAs Panel…» y hace la instalación guiada (paquetes, voces, abrir el panel).
3. Cuando el panel se apague o se desconecte, escríbele **`devias`**.

## B) Instalar y usar con Codex (ChatGPT)
1. Abre **Codex** dentro de la carpeta del panel. Codex lee solo el archivo `AGENTS.md` (no hay que activar nada).
2. Escríbele: **«instala el DevIAs Panel»**. Hará la instalación guiada: paquetes, carpeta de temporales, voces y abrir el panel. Codex te pedirá aprobación para ejecutar comandos.
3. En el panel: **Ajustes → «¿Quién atiende los pedidos?» → Codex (ChatGPT)**. Sin este paso los pedidos van a Claude.
4. Escríbele a Codex **`devias`**. Queda conectado y la barra dice «Codex conectado».
5. Codex **no recibe avisos solo**: cuando hagas un pedido en el panel, dile «mira los pedidos» (o «espera pedidos» y se queda esperando).

## C) Cambiar de uno a otro (cuando a uno se le acaba el uso)
| Quieres pasar de… | Haz esto |
|---|---|
| **Claude → Codex** | 1) Ajustes → «¿Quién atiende?» → **Codex**. 2) Abre Codex en la carpeta del panel. 3) Escríbele **`devias`**. |
| **Codex → Claude** | 1) Ajustes → «¿Quién atiende?» → **Claude**. 2) Abre Claude Code en la carpeta del panel. 3) Escríbele **`devias`**. |

- Al elegir uno, **el otro queda desactivado**: no recibe pedidos y deja de aparecer como conectado.
- **Lo que ya terminó se conserva.** Un pedido que el otro agente estaba atendiendo queda libre 20 minutos después de su último aviso. Si no quieres esperar, dile al nuevo: «retoma el pedido X».
- La voz y la unión de los videos siempre las inicias tú desde el panel, con cualquier agente.

## D) Si dejas de usar ChatGPT y vuelves solo a Claude
Elige **Claude** en Ajustes y listo. No hay nada que desinstalar: `AGENTS.md` es solo un archivo que Codex lee si lo abres en esa carpeta.

## Preguntas frecuentes
**Es mi primera vez con Codex y con Claude Code: ¿se instala todo si lo bajo de git?**
Sí. Baja el panel (`git clone`) y abre **cualquiera** de los dos agentes dentro de la carpeta. Al abrirse, **Claude Code lee `CLAUDE.md`** y **Codex lee `AGENTS.md`** (no hay que activar nada). Dile «instala el DevIAs Panel» y hace la instalación guiada: paquetes, voces y abrir el panel. Si abres el otro agente después, **no reinstala**: ve que ya está todo y solo se conecta.

**Ya lo instalé con Codex; ¿para usar Claude Code hago lo mismo y le digo `devias`?**
Sí, es lo mismo y no repite la instalación:
1. En el panel: Ajustes → «¿Quién atiende los pedidos?» → **Claude**.
2. Abre Claude Code en la carpeta del panel.
3. Escríbele **`devias`**: enciende el panel si hace falta, se conecta y atiende lo pendiente.

Y al revés (de Claude a Codex) es igual: Ajustes → Codex, abrir Codex en la carpeta y escribir `devias`.

**¿Y si olvido cambiar el selector de Ajustes?**
Si le escribes `devias` a un agente que no es el elegido, te avisa que el panel está dirigido al otro y **no toma pedidos**. Cámbialo en Ajustes y vuelve a escribir `devias`.

## Límites
- Con Codex no hay botón de **Emergencia** (solo despierta a Claude).
- Las instrucciones para Codex están escritas según la documentación de OpenAI; **no se han probado con un Codex real**. Si algo falla, díselo al agente y pídele que lea `AGENTS.md` de nuevo.
- Los plugins traen reglas muy largas; el resultado puede variar entre un agente y otro.
