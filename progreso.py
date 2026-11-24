"""Claude informa aqui como va la produccion de un video (el panel lo muestra con barras de %).
Uso: python progreso.py PROYECTO "etapa" PCT "mensaje" [--escena N]     (sin tildes en los textos)"""
import json, sys, time, pathlib
D = pathlib.Path(__file__).parent; a = sys.argv[1:]
pid, etapa, pct, msg = a[0], a[1], int(a[2]), a[3] if len(a) > 3 else ""
esc = int(a[a.index("--escena") + 1]) if "--escena" in a else None
ps = json.loads((D / "proyectos.json").read_text(encoding="utf-8"))
for p in ps:
    if p["id"] != pid: continue
    if esc is None: p["progreso"] = {"etapa": etapa, "pct": pct, "msg": msg, "act": time.strftime("%Y-%m-%d %H:%M:%S")}
    else:
        for e in p.get("escenas", []):
            if e["n"] == esc: e["pct"] = pct; e["msg"] = msg; e["act"] = time.strftime("%Y-%m-%d %H:%M:%S")
(D / "proyectos.json").write_text(json.dumps(ps, ensure_ascii=False, indent=1), encoding="utf-8"); print("ok", pid, etapa, pct)
