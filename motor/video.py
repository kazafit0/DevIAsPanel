"""MOTOR DE VIDEO DEL DEVPANEL — biblioteca ÚNICA que usan los pipelines de TODOS los plugins. (2026-11-21)
El panel se encarga de: RENDER (grabador rápido con la tarjeta de video y trabajadores en paralelo, borrador a 20 fps, final a 30 fps, regrabar un tramo, huella para no regrabar si nada cambió),
VOZ (motor/voz_partes.py), MEZCLA (motor/mezcla.py), UNIÓN (concat), MÚSICA de fondo, registro del video en el panel y avance de cada etapa.
El plugin solo aporta lo suyo: el juego/escena (la página que se graba), el guion, los datos de sonido y, en su pipeline, la «receta» (qué etapas y en qué orden).
Uso desde un pipeline de plugin:
    import sys, os, pathlib; sys.path.insert(0, str(pathlib.Path(os.environ["DEVPANEL"]) / "motor")); import video as V
    P = V.Proyecto(sys.argv[1], sys.argv[2])        # carpeta del video y etapa (borrador | voz | parte | conforme | unir | tramo)
    P.voz(["--borrador"]); d = P.grabar(rapido=True, archivos=("game.js",)); P.registrar("borrador", dur=d, pct=40, msg="…")"""
import os, sys, json, re, time, shutil, pathlib, subprocess, hashlib
os.environ["TEMP"] = os.environ["TMP"] = os.environ.get("DEVPANEL_TMP") or os.environ.get("TEMP") or "."
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); PANEL = pathlib.Path(__file__).resolve().parent.parent; PYX = [sys.executable, "-X", "utf8"]
def jl(p, d=None):
    try: return json.loads(pathlib.Path(p).read_text(encoding="utf8"))
    except Exception: return d
