# DevIAs Panel — instrucciones para Claude Code

Este proyecto es el **DevIAs Panel** (panel local de producción de videos con IA). Claude Code lee este archivo solo al abrirse en esta carpeta.

**Todo lo que debes hacer está en `SKILL.md`** (el skill `devias-panel`): léelo y sigue sus instrucciones, sin pedirle al usuario que "active el skill" a mano.

- Si el usuario dice **«instala el panel»** o es la primera vez → sigue la «INSTALACIÓN GUIADA» de `SKILL.md`. **Solo si falta algo:** si `python instalar.py --estado` ya muestra `paquetes_faltan` vacío, `chromium` en true y `voces.instaladas` en true, y `GET http://localhost:8820/api/senal` dice `primer_uso: false`, **ya está instalado: no reinstales**, pasa a «devias».
- Si el usuario escribe **«devias»** → sigue la sección «PALABRA CLAVE: devias» de `SKILL.md` (enciende el panel si hace falta, conecta, atiende lo pendiente).
- **Quién atiende los pedidos** lo elige el usuario en el panel (Ajustes → «¿Quién atiende los pedidos?»). Antes de tomar un pedido corre `python pendientes.py --soy claude`: si el panel está dirigido a «codex», no tomes nada.
- La guía para el usuario sobre cómo usar Claude y Codex por turnos está en `GUIA_AGENTES.md`.
- Habla en español sencillo. La voz y la unión de los videos las inicia solo el usuario.
