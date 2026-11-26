"""PENDIENTES del DevIAs Panel, para CUALQUIER agente (Claude, Codex…): qué pedidos hay y quién los está atendiendo.
El usuario elige en el panel (Ajustes → «¿Quién atiende los pedidos?») a QUÉ agente le llegan; el otro no recibe nada.
Uso:
  python pendientes.py --soy codex             lista los pedidos LIBRES (si el panel está dirigido a «codex»; si no, dice que no debes tomar nada)
  python pendientes.py --soy codex --json      lo mismo en JSON
  python pendientes.py --soy codex --esperar 600   espera hasta 600 s a que llegue un pedido libre para ti (código 0 si hay, 2 si se acabó el tiempo, 3 si el panel está dirigido a otro agente)
  python pendientes.py --todos                 incluye también los pedidos hechos o cancelados
Un pedido está OCUPADO si lleva la marca «atiende» (la pone `pedido.py ... --yo NOMBRE`) y se renovó hace menos de 20 minutos:
si el agente se queda sin uso o se cae, a los 20 min el pedido vuelve a estar libre."""
import json, pathlib, sys, time
D = pathlib.Path(__file__).resolve().parent
CADUCA_S = 20 * 60
def leer():
    try: return json.loads((D / "pedidos.json").read_text(encoding="utf-8"))
    except Exception: return []
def agente_activo():   # a quién le llegan los pedidos (devpanel.json → «agente»); por defecto Claude
    try: a = str(json.loads((D / "devpanel.json").read_text(encoding="utf-8")).get("agente") or "claude").lower()
    except Exception: a = "claude"
    return a if a in ("claude", "codex") else "claude"
def estado_de(x, ahora):
    """libre | ocupado | cerrado"""
    if (x.get("estado") or "pendiente") in ("hecho", "cancelado"): return "cerrado"
    if x.get("atiende") and ahora - float(x.get("atiende_ts") or 0) < CADUCA_S: return "ocupado"
    return "libre"
def resumen(x, ahora):
    return {"idea": x.get("idea"), "tipo": x.get("tipo") or "idea", "titulo": x.get("titulo"), "estado": x.get("estado") or "pendiente", "pct": x.get("pct", 0),
            "plugin": x.get("plugin"), "atiende": x.get("atiende") if estado_de(x, ahora) == "ocupado" else None, "hora": x.get("hora"), "nota": (x.get("nota") or "")[:600], "situacion": estado_de(x, ahora)}
def lista(todos=False):
    ahora = time.time(); out = []
    for x in leer():
        s = estado_de(x, ahora)
        if s == "cerrado" and not todos: continue
        out.append(resumen(x, ahora))
    return out
def main():
    a = sys.argv[1:]; js = "--json" in a; todos = "--todos" in a; soy = a[a.index("--soy") + 1].lower() if "--soy" in a and len(a) > a.index("--soy") + 1 else None
    if soy and agente_activo() != soy and "--esperar" not in a:
        msg = "El panel está dirigido a «%s», no a «%s»: NO tomes pedidos. (El usuario lo cambia en Ajustes → ¿Quién atiende los pedidos?)" % (agente_activo(), soy)
        print(json.dumps({"dirigido_a": agente_activo(), "mensaje": msg}, ensure_ascii=False) if js else msg); sys.exit(3)
    if "--esperar" in a:
        lim = time.time() + (float(a[a.index("--esperar") + 1]) if len(a) > a.index("--esperar") + 1 else 600)
        while time.time() < lim:
            if (not soy or agente_activo() == soy) and any(p["situacion"] == "libre" for p in lista()): break
            time.sleep(3)
        else:
            print("sin pedidos nuevos para ti" + ("" if not soy or agente_activo() == soy else " (el panel está dirigido a «%s»)" % agente_activo())); sys.exit(2 if not soy or agente_activo() == soy else 3)
    L = lista(todos)
    if js: print(json.dumps(L, ensure_ascii=False, indent=1)); return
    libres = [p for p in L if p["situacion"] == "libre"]; ocupados = [p for p in L if p["situacion"] == "ocupado"]
    print("PEDIDOS LIBRES: %d · OCUPADOS: %d · el panel está dirigido a: %s" % (len(libres), len(ocupados), agente_activo()))
    for p in libres: print("  [libre] %s · %s · %s :: %s" % (p["idea"], p["tipo"], p["titulo"], p["nota"][:160].replace("\n", " ")))
    for p in ocupados: print("  [lo atiende %s] %s · %s · %s%%" % (p["atiende"], p["idea"], p["titulo"], p["pct"]))
if __name__ == "__main__": main()
