"""Actualiza solo el progreso del panel mientras una grabacion corre (lee su log). Uso: python vigila_log.py LOG PROYECTO IDEA DURACION"""
import sys, re, time, subprocess, pathlib
log, pid, idea, dur = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3], float(sys.argv[4]); D = pathlib.Path(__file__).parent; ult = -1
while True:
    try: txt = log.read_text(encoding="utf-8", errors="replace")
    except Exception: txt = ""
    if "LISTO" in txt: break
    m = re.findall(r"\s*([\d.]+)s \(\d+s\)", txt)
    if m:
        t = float(m[-1]); pct = int(40 + 55 * min(1, t / dur))
        if pct != ult:
            ult = pct; subprocess.run([sys.executable, str(D / "progreso.py"), pid, "Grabando el juego", str(pct), "Grabado %.0f s de %.0f s del video mudo" % (t, dur)], capture_output=True)
            subprocess.run([sys.executable, str(D / "pedido.py"), idea, str(pct), "Grabando el juego mudo: %.0f de %.0f s" % (t, dur), "--proyecto", pid], capture_output=True)
    time.sleep(6)
