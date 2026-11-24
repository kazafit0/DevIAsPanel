import os
"""Escucha DIRECTA del panel: la sesion de Claude la lanza (Monitor) y asi los pedidos llegan solos, sin copiar ni pegar nada.
- Cada 3 s escribe claude_vivo.json (el panel muestra «Claude conectado»).
- Respeta el TEMPORIZADOR del panel (vivo_hasta.json): cuando se acaba el tiempo, avisa y se apaga; el usuario puede darle mas tiempo desde el panel.
- Cuando aparece un pedido nuevo en estado pendiente, imprime una linea (eso despierta a Claude)."""
import json, pathlib, time, sys
SOLO = '--latido' in sys.argv   # modo LATIDO: solo escribe claude_vivo.json mientras dure el temporizador del panel (proceso aparte, no depende del Monitor de Claude, que caduca a los 30 min)
D = pathlib.Path(__file__).parent; vistos = set(); F = D / "vivo_hasta.json"
def hasta():
    try: return float(json.loads(F.read_text(encoding="utf-8"))["hasta"])
    except Exception: return 0
if hasta() < time.time() + 60: F.write_text(json.dumps({"hasta": time.time() + 30 * 60}), encoding="utf-8")   # por defecto 30 min si no hay tiempo puesto
aviso = False
avisado_fin = False
try: emerg_visto = float(json.loads((D / "emergencia.json").read_text(encoding="utf-8")).get("ts", 0))
except Exception: emerg_visto = 0
try:   # lo que ya existe al arrancar no se vuelve a anunciar
    for x in json.loads((D / "pedidos.json").read_text(encoding="utf-8")):
        if (x.get("tipo") or "") == "ideas": vistos.add((x.get("hora"), x.get("titulo"), x.get("tipo"), x.get("nota")))
except Exception: pass
while True:
    h = hasta(); ahora = time.time()
    if ahora >= h:   # temporizador a cero: NO se cierra (si el usuario suma tiempo, sigue y avisa de los pedidos pendientes)
        if not avisado_fin and not SOLO: avisado_fin = True; print("TIEMPO AGOTADO: el temporizador del panel llego a cero; Claude figura desconectado. Sigo escuchando: en cuanto el usuario sume tiempo en el panel, atiendo los pedidos pendientes.", flush=True)
        time.sleep(3); continue
    if avisado_fin: avisado_fin = False; aviso = False; print("TIEMPO REACTIVADO: el usuario sumo tiempo; reviso los pedidos pendientes.", flush=True)
    if h - ahora < 300 and not aviso: aviso = True; print("AVISO: quedan menos de 5 min de conexion; el usuario puede sumar tiempo en el panel.", flush=True)
    if h - ahora >= 300: aviso = False
    (D / "claude_vivo.json").write_text(json.dumps({"ts": ahora, "hasta": h, "chat": os.environ.get("CHAT_ID", "")}), encoding="utf-8")
    if SOLO: time.sleep(3); continue
    (D / "claude_monitor.json").write_text(json.dumps({"ts": ahora, "chat": os.environ.get("CHAT_ID", "")}), encoding="utf-8")   # latido del MONITOR real (el que despierta a Claude); el panel lo distingue del latido simple
    try:   # BOTON DE EMERGENCIA del panel: despierta a Claude aunque este parado
        em = json.loads((D / "emergencia.json").read_text(encoding="utf-8")); et = float(em.get("ts", 0))
        if et > emerg_visto:
            emerg_visto = et; pend = [x.get("titulo") for x in json.loads((D / "pedidos.json").read_text(encoding="utf-8")) if (x.get("estado") or "pendiente") not in ("hecho", "cancelado") and (x.get("tipo") or "") != "ideas"]
            print(("EMERGENCIA AUTOMATICA: el detector del panel vio que lo pendiente lleva minutos sin avanzar" if em.get("auto") else "EMERGENCIA: el usuario pulso el boton de emergencia del panel") + "; retoma YA lo pendiente sin esperar que escriba: %s" % ("; ".join(str(t)[:80] for t in pend[-6:]) or "(revisa pedidos y avisa)"), flush=True)
    except Exception: pass
    try: ped = json.loads((D / "pedidos.json").read_text(encoding="utf-8"))
    except Exception: ped = []
    for x in ped:
        k = (x.get("hora"), x.get("titulo"), x.get("tipo"), x.get("nota"))
        if (x.get("tipo") or "") == "ideas" and k not in vistos:   # petición de ideas: el panel ya preparó la lista, pero Claude también se entera
            vistos.add(k); print("IDEAS PEDIDAS [%s] %s :: el panel solo puso ideas de PLANTILLA: ANALIZA el pedido, investiga lo necesario y CARGA 6-8 ideas variadas con «python ideas.py --texto \"<pedido>\" --formato <f> --json ideas.json» (no empieces ningún video si el usuario no lo pide)" % (x.get("formato") or "short", (x.get("titulo") or "")[:200]), flush=True); continue
        if (x.get("estado") or "pendiente") == "pendiente" and k not in vistos:
            vistos.add(k)
            try:   # aviso al panel (campana): Claude recibió el pedido
                AF = D / "actividad.json"; Lg = json.loads(AF.read_text(encoding="utf-8")) if AF.exists() else []
                if (x.get("tipo") or "idea") in ("video", "mejora", "idea", "plugin_mejora"): Lg.append({"ts": time.time(), "hora": time.strftime("%H:%M:%S"), "dia": time.strftime("%Y-%m-%d"), "idea": x.get("idea"), "tipo": "recibido", "msg": "Claude recibió tu pedido «%s» y lo está leyendo." % (x.get("titulo") or "")[:70]}); AF.write_text(json.dumps(Lg[-400:], ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception: pass
            print("PEDIDO NUEVO [%s] %s :: %s" % (x.get("tipo") or "idea", x.get("titulo"), (x.get("nota") or "")[:200]), flush=True)
    time.sleep(3)
