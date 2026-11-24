"""Capturas (8 fotogramas) del video mudo -> CARPETA/miniaturas/NN.jpg. CADA vez que se pide salen OTRAS distintas (momentos al azar, nunca los mismos que la tanda anterior).
Uso: python capturas_ffmpeg.py CARPETA VIDEO_RELATIVO"""
import sys, pathlib, subprocess, json, random, time, re, imageio_ffmpeg
c = pathlib.Path(sys.argv[1]); v = c / sys.argv[2]; out = c / "miniaturas"; out.mkdir(exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe(); r = subprocess.run([FF, "-i", str(v)], capture_output=True, text=True).stderr
m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r); dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
prev_f = out / "_anteriores.json"
try: prev = json.loads(prev_f.read_text())
except Exception: prev = []
rnd = random.Random(time.time_ns()); tiempos = []
for k in range(8):   # un momento al azar dentro de cada octavo del video (así cubre todo el vídeo), lejos de los de la tanda anterior
    for intento in range(40):
        t = dur * (k + .08 + .84 * rnd.random()) / 8
        if all(abs(t - p) > 1.2 for p in prev): break
    tiempos.append(t)
for f in out.glob("*.jpg"): f.unlink()
stamp = int(time.time())
for k, t in enumerate(tiempos, 1):
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", "%.2f" % t, "-i", str(v), "-frames:v", "1", "-q:v", "2", str(out / ("%02d_%d.jpg" % (k, stamp)))], check=True); print("captura", k, "%.1f s" % t, flush=True)
prev_f.write_text(json.dumps([round(t, 2) for t in tiempos + prev][:24]))
print("LISTO")
