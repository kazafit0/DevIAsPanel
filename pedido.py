"""Claude actualiza aqui el progreso de un pedido del panel.
Uso: python pedido.py IDEA_ID PORCENTAJE "mensaje" [--hecho] [--proyecto ID_PROYECTO] [--etapa N] [--archivos a.js,b.py] [--error]
  --etapa N   etapa del CEREBRO del panel (1 Entender el pedido, 2 Guion, 3 Mapa y países, 4 Personajes y escenas, 5 Gráficos, 6 Voz y tiempos, 7 Verificación, 8 Borrador listo)
  --archivos  archivos que acabas de crear o cambiar (salen en la pestaña Actividad)
  --cambio "texto" (con --proyecto ID)  anota QUÉ cambió en el video: sale en el aviso «Borrador actualizado» cuando se vuelva a grabar
  --error     avisa que algo falló (campana roja en el panel)
  --pregunta "texto" [--opciones "Sí|No"]   Claude necesita una decisión del usuario: sale en el panel (chip naranja, campana y banner en el video) y espera su respuesta
  --agente formato|diseno "texto" [--estado pensando|listo]   uno de los dos agentes del cerebro (formato = mejor formato para la idea; diseno = mejor diseño del juego) deja lo que trajo: sale en el cerebro del panel
  --yo NOMBRE  quién atiende el pedido (claude, codex…): marca el pedido como «ocupado» para que otro agente no lo pise; se renueva en cada aviso y caduca a los 20 min (ver pendientes.py)
  --hecho     marca el pedido como hecho (y, si era una muestra, la idea pasa a «Escena 1 lista»)
  --proyecto  proyecto (de proyectos.json) donde se ve la muestra
"""
import json, sys, time, pathlib
D = pathlib.Path(__file__).parent
a = sys.argv[1:]; a_ = a
idea, pct, msg = a[0], int(a[1]), a[2] if len(a) > 2 else ""
hecho = "--hecho" in a or "--previa" in a
proy = a[a.index("--proyecto") + 1] if "--proyecto" in a else None
esc = int(a[a.index("--escena") + 1]) if "--escena" in a else None
fase = a[a.index("--fase") + 1] if "--fase" in a else None
etapa = int(a[a.index("--etapa") + 1]) if "--etapa" in a else None
arch = [z for z in a[a.index("--archivos") + 1].split(",") if z] if "--archivos" in a else []
hubo_error = "--error" in a
if "--cambio" in a and proy:
    _cf = D / "cambios_pendientes.json"; _c = json.loads(_cf.read_text(encoding="utf-8")) if _cf.exists() else {}
    _c.setdefault(proy, []).append(a[a.index("--cambio") + 1]); _cf.write_text(json.dumps(_c, ensure_ascii=False, indent=1), encoding="utf-8")
pregunta = a[a.index("--pregunta") + 1] if "--pregunta" in a else None
opciones = [z for z in a[a.index("--opciones") + 1].split("|") if z] if "--opciones" in a else []
if fase and proy:
    _ps = json.loads((D / "proyectos.json").read_text(encoding="utf-8"))
    for _q in _ps:
        if _q["id"] == proy: _q["fase"] = fase
    (D / "proyectos.json").write_text(json.dumps(_ps, ensure_ascii=False, indent=1), encoding="utf-8")
vid = a[a.index("--video") + 1] if "--video" in a else None
ped = json.loads((D / "pedidos.json").read_text(encoding="utf-8"))
if esc is not None and proy:   # escena rehecha/avanzada: actualiza proyectos.json
    ps = json.loads((D / "proyectos.json").read_text(encoding="utf-8"))
    for q in ps:
        if q["id"] == proy:
            for e in q.get("escenas", []):
                if e["n"] == esc:
                    e["estado"] = "lista" if hecho else "rehacer"
                    if vid: e["video"] = vid; e["ver"] = e.get("ver", 1) + 1
    (D / "proyectos.json").write_text(json.dumps(ps, ensure_ascii=False, indent=1), encoding="utf-8")
