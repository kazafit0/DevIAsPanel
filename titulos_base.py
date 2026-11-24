"""TÍTULOS del NÚCLEO del DevPanel: guardar/cargar las opciones y un generador GENÉRICO de respaldo (2026-11-20).
Cada plugin aporta sus propios generadores (plugin.json -> titulos.tipos) con mucha más calidad para su formato; este solo se usa si el plugin no tiene uno para el tipo del video.
Entrada f = bloque «seo» del proyecto: pregunta/clave, momentos, datos, hashtags, tags_tema."""
import json, pathlib, random, hashlib, re
EMO = ["🔥", "🌎", "🎬", "✨", "💡", "👀"]
def cargar(carpeta, pid):
    f = pathlib.Path(carpeta) / (pid + ".json")
    try: return json.loads(f.read_text(encoding="utf-8"))
    except Exception: return None
def guardar(carpeta, pid, o):
    pathlib.Path(carpeta).mkdir(exist_ok=True); (pathlib.Path(carpeta) / (pid + ".json")).write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
def generar(pid, f, lote, usados=(), largo=False):
    T = (f.get("pregunta") or f.get("clave") or "").strip()
    if not T: return []
    rnd = random.Random(int(hashlib.md5(("%s-%d-base" % (pid, lote)).encode()).hexdigest()[:8], 16)); mom = f.get("momentos") or []; dat = f.get("datos") or []
    tpl = ["{T} {E}", "{T} (con datos reales) {E}", "{T}: lo que casi nadie sabe {E}", "Todo sobre: {T} {E}", "{T} Mira la respuesta {E}"] + ["{T} " + "{M}" + " {E}", "{M}: " + "{T} {E}"] * 3
    out, vistos = [], set(usados)
    for _ in range(4000):
        if len(out) >= 100: break
        t = rnd.choice(tpl).format(T=T, M=(rnd.choice(mom) if mom else ""), E=rnd.choice(EMO)); t = re.sub(r"\s+", " ", t).strip(); t = t[:1].upper() + t[1:]
        if t in vistos or len(t) > 98: continue
        vistos.add(t); out.append(t)
    tags = [x.lower() for x in (f.get("tags_tema") or [])] + [h.lower() for h in (f.get("hashtags") or [])]
    desc = "\n".join([T + " " + ("Esto es lo que cuenta el video." if not dat else "Lo que cuenta este video:")] + ["• " + (x[:1].upper() + x[1:]).rstrip(".") + "." for x in dat[:8]] + ["", "🔔 Suscríbete para más videos."])
    return [{"titulo": t, "descripcion": desc, "etiquetas": tags[:20], "score": 60, "motivo": ["genérico", "respaldo"], "largo": len(t), "hook_3s": T, "comentario_fijado": "¿Qué te pareció? Cuéntalo en los comentarios.", "hashtags": ["#" + h.title().replace(" ", "") for h in tags[:3]]} for t in out]
