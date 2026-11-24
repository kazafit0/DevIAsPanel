"""ideas.py — Claude carga IDEAS PROPIAS en la pestaña «Ideas» del panel (2026-11-23, pedido del usuario: «la idea va al panel, el panel le pregunta a Claude y Claude debe dar ideas»).
Flujo: el usuario escribe un pedido -> el panel guarda ideas de plantilla y avisa a Claude (escucha.py: «IDEAS PEDIDAS») -> CLAUDE analiza el pedido, investiga lo necesario y propone 6–8 ideas VARIADAS con este script.
Uso:   python ideas.py --texto "<pedido tal cual lo escribió el usuario>" --formato short|largo --json ideas.json
ideas.json = lista de {"titulo","desc","enfoque","como":[pasos],"ref","temas":[...],"sujeto","modo"}.
Reemplaza las ideas de plantilla de ESE pedido (las que siguen en estado «idea») por las de Claude; las ya elegidas o usadas no se tocan."""
import json, os, sys, time, argparse, pathlib
D = pathlib.Path(__file__).resolve().parent

def jl(n, por):
    try: return json.loads((D / n).read_text(encoding="utf-8"))
    except Exception: return por

def guardar(n, v):   # escritura atómica: el panel lee estos archivos en cada petición
    tmp = D / (n + ".tmp"); tmp.write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8"); os.replace(tmp, D / n)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--texto", required=True); ap.add_argument("--formato", default="short"); ap.add_argument("--json", required=True)
    a = ap.parse_args()
    ideas = json.loads(pathlib.Path(a.json).read_text(encoding="utf-8"))
    if not isinstance(ideas, list) or not ideas: sys.exit("ideas.json debe ser una lista con al menos 1 idea")
    for i in ideas:
        if not i.get("titulo") or not i.get("desc"): sys.exit("cada idea necesita titulo y desc: %s" % json.dumps(i, ensure_ascii=False)[:80])
    cat = jl("catalogo.json", [])
    previas = [c for c in cat if (c.get("pedido_texto") or "").strip() == a.texto.strip() and c.get("formato") == a.formato]
    plugin = next((c.get("plugin") for c in previas if c.get("plugin")), None) or (jl("plugins_estado.json", {}) or {}).get("activo") or ""   # el plugin ACTIVO (el panel no asume ninguno)
    pid = next((c.get("pedido") for c in previas if c.get("pedido")), "p%d" % int(time.time()))
    lote = max([c.get("lote", 1) for c in cat if c.get("formato") == a.formato] + [1]) + (0 if previas else 1)
    quitadas = [c for c in previas if c.get("estado") == "idea" and not c.get("claude")]   # solo las de plantilla sin tocar
    cat = [c for c in cat if c not in quitadas]
    usados = {c.get("id") for c in cat}; k = 0
    for it in ideas:
        k += 1
        while "%s-c%d" % (pid, k) in usados: k += 1
        cat.append(dict({"modo": "historia"}, **{x: y for x, y in it.items() if x != "id"}, id="%s-c%d" % (pid, k), formato=a.formato, estado="idea", lote=lote, pedido=pid, pedido_texto=a.texto.strip(), plugin=plugin, claude=True))
    guardar("catalogo.json", cat)
    ped = jl("pedidos.json", [])
    for x in ped:
        if x.get("tipo") == "ideas" and (x.get("nota") or x.get("titulo") or "").strip()[:200] == a.texto.strip()[:200] and x.get("formato") == a.formato:
            x["msg"] = "%d ideas de Claude en «Ideas»" % len(ideas); x["act"] = time.strftime("%Y-%m-%d %H:%M:%S")
    guardar("pedidos.json", ped)
    print("ok: %d ideas de Claude cargadas (se quitaron %d de plantilla) para «%s» [%s]" % (len(ideas), len(quitadas), a.texto[:60], a.formato))

if __name__ == "__main__": main()
