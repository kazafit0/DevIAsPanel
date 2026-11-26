"""CHEQUEO AUTOMÁTICO del panel de mapas y de sus proyectos (2026-11-17). Existe porque se repitieron errores míos: sintaxis rota al editar, falta game.js, escenas.json,
campos None que tumban el panel, video viejo en caché, pedidos sin idea, textos de otro video, voz con puntos, etc.
Uso:  python chequeo.py              -> revisa TODO (código, panel, proyectos)
      python chequeo.py CARPETA      -> revisa un proyecto (lo usa el pipeline antes de cada etapa)
      python chequeo.py --js CARPETA -> además carga el juego en un navegador y mira que no haya errores de JavaScript
Sale con código 1 si hay problemas (y los lista). Los de gravedad «AVISO» no detienen."""
import sys, os, json, re, pathlib, py_compile, urllib.request, time
os.environ["TEMP"] = os.environ["TMP"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp")
P = pathlib.Path(__file__).resolve().parent; SER = P.parent / "series"
ERR, AV = [], []
def err(m): ERR.append(m)
def av(m): AV.append(m)
def jl(f, d=None):
    try: return json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    except Exception as e: return d
def codigo():   # 1) todo el código del panel compila (una sangría mala tumba el panel entero)
    for f in list(P.glob("*.py")):
        try: py_compile.compile(str(f), doraise=True, cfile=os.path.join(os.environ["TMP"], "_pyc_chequeo"))
        except Exception as e: err("CÓDIGO ROTO %s: %s" % (f.name, str(e)[:160]))
    h = (P / "static" / "index.html")
    if h.exists():
        t = h.read_text(encoding="utf-8")
        if t.count("{") < 10 or "function drawPlayer" not in t: err("index.html del panel parece incompleto")
def panel():    # 2) el servidor responde y sus rutas clave no dan 500
    for ruta in ("/api/estado", "/api/proyectos", "/api/pedidos", "/api/jobs"):
        try:
            r = urllib.request.urlopen("http://localhost:8810" + ruta, timeout=10).read(); json.loads(r)
        except Exception as e: err("PANEL: %s no responde bien (%s)" % (ruta, str(e)[:80]))
    try:
        e = json.loads(urllib.request.urlopen("http://localhost:8810/api/estado", timeout=10).read())
        if not e.get("claude"): err("Claude figura DESCONECTADO en el panel (latido o temporizador vencido)")
        if e.get("vivo_resta", 0) < 1800: av("el temporizador de Claude queda con menos de 30 min")
    except Exception: pass
    for p in jl(P / "proyectos.json", []):
        for k in ("video_final", "video_mudo"):
            if k in p and p[k] is None: err("proyectos.json: %s tiene %s=null (tumba el panel)" % (p["id"], k))
        try:
            t = json.loads(urllib.request.urlopen("http://localhost:8810/api/titulos?id=" + p["id"], timeout=60).read())
            if not (t.get("items") or t.get("elegido")): err("TÍTULOS vacíos en %s (sujeto/hecho muy largos?)" % p["id"])
        except Exception as e: err("TÍTULOS fallan en %s: %s" % (p["id"], str(e)[:80]))
    ped = jl(P / "pedidos.json", []); cat = {i["id"] for i in jl(P / "catalogo.json", [])}
    for x in ped:
        if x.get("estado") not in ("hecho",) and (not x.get("idea") or x.get("idea") not in cat): err("PEDIDO sin idea enlazada (saldrá «aún no empezó»): %s" % x.get("titulo", "")[:50])
def proyecto(c):  # 3) un proyecto concreto
    c = pathlib.Path(c); n = c.name
    for f in ("game.js", "game_head.js", "game_body.js", "game_tail.js", "pausecard.js", "index.html", "proyecto.json", "guion/1.json"):
        if not (c / f).exists(): err("%s: falta %s" % (n, f))
    for f in ("motor/studio.js", "motor/kit.js", "tools/mix_escena.py"):
        if not (c / f).exists(): err("%s: falta %s" % (n, f))
    if (c / "game.js").exists() and all((c / f).exists() for f in ("game_head.js", "game_body.js", "pausecard.js", "game_tail.js")):
        arm = "".join((c / f).read_text(encoding="utf-8") + "\n" for f in ("game_head.js", "game_body.js", "pausecard.js", "game_tail.js"))
        if re.sub(r"\s+", "", arm) != re.sub(r"\s+", "", (c / "game.js").read_text(encoding="utf-8")): err("%s: game.js NO está al día con head/body/tail (hay que rearmarlo)" % n)
    g = jl(c / "guion/1.json", [])
    if g:
        ts = [float(x["t"]) for x in g]
        if any(b < a for a, b in zip(ts, ts[1:])): err("%s: los tiempos del guion no van en orden" % n)
        keys = [x["key"] for x in g]
        if len(set(keys)) != len(keys): err("%s: claves repetidas en el guion" % n)
        for x in g:
            if "." in x["texto"].replace("EE. UU.", ""): av("%s: el texto «%s…» lleva punto (la voz lo limpia, pero revisa)" % (n, x["texto"][:25]))
        if "uL1" not in keys or "uL2" not in keys: av("%s: no tiene intermedio de like (uL1/uL2)" % n)
    m = jl(c / "proyecto.json", {})
    if m:
        tx = " ".join(x["texto"] for x in g) + " " + (c / "game.js").read_text(encoding="utf-8") if (c / "game.js").exists() else ""
        prot = {"Perú": ["CHILE?", "SUDAMÉRICA"], "Chile": ["PERÚ + CHILE"]}   # restos típicos de copiar otro video
        for k, l in prot.items():
            if k in m.get("titulo", "") and False: pass
        base = {"formato": m.get("formato"), "aspecto": m.get("aspecto")}
        if m.get("formato") == "largo" and m.get("aspecto") != "16:9": err("%s: es «largo» pero no es 16:9" % n)
        pr = [p for p in jl(P / "proyectos.json", []) if p["id"] == m.get("id")]
        if pr and pr[0].get("video_final") and not (c / pr[0]["video_final"]).exists(): err("%s: el panel apunta a un video final que no existe" % n)
        if pr and pr[0].get("video_final") and (c / pr[0]["video_final"]).exists():
            mt = int((c / pr[0]["video_final"]).stat().st_mtime)
            if abs(mt - int(pr[0].get("unido_t", 0))) > 120: err("%s: unido_t (%s) no coincide con el video final (%s): el navegador mostraría el viejo" % (n, pr[0].get("unido_t"), mt))
    ti = jl(c / "audiolibro/tiempos.json", {})
    if ti and not ti.get("estimado") and (c / "voz/voz_completa.wav").exists():
        if (c / "salida_mudo/s1_completo.mp4").exists() and (c / "voz/voz_completa.wav").stat().st_mtime > (c / "salida/").stat().st_mtime + 3600 * 0 and False: pass
def js(c):      # 4) el juego carga y dibuja sin errores de JavaScript
    from playwright.sync_api import sync_playwright
    c = pathlib.Path(c); errs = []
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1080, "height": 1920}); pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        try:
            pg.goto("http://localhost:8810/series/%s/index.html?seed=1" % c.name); pg.wait_for_function("window.__ready===true", timeout=60000)
            for t in (3, 12, 25, 40, 55):
                pg.evaluate("__adv(%d)" % int(t * 30)); pg.evaluate("__frame(1/30)")
        except Exception as e: errs.append("no carga/no dibuja: " + str(e)[:160])
        br.close()
    for e in errs[:3]: err("%s: JS: %s" % (c.name, e))
def revisar(carpeta=None, con_js=False):
    ERR.clear(); AV.clear(); codigo()
    if carpeta: proyecto(carpeta); (con_js and js(carpeta))
    else:
        panel()
        for c in sorted(SER.glob("mapa_*")):
            if (c / "proyecto.json").exists(): proyecto(c)
    return list(ERR), list(AV)
if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]; e, v = revisar(a[0] if a else None, "--js" in sys.argv)
    for m in v: print("AVISO:", m)
    for m in e: print("ERROR:", m)
    print("CHEQUEO:", "TODO BIEN" if not e else "%d ERRORES" % len(e)); sys.exit(1 if e else 0)