for x in ped:
    if x.get("idea") == idea and x.get("estado") != "hecho" and (esc is None or (x.get("tipo") == "escena" and x.get("n") == esc and x.get("estado") != "hecho")):
        x["estado"] = "hecho" if hecho else "en_proceso"; x["pct"] = 100 if hecho else pct; x["msg"] = msg; x["error"] = bool(hubo_error)
        if pregunta: x["pregunta"] = {"texto": pregunta, "opciones": opciones, "hora": time.strftime("%H:%M:%S")}; x.pop("respuesta", None)
        elif x.get("pregunta") and not x.get("respuesta"): pass
        if x.get("tipo") == "video": x["etapa"] = 8 if hecho else (etapa or max(x.get("etapa") or 1, min(8, 1 + pct * 8 // 100)))
        x["act"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if "--yo" in a_ and len(a_) > a_.index("--yo") + 1: x["atiende"] = a_[a_.index("--yo") + 1]; x["atiende_ts"] = time.time()   # quién lo atiende (varios agentes pueden turnarse)
        if hecho: x.pop("atiende", None); x.pop("atiende_ts", None)
        if "--agente" in a_:   # los dos agentes del cerebro: pedido.py IDEA PCT "msg" --agente formato|diseno "texto" [--estado pensando|listo]
            _i = a_.index("--agente"); _n = a_[_i + 1]; _tx = a_[_i + 2] if len(a_) > _i + 2 else ""; _est = a_[a_.index("--estado") + 1] if "--estado" in a_ else "listo"
            x.setdefault("agentes", {}).setdefault(_n, {}).update({"estado": _est, "msg": _tx, "hora": time.strftime("%H:%M:%S")})
        cat = json.loads((D / "catalogo.json").read_text(encoding="utf-8"))
        for it in cat:
            if it["id"] == idea:
                if proy: it["proyecto"] = proy
                if "--previa" in a: it["muestra"] = "previa"
                if hecho and x.get("tipo") in ("muestra", "escena1") and "--previa" not in a: it["muestra"] = "lista"
                if hecho and x.get("tipo") == "resto": it["estado"] = "hecho"
        if True:
            (D / "catalogo.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
(D / "pedidos.json").write_text(json.dumps(ped, ensure_ascii=False, indent=1), encoding="utf-8")
try:   # bitácora para la pestaña Actividad y la campana del panel
    AF = D / "actividad.json"; L = json.loads(AF.read_text(encoding="utf-8")) if AF.exists() else []
    L.append({"ts": time.time(), "hora": time.strftime("%H:%M:%S"), "dia": time.strftime("%Y-%m-%d"), "idea": idea, "tipo": "pregunta" if pregunta else ("error" if hubo_error else ("listo" if hecho else "avance")), "msg": (("Claude te pregunta: " + pregunta) if pregunta else msg), "pct": 100 if hecho else pct, "etapa": etapa, "archivos": arch})
    AF.write_text(json.dumps(L[-400:], ensure_ascii=False, indent=1), encoding="utf-8")
except Exception as e: print("aviso bitacora:", e)
try:   # que el panel lo muestre también en «Trabajos recientes» (si el panel está apagado no pasa nada)
    import urllib.request; _cfg = json.loads((D / "devpanel.json").read_text(encoding="utf-8")) if (D / "devpanel.json").exists() else {}
    urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%s/api/trabajo_externo" % (_cfg.get("puerto") or 8820), json.dumps({"idea": idea, "proyecto": proy, "pct": pct, "msg": msg, "hecho": bool(hecho), "cierra": "--cierra-trabajo" in a, "error": bool(hubo_error), "etapa": etapa}).encode("utf-8"), {"Content-Type": "application/json"}), timeout=3).read()
except Exception: pass
import cola; cola.avanzar() if hecho else None
print("ok", idea, pct, msg)