def js(p, o): pathlib.Path(p).write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf8")
class Proyecto:
    def __init__(self, carpeta, etapa="borrador", plugin_dir=None):
        self.R = pathlib.Path(carpeta).resolve(); self.ET = etapa; self.PLUGIN = pathlib.Path(plugin_dir or os.environ["PLUGIN_DIR"]).resolve()
        self.META = json.loads((self.R / "proyecto.json").read_text(encoding="utf8")); self.PID = self.META["id"]; self.IDEA = self.META.get("idea"); self.SEED = str(self.META.get("seed", 1)); self.TAG = "_completo"
        self.MUDO = "salida_mudo/s%s%s.mp4" % (self.SEED, self.TAG)
        ficha = jl(self.PLUGIN / "plugin.json", {}); self.AJ = dict({a["id"]: a.get("defecto") for a in ficha.get("ajustes", [])}, **json.loads(os.environ.get("PLUGIN_AJUSTES") or "{}"))
        self.VOZ_MODO = (ficha.get("voz") or {}).get("modo", "json_manda"); self.TIEMPOS = ficha.get("tiempos", "guion"); self.ENV = dict(os.environ)
        if self.META.get("aspecto") == "16:9": self.ENV["GRAB_W"], self.ENV["GRAB_H"] = "1920", "1080"
        self.BORRADOR_RAPIDO = str(self.AJ.get("borrador_calidad", self.AJ.get("borrador_fps", "rápido"))).startswith("rápido")
    # ---------- avance y registro en el panel ----------
    def avance(self, pct, msg, etapa=None, cierra=False):
        print("[%d%%] %s" % (pct, msg), flush=True)
        if self.IDEA:
            if not etapa and self.ET == "borrador": etapa = 6 if pct <= 10 else 7 if pct <= 30 else 8   # el CEREBRO del panel sigue estas etapas
            ex = (["--etapa", str(etapa)] if etapa else []) + (["--cierra-trabajo"] if cierra else []) + (["--hecho", "--proyecto", self.PID] if (self.ET == "borrador" and pct >= 40) else [])
            subprocess.run(PYX + ["pedido.py", self.IDEA, str(pct), msg] + ex, cwd=str(PANEL), capture_output=True)
        try:
            P = PANEL / "proyectos.json"; pr = json.loads(P.read_text(encoding="utf8"))
            for x in pr:
                if x["id"] == self.PID and pct < 100: x["progreso"] = {"etapa": x.get("estado", "en_proceso"), "pct": pct, "msg": msg, "act": time.strftime("%Y-%m-%d %H:%M:%S")}
            P.write_text(json.dumps(pr, ensure_ascii=False, indent=1), encoding="utf8")
        except Exception as e: print("aviso progreso:", e)
    def dur_video(self, p):
        m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", subprocess.run([FF, "-i", str(p)], capture_output=True, text=True).stderr); return round(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)), 2)
    def registrar(self, estado, video_final=None, escenas=None, dur=None, pct=100, msg=""):
        P = PANEL / "proyectos.json"; pr = json.loads(P.read_text(encoding="utf8")); cur = next((x for x in pr if x["id"] == self.PID), None)
        if cur is None: cur = {"seed": int(self.SEED), "tag": self.TAG, "guion": "guion/1.json", "video_mudo": self.MUDO, "juego": "index.html?seed=%s&play=1" % self.SEED, "escenas": [], "mejoras": [], "voz_metodo": "audiolibro", "plugin": self.PLUGIN.name}
        if estado == "borrador" and cur.get("video_final") and cur.get("unido_ok"):   # un video YA UNIDO no vuelve a «borrador» por regenerar la voz o regrabar el borrador: sigue «listo» y avisa si hay que unir de nuevo
            estado = "listo"; cur["voz_cambiada"] = True; msg = "El video final ya existe. Cambiaste la voz o el borrador después de unir: pulsa «Unir con la voz» si quieres que el final los lleve."; pct = 100
        elif estado == "listo": cur.pop("voz_cambiada", None)
        cur.update({"id": self.PID, "titulo": self.META["titulo"], "carpeta": self.R.name, "formato": self.META.get("formato", "short"), "seed": int(self.SEED), "tag": self.TAG, "video_mudo": self.MUDO, "mudo_t": int(time.time()), "estado": estado, "momentos": self.META.get("momentos", cur.get("momentos", [])), "paises": self.META.get("paises", cur.get("paises", [])), "seo": self.META.get("seo", cur.get("seo", {})), "plugin": self.PLUGIN.name})
        for k in ("aspecto", "categoria", "ganador", "senuelos"):
            if self.META.get(k): cur[k] = self.META[k]
        if self.IDEA: cur["idea"] = self.IDEA   # el panel enlaza el video EN ESPERA con el proyecto real por la idea
        if dur: cur["duracion"] = dur
        if video_final: cur.update({"video_final": video_final, "unido_ok": True, "unido_t": int(time.time()), "escenas": escenas or [{"n": 1, "titulo": self.META["titulo"], "desde": 0, "hasta": dur or 0, "estado": "lista", "video": video_final}]})   # unido_t = ?v= del video: sin él el navegador mostraba el video VIEJO
        for k_ in ("video_final", "video_mudo"):
            if k_ in cur and cur[k_] is None: del cur[k_]
        cur["progreso"] = {"etapa": estado, "pct": pct, "msg": msg, "act": time.strftime("%Y-%m-%d %H:%M:%S")}
        js(P, [x for x in pr if x["id"] != self.PID and x["id"] != "esp-" + str(self.IDEA)] + [cur])   # el marcador «en espera» desaparece cuando el video real existe
        if estado == "listo" and self.IDEA:   # la idea del video terminado pasa a «hecho» (antes se quedaba en «espera»)
            try:
                C = PANEL / "catalogo.json"; cat = json.loads(C.read_text(encoding="utf8"))
                for it in cat:
                    if it.get("id") == self.IDEA: it["estado"] = "hecho"; it["proyecto"] = self.PID
                C.write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf8")
            except Exception as e_: print("aviso catálogo:", e_)
    def registra_borrador_voz(self):
        try:
            P_ = PANEL / "proyectos.json"; pr_ = json.loads(P_.read_text(encoding="utf8"))
            for x_ in pr_:
                if x_["id"] == self.PID and (self.R / "salida_mudo" / "borrador_voz.mp4").exists(): x_["borrador_voz"] = "salida_mudo/borrador_voz.mp4"; x_["borrador_voz_t"] = int(time.time())
            P_.write_text(json.dumps(pr_, ensure_ascii=False, indent=1), encoding="utf8")
        except Exception as e_: print("aviso:", e_)
    # ---------- RENDER ----------
    def tiempos(self): return json.loads((self.R / "audiolibro" / "tiempos.json").read_text(encoding="utf8"))
    def huella(self, archivos):
        g = jl(self.R / "guion" / "1.json", []); t = jl(self.R / "audiolibro" / "tiempos.json", {"tags": {}}); tg = t.get("tags", {})
        h = hashlib.md5(json.dumps([[x.get("key"), round(float(x.get("t", 0)), 2)] for x in g] + [[k, [round(float(v), 2) for v in vv]] for k, vv in sorted(tg.items())] + [bool(t.get("estimado"))]).encode())
        for f in archivos:
            if (self.R / f).exists(): h.update((self.R / f).read_bytes())
        return h.hexdigest()
    def grabar(self, rapido=False, forzar=False, archivos=("game.js",)):
        """Graba el video mudo con el grabador del DevIAs Panel. rapido=True (BORRADOR): 20 fps. Los finales siempre a 30 fps. Si lo que dibuja el video no cambió, NO se regraba."""
        hf = self.R / "salida_mudo" / "_tiempos.hash"; v = self.R / self.MUDO; v.parent.mkdir(exist_ok=True); hc = self.huella(archivos); hr = hc + "-r"; hcc = hc + "-c"
        h_ = hf.read_text() if hf.exists() else ""; ok = (h_ in (hr, hcc)) if rapido else (h_ == hcc)   # un borrador rápido NUNCA se reutiliza como final; un completo sí sirve de borrador
        if not forzar and v.exists() and ok: print("video mudo al día: lo que lo dibuja no cambió, NO se vuelve a grabar", flush=True); return self.dur_video(v)
        self.ENV.pop("GRAB_FPS", None); self.ENV.pop("GRAB_MBPS", None)
        if rapido: self.ENV["GRAB_FPS"], self.ENV["GRAB_MBPS"] = "20", "12"
        r = subprocess.run(PYX + ["-u", str(PANEL / "grabador" / "grabar_rapido.py"), str(self.R), self.SEED, "--tag", self.TAG], cwd=str(self.R), env=self.ENV)
        if r.returncode != 0: sys.exit("El grabador falló: revisa el registro de arriba.")
        hf.write_text(hr if rapido else hcc); return self.dur_video(v)
    def tramo(self, desde, hasta, archivos=("game.js",)):
        """Regraba SOLO un tramo y lo pega; el resto del video no se toca."""
        hf = self.R / "salida_mudo" / "_tiempos.hash"; suf = "-r" if hf.exists() and hf.read_text().endswith("-r") else "-c"
        r = subprocess.run(PYX + [str(PANEL / "grabador" / "regrabar_tramo.py"), str(self.R), self.SEED, str(desde), str(hasta)], cwd=str(self.R), env=self.ENV)
        if r.returncode != 0: sys.exit("No se pudo regrabar el tramo.")
        hf.write_text(self.huella(archivos) + suf)
    # ---------- VOZ ----------
    def voz(self, extra=()):
        r = subprocess.run(PYX + [str(PANEL / "motor" / "voz_partes.py"), str(self.R), *extra], cwd=str(self.R), env=dict(self.ENV, PLUGIN_DIR=str(self.PLUGIN)))
        if r.returncode != 0:
            hechas = len(list((self.R / "audiolibro" / "partes").glob("*.npz"))) if (self.R / "audiolibro" / "partes").exists() else 0
            sys.exit("La voz se cortó (¿Voice Studio abierto, o se movió/renombró la carpeta del video?). Las %d partes ya hechas se conservan: vuelve a pulsar «Generar voz» y solo hará las que faltan." % hechas)
        if "--borrador" not in extra and self.tiempos().get("estimado"): sys.exit("La voz no quedó medida (tiempos aún estimados).")
    # ---------- MÚSICA, MEZCLA, UNIÓN ----------
    def musica(self):
        """Instala el mp3 de fondo (ajuste «musica_archivo» del plugin) en music/bgm.wav (24 kHz mono) + creditos.json con la ganancia."""
        src = pathlib.Path(str(self.AJ.get("musica_archivo") or "")); out = self.R / "music"
        if not str(self.AJ.get("musica_archivo") or "").strip() or not src.is_file(): print("sin música de fondo (ajuste vacío o archivo inexistente: %s)" % src, flush=True); return False
        out.mkdir(exist_ok=True); subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(src), "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(out / "bgm.wav")], check=True)
        js(out / "creditos.json", {"nombre": src.stem, "ganancia": float(self.AJ.get("musica_ganancia", .6))}); print("música de fondo: %s (ganancia %s)" % (src.name, self.AJ.get("musica_ganancia")), flush=True); return True
    def sfx(self):
        """EFECTOS DE SONIDO: baja de Freesound (solo CC0) los que piden sfx_cues.json / sfx_plan.json, con la «Clave API de Freesound» del plugin (ajuste freesound_key). NO frena la unión: sin clave el video se une sin efectos y lo avisa."""
        self.avance(78, "Efectos de sonido: preparando los que pide el video (Freesound, solo CC0).")
        env = dict(self.ENV); k = str(self.AJ.get("freesound_key") or "").strip()
        if k: env["FREESOUND_KEY"] = k
        try: subprocess.run(PYX + [str(PANEL / "motor" / "sfx_freesound.py"), str(self.R), str(self.PLUGIN / "base" / "sfx" / "catalogo.json")], cwd=str(self.R), env=env, timeout=300)
        except Exception as e: print("AVISO: efectos de sonido no preparados (%s); la unión sigue sin ellos." % e, flush=True)
    def pega_voz(self, destino, musica=False):
        """Video mudo + voz (+ música de fondo) sin volver a grabar."""
        ent = ["-i", str(self.R / self.MUDO), "-i", str(self.R / "voz" / "voz_completa.wav")]; bgm = self.R / "music" / "bgm.wav"
        if musica and bgm.exists():
            g = float((jl(self.R / "music" / "creditos.json", {}) or {}).get("ganancia", .6)); ent += ["-stream_loop", "-1", "-i", str(bgm)]
            mapa = ["-filter_complex", "[2:a]volume=%s[m];[1:a][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]" % g, "-map", "0:v:0", "-map", "[a]"]
        else: mapa = ["-map", "0:v:0", "-map", "1:a:0"]
        pathlib.Path(destino).parent.mkdir(exist_ok=True); r = subprocess.run([FF, "-y", "-loglevel", "error", *ent, *mapa, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(destino)], capture_output=True, text=True)
        if r.returncode != 0: print("aviso: no pude pegar la voz:", r.stderr[-300:]); return False
        return True
    def borrador_con_voz(self):
        ok = self.pega_voz(self.R / "salida_mudo" / "borrador_voz.mp4")
        if ok: self.registra_borrador_voz()
        return ok
    def escenas(self, dur):
        """escenas.json del proyecto (las define el plugin); si no hay, una sola escena con todo el video."""
        E = jl(self.R / "escenas.json", None)
        if not E: E = [{"n": 1, "titulo": self.META["titulo"], "desde": 0, "hasta": dur}]; js(self.R / "escenas.json", E)
        return E
    def mezclar(self, dur, pct0=80, pct1=92):
        """Mezcla cada escena (voz + efectos + música) con el motor de mezcla y las une en salida/<id>_completo.mp4. -> (ruta relativa, lista de escenas) o (None, None) si falla."""
        E = self.escenas(dur); out = []
        for k, e in enumerate(E):
            self.avance(pct0 + int((pct1 - pct0) * (k + 1) / len(E)), "Unión: mezclando voz, efectos y música, escena %d de %d." % (k + 1, len(E)))
            r = subprocess.run(PYX + [str(PANEL / "motor" / "mezcla.py"), str(self.R), str(e["n"]), ""], cwd=str(self.R), env=self.ENV, capture_output=True, text=True, encoding="utf-8", errors="replace"); print((r.stdout.strip().splitlines() or [r.stderr[-200:]])[-1], flush=True)
            v = self.R / "salida" / ("escena_%02d.mp4" % e["n"])
            if r.returncode != 0 or not v.exists(): print("aviso: falló la mezcla de la escena %d: %s" % (e["n"], r.stderr[-300:]), flush=True); return None, None
            out.append({"n": e["n"], "titulo": e.get("titulo", "Escena %d" % e["n"]), "desde": e["desde"], "hasta": e["hasta"], "estado": "lista", "video": "salida/escena_%02d.mp4" % e["n"]})
        lst = pathlib.Path(os.environ["TEMP"]) / ("unir_%s.txt" % self.PID); lst.write_text("".join("file '%s'\n" % str(self.R / x["video"]).replace(chr(92), "/") for x in out), encoding="utf8")
        rel = "salida/%s_completo.mp4" % self.PID; subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(self.R / rel)], check=True); return rel, out
    def termina(self, rel, escenas, dur):
        """Cierra el video: registro «listo», título/SEO viejos fuera y pedido hecho."""
        for t in (PANEL / "titulos").glob(self.PID + ".json"): t.unlink()
        self.registrar("listo", video_final=rel, escenas=escenas, dur=dur, pct=100, msg="Video listo con voz y música"); self.avance(100, "Video listo (%.0f s) con voz y música." % dur)
        if self.IDEA: subprocess.run(PYX + ["pedido.py", self.IDEA, "100", "Video listo (%.0f s) con voz y música." % dur, "--hecho", "--proyecto", self.PID], cwd=str(PANEL), capture_output=True)
