"""REGRABAR SOLO UN TRAMO (2026-11-19): cuando cambia un detalle de unas escenas, no hace falta grabar todo el video.
Graba únicamente [DESDE, HASTA] (ajustado a los cuadros clave del video existente) y lo pega con ffmpeg SIN recodificar el resto.
Uso: python regrabar_tramo.py CARPETA SEED DESDE HASTA [--tag _completo] [--salida RUTA.mp4] [--workers N]
  · Sin --salida reemplaza CARPETA/salida_mudo/s{SEED}{TAG}.mp4 (deja copia .anterior.mp4).
  · La velocidad (30 o 20 fps) se toma del video existente; el tramo se graba con la misma.
Probado: el resultado es idéntico al original en todos los puntos (diferencia 0,00) cuando no hay cambios."""
import os, sys, re, argparse, pathlib, subprocess, shutil, time
os.environ["TEMP"] = os.environ["TMP"] = os.environ.get("DEVPANEL_TMP") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_tmp")
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); D = pathlib.Path(__file__).resolve().parent
def sh(cmd, **kw): return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
def info(v):
    t = sh([FF, "-i", str(v)]).stderr; m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", t); f = re.search(r"([\d.]+) fps", t)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)), float(f.group(1)) if f else 30.0
def clave(v):   # segundos de los cuadros clave (I) del video
    t = sh([FF, "-skip_frame", "nokey", "-i", str(v), "-vf", "showinfo", "-an", "-f", "null", "-"]).stderr
    return sorted(set(round(float(x), 3) for x in re.findall(r"pts_time:([\d.]+)", t)))
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("carpeta"); ap.add_argument("seed", type=int); ap.add_argument("desde", type=float); ap.add_argument("hasta", type=float)
    ap.add_argument("--tag", default="_completo"); ap.add_argument("--salida", default=""); ap.add_argument("--workers", type=int, default=0); a = ap.parse_args()
    R = pathlib.Path(a.carpeta).resolve(); V = R / "salida_mudo" / ("s%d%s.mp4" % (a.seed, a.tag))
    if not V.exists(): sys.exit("No existe el video a parchear: %s (primero graba el video completo)" % V)
    dur, fps = info(V); ks = clave(V)
    if not ks: sys.exit("No encontré cuadros clave en el video.")
    k1 = max([k for k in ks if k <= a.desde] or [0.0]); k2 = min([k for k in ks if k >= a.hasta] or [dur])
    print("Video existente: %.1f s a %.0f fps · cuadros clave cada ~%.1f s · tramo pedido %.1f-%.1f s -> regrabo %.2f-%.2f s" % (dur, fps, (ks[-1] - ks[0]) / max(1, len(ks) - 1), a.desde, a.hasta, k1, k2), flush=True)
    mbps = "20" if fps >= 25 else "12"; env = dict(os.environ, GRAB_FPS=str(int(round(fps))), GRAB_MBPS=mbps); env.setdefault("GRAB_W", "1920" if R.name and (R / "game.js").exists() and "16x9" in open(R / "game_head.js", encoding="utf-8").read(2000) else env.get("GRAB_W", "1080"))
    tag_t = "_tramo"; T = R / "salida_mudo" / ("s%d%s.mp4" % (a.seed, tag_t))
    if T.exists(): T.unlink()
    w = a.workers or (2 if (k2 - k1) > 12 else 1)
    r = subprocess.run([sys.executable, "-u", str(D / "grab_gpu.py"), str(R), str(a.seed), "--tag", tag_t, "--desde", "%.3f" % k1, "--hasta", "%.3f" % k2, "--workers", str(w), "--fps", str(int(round(fps))), "--mbps", mbps], env=env)
    if r.returncode != 0 or not T.exists(): sys.exit("Falló la grabación del tramo.")
    tmp = pathlib.Path(os.environ.get("DEVPANEL_TMP") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_tmp")) / ("tramo_%d" % int(time.time())); tmp.mkdir(parents=True, exist_ok=True); partes = []
    if k1 > 0.01:
        A = tmp / "a.mp4"; sh([FF, "-y", "-loglevel", "error", "-i", str(V), "-t", "%.3f" % k1, "-c", "copy", str(A)]); partes.append(A)
    partes.append(T)
    if k2 < dur - 0.01:
        C = tmp / "c.mp4"; sh([FF, "-y", "-loglevel", "error", "-ss", "%.3f" % k2, "-i", str(V), "-c", "copy", str(C)]); partes.append(C)
    lst = tmp / "lista.txt"; lst.write_text("".join("file '%s'\n" % str(p).replace("\\", "/") for p in partes), encoding="utf-8")
    out = pathlib.Path(a.salida) if a.salida else tmp / "pegado.mp4"
    rr = sh([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])
    if rr.returncode != 0: sys.exit("Falló el pegado: " + rr.stderr[-300:])
    nd, _ = info(out)
    if abs(nd - dur) > 0.6: sys.exit("El video pegado dura %.2f s y el original %.2f s: no lo reemplazo." % (nd, dur))
    if not a.salida:
        shutil.copy(V, V.with_suffix(".anterior.mp4")); shutil.copy(out, V)
    T.unlink(missing_ok=True); print("LISTO tramo %.2f-%.2f s pegado: %.2f s (original %.2f s)%s" % (k1, k2, nd, dur, "" if a.salida else " · copia previa: " + V.with_suffix(".anterior.mp4").name), flush=True)
main()
