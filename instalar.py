"""INSTALADOR DEL DEVIAS PANEL (antes DevPanel). Al instalarlo (o al ejecutarlo de nuevo) deja todo listo para encenderlo a mano:
  · crea las carpetas y los archivos de datos que falten (plugins/, series/, titulos/, _tmp/ …),
  · comprueba Python y los paquetes (y los instala si pasas --instalar-paquetes),
  · genera  iniciar_devpanel.bat  (enciende el panel y abre el navegador)  y  detener_devpanel.bat,
  · opcional --acceso-directo: crea «DevPanel» en el escritorio.
Uso:  python instalar.py [--puerto 8820] [--instalar-paquetes] [--acceso-directo]      (o doble clic en instalar.bat)
Las rutas se calculan desde la carpeta donde está este archivo: se puede copiar el DevPanel a cualquier lugar y volver a instalar."""
import os, sys, json, time, socket, shutil, argparse, pathlib, subprocess, importlib.util
AQUI = pathlib.Path(__file__).resolve().parent
PAQUETES = [("playwright", "playwright"), ("PIL", "pillow"), ("numpy", "numpy"), ("imageio_ffmpeg", "imageio-ffmpeg")]
DATOS = ["catalogo.json", "pedidos.json", "proyectos.json", "referencias.json", "actividad.json", "banco.json", "banco_original.json"]
def puerto_libre(p):
    for q in range(p, p + 30):
        with socket.socket() as s:
            s.settimeout(.3)
            if s.connect_ex(("127.0.0.1", q)) != 0: return q
    return p
def _vs_auto():   # dónde está Voice Studio si no se dijo en devpanel.json -> "voice_studio_dir" (sin rutas de nadie): variable VOICESTUDIO_DIR o sitios habituales
    import os
    for b in (os.environ.get("VOICESTUDIO_DIR"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "VoiceStudio"), os.path.join(os.environ.get("ProgramFiles", ""), "VoiceStudio"), os.path.join(os.path.expanduser("~"), "VoiceStudio")):
        if b:
            for sub in ("project", ""):
                p = pathlib.Path(b) / sub if sub else pathlib.Path(b)
                if (p / ".venv").exists() or (p / "data").exists(): return p
    return pathlib.Path(os.path.expanduser("~")) / "VoiceStudio" / "project"
def voice_studio_estado():   # ¿está Voice Studio instalado? (lo instala el usuario A MANO: el instalador solo lo detecta)
    import urllib.request
    cfg = {}
    try: cfg = json.loads((AQUI / "devpanel.json").read_text(encoding="utf-8"))
    except Exception: pass
    ruta = pathlib.Path(cfg.get("voice_studio_dir") or _vs_auto())
    enc = False
    try: urllib.request.urlopen("http://127.0.0.1:3900/openapi.json", timeout=1.5); enc = True
    except Exception: pass
    return {"instalado": bool(enc or ruta.exists()), "ruta": str(ruta), "encendido": enc}
def estado():   # lo usa el skill de instalación: qué falta, en JSON
    falta = comprobar_paquetes(); chromium = False
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw: chromium = pathlib.Path(pw.chromium.executable_path).exists()
    except Exception: pass
    return {"python": sys.version.split()[0], "python_ok": sys.version_info >= (3, 10), "paquetes_faltan": [p for _, p in falta], "chromium": chromium, "voice_studio": voice_studio_estado(), "carpeta": str(AQUI)}
def comprobar_paquetes():
    return [(m, pip) for m, pip in PAQUETES if importlib.util.find_spec(m) is None]
def escribe(path, txt):
    p = AQUI / path
    if p.exists():
        try: shutil.copy(p, str(p) + ".bak")
        except Exception: pass
    p.write_text(txt, encoding="utf-8", newline="\r\n")
