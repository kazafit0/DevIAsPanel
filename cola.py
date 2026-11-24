"""Cola de produccion: los videos aprobados avanzan UNO POR UNO. Cuando termina el de turno, pasa al siguiente (crea su pedido para Claude)."""
import json, pathlib, time
D = pathlib.Path(__file__).parent
def _l(n, d):
    try: return json.loads((D / n).read_text(encoding="utf-8"))
    except Exception: return d
def _s(n, o): (D / n).write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
def avanzar():
    cat = _l("catalogo.json", []); ped = _l("pedidos.json", [])
    cola = sorted([i for i in cat if i.get("estado") == "produccion"], key=lambda i: i.get("cola", 999))
    if not cola: return
    activo = [x for x in ped if x.get("tipo") == "resto" and x.get("estado") != "hecho"]
    if activo: return
    it = cola[0]
    ped.append({"idea": it["id"], "tipo": "resto", "titulo": it["titulo"], "formato": it["formato"], "nota": "La escena 1 gusto: construir el resto del video (cola de produccion, turno actual).", "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente"})
    _s("pedidos.json", ped)
def encolar(cat, it):
    it["cola"] = max([i.get("cola", 0) for i in cat if i.get("estado") == "produccion"] + [0]) + 1

PAIS = {}   # los países los pone el PLUGIN activo (plugins/<id>/recursos/paises.json); el panel no trae ninguno
MAPA2D_DEF = {"camara": "dinamica", "zoom": "medio", "velocidad": "normal", "halo_costa": True, "olas": True, "nombres_paises": False, "fronteras": "finas", "vineta": True,
              "gelatinas": "normal", "nombre_gelatina": True, "ojos": "expresivos", "burbujas": True,
              "chip_titulo": True, "barra": True, "capitulos": True, "lista_lateral": True, "tarjeta": True, "contadores": True, "marca": True,
              "rayos": True, "pines": True, "flechas": True, "chispas": True, "barcos": True, "confeti": True, "intermedio_like": True, "loop": True}
def cfg_resumen(c):
    """Ajustes de un MAPA (nadie compite: sin paises, estilo, dificultad ni ganador). Texto que recibe Claude al aplicar los ajustes."""
    if not c or "mapa2d" not in c: return "Ajustes del mapa: por defecto (2D mejorado completo, 90 s)."
    m = dict(MAPA2D_DEF, **(c.get("mapa2d") or {})); si = lambda k: "si" if m.get(k) else "no"
    d = c.get("duracion") or 90
    return ("Ajustes del MAPA elegidos por el usuario (aplicalos de verdad): duracion = %s s | acabado = 2D mejorado (kit2d) | camara = %s, zoom %s, velocidad %s | mapa: halo de costa %s, olas %s, nombres de paises %s, fronteras %s, vineta %s | "
            "gelatinas: tamano %s, nombre %s, ojos %s, bocadillos %s | pantalla: chip de titulo %s, barra %s, capitulos %s, lista lateral %s, tarjeta de categoria %s, contadores %s, marca MAPA %s | "
            "efectos 2D: rayos %s, pines %s, flechas %s, chispas %s, barcos %s, confeti %s | intermedio de like %s | final en loop %s") % (d, m["camara"], m["zoom"], m["velocidad"], si("halo_costa"), si("olas"), si("nombres_paises"), m["fronteras"], si("vineta"),
            m["gelatinas"], si("nombre_gelatina"), m["ojos"], si("burbujas"), si("chip_titulo"), si("barra"), si("capitulos"), si("lista_lateral"), si("tarjeta"), si("contadores"), si("marca"),
            si("rayos"), si("pines"), si("flechas"), si("chispas"), si("barcos"), si("confeti"), si("intermedio_like"), si("loop"))
def cfg_default(formato, titulo="", desc=""):
    return {"duracion": 90, "mapa2d": dict(MAPA2D_DEF)}
def cargar_paises():   # lista de países del plugin activo (si trae recursos/paises.json)
    try:
        act = json.loads((D / "plugins_estado.json").read_text(encoding="utf-8")).get("activo")
        f = D / "plugins" / act / "recursos" / "paises.json" if act else None
        PAIS.clear()
        if f and f.exists():
            for _cn, _lst in json.loads(f.read_text(encoding="utf-8")):
                for _x in _lst: PAIS[_x["c"]] = _x["n"]
    except Exception: pass
cargar_paises()