def generar_bats(py, puerto):
    escribe("iniciar_devpanel.bat", f'''@echo off
rem DEVIAS PANEL: enciende el panel (puerto {puerto}). Generado por instalar.py; si mueves la carpeta, vuelve a ejecutar instalar.bat.
setlocal
cd /d "%~dp0"
set "DEVPANEL_TMP=%~dp0_tmp"
if not exist "%DEVPANEL_TMP%" mkdir "%DEVPANEL_TMP%"
set "TEMP=%DEVPANEL_TMP%"
set "TMP=%DEVPANEL_TMP%"
set "PYTHONIOENCODING=utf-8"
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort {puerto} -State Listen -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}"
if %errorlevel%==0 (
  echo El DevIAs Panel ya esta encendido en el puerto {puerto}.
) else (
  start "DevIAs Panel (servidor)" /min "{py}" -X utf8 "%~dp0servidor.py" {puerto}
  timeout /t 3 /nobreak >nul
)
start "" http://localhost:{puerto}/static/admin.html
''')
    escribe("detener_devpanel.bat", f'''@echo off
rem DEVIAS PANEL: apaga el panel (puerto {puerto}).
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort {puerto} -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"
echo DevIAs Panel apagado.
timeout /t 2 /nobreak >nul
''')
def acceso_directo():
    bat = AQUI / "iniciar_devpanel.bat"
    ps = f'$d=[Environment]::GetFolderPath("Desktop"); $s=(New-Object -ComObject WScript.Shell).CreateShortcut("$d\\DevIAs Panel.lnk"); $s.TargetPath="{bat}"; $s.WorkingDirectory="{AQUI}"; $s.Save()'
    return subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True).returncode == 0
def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--puerto", type=int, default=0); ap.add_argument("--instalar-paquetes", action="store_true"); ap.add_argument("--acceso-directo", action="store_true"); ap.add_argument("--temp", default="", help="carpeta de temporales (por defecto _tmp dentro del panel)"); ap.add_argument("--estado", action="store_true", help="imprime en JSON qué está instalado y qué falta (lo usa el skill)"); a = ap.parse_args(argv)
    if a.estado: print(json.dumps(estado(), ensure_ascii=False)); return
    print("== Instalando el DevIAs Panel en:", AQUI)
    if sys.version_info < (3, 10): print("AVISO: se recomienda Python 3.10 o superior (tienes %s)." % sys.version.split()[0])
    for d in ("plugins", "series", "titulos", "miniaturas", "_tmp", "grabador"): (AQUI / d).mkdir(exist_ok=True)
    for f in DATOS:
        if not (AQUI / f).exists(): (AQUI / f).write_text("[]", encoding="utf-8")
    if not (AQUI / "plugins_estado.json").exists(): (AQUI / "plugins_estado.json").write_text("{}", encoding="utf-8")
    falta = comprobar_paquetes()
    if falta and a.instalar_paquetes:
        print("Instalando paquetes:", ", ".join(p for _, p in falta)); r = subprocess.run([sys.executable, "-m", "pip", "install", *[p for _, p in falta]])
        if "playwright" in [p for _, p in falta] and r.returncode == 0: subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        falta = comprobar_paquetes()
    cfg_f = AQUI / "devpanel.json"; cfg = json.loads(cfg_f.read_text(encoding="utf-8")) if cfg_f.exists() else {}
    puerto = a.puerto or cfg.get("puerto") or puerto_libre(8820)
    cfg.setdefault("senal_min", 30)
    if a.temp: pathlib.Path(a.temp).mkdir(parents=True, exist_ok=True); cfg["temp_dir"] = a.temp
    if not cfg.get("instalado"): cfg["primer_uso"] = True   # la primera vez el panel muestra el popup de bienvenida (señal de conexión)
    cfg.update({"puerto": puerto, "ruta": str(AQUI), "python": sys.executable, "instalado": time.strftime("%Y-%m-%d %H:%M:%S")}); cfg_f.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    generar_bats(sys.executable, puerto)
    ok_lnk = acceso_directo() if a.acceso_directo else None
    print("\nListo.\n  · Para ENCENDER el panel: doble clic en  iniciar_devpanel.bat   (abre http://localhost:%d/static/admin.html)\n  · Para APAGARLO:          doble clic en  detener_devpanel.bat" % puerto)
    if a.acceso_directo: print("  · Acceso directo «DevIAs Panel» en el escritorio:", "creado" if ok_lnk else "no se pudo crear")
    if falta: print("\nFALTAN paquetes de Python: %s\n  Instálalos con:  python instalar.py --instalar-paquetes" % ", ".join(p for _, p in falta))
    print("\n== Comprobando requisitos (voz, tarjeta de video, navegador…) =="); subprocess.run([sys.executable, str(AQUI / "requisitos.py")])
    vs = voice_studio_estado(); print("\nVOICE_STUDIO: " + ("instalado" if vs["instalado"] else "FALTA: hay que instalarlo A MANO (el instalador no puede hacerlo por ti)"))
    print("\nLos plugins se ponen en la carpeta plugins/ (cada uno con su plugin.json); aparecerán en la pestaña Plugins.")
    return {"puerto": puerto, "faltan": [p for _, p in falta], "bat": str(AQUI / "iniciar_devpanel.bat")}
if __name__ == "__main__": main()
