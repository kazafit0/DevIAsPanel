#!/usr/bin/env python3
# Instala en tu PC 3 voces masculinas en espanol para los render_video_*.py:
#   1) es_MX-claude-high  (Piper, Mexico, calidad alta)       -> se descarga a la carpeta voces_tts
#   2) em_alex            (Kokoro via HyperFrames, neutra)     -> se descarga con el modelo de Kokoro
#   3) em_santa           (Kokoro via HyperFrames, calida)     -> se descarga con el modelo de Kokoro
#   + es-MX-JorgeNeural (edge-tts, Jorge - Mexico): por INTERNET, el texto se envia al servicio de voz de Microsoft. Solo requiere pip install edge-tts.
# Opcional: python instalar_voces.py --extras   agrega es_ES-davefx-medium y es_MX-ald-medium (Piper).
#   OJO: esas dos estan entrenadas sobre una voz base de uso no comercial (Lessac); su propia tarjeta dice
#   CC0 / Unlicense, pero si monetizas conviene revisar la licencia antes de usarlas.
# Las voces de Piper quedan en  <tu carpeta de usuario>/voces_tts  y todos los videos las encuentran solas.
# Requisitos: Python 3.9+, internet (solo para instalar), Node.js 22+ (para Kokoro/HyperFrames).
# Uso:  python instalar_voces.py          (instala todo y prueba cada voz)
#       python instalar_voces.py --solo-piper | --solo-kokoro | --sin-prueba | --extras
import os, shutil, subprocess, sys, urllib.request
from pathlib import Path

DESTINO = Path.home() / 'voces_tts'
BASE = 'https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es'
PIPER = [  # (id, region, nombre, calidad, MB aprox., descripcion)
    ('es_MX-claude-high', 'es_MX', 'claude', 'high', 110, 'Claude - Mexico, calidad alta'),
]
EXTRAS = [
    ('es_ES-davefx-medium', 'es_ES', 'davefx', 'medium', 64, 'Davefx - Espana, calidad media'),
    ('es_MX-ald-medium', 'es_MX', 'ald', 'medium', 64, 'Ald - Mexico, calidad media'),
]
KOKORO = [('em_alex', 'Alex - neutra, natural'), ('em_santa', 'Santa - calida')]
FRASE = 'Hola. Esta es una prueba de voz para tus videos. Si me escuchas bien, ya podes usarme.'

args = sys.argv[1:]
SOLO_PIPER = '--solo-piper' in args
SOLO_KOKORO = '--solo-kokoro' in args
SOLO_EDGE = '--solo-edge' in args
SIN_PRUEBA = '--sin-prueba' in args
EXTRA = '--extras' in args


def run(cmd, **kw):
    cmd = [str(c) for c in cmd]
    if os.name == 'nt' and Path(cmd[0]).suffix.lower() in ('.cmd', '.bat'):
        return subprocess.run(subprocess.list2cmdline(cmd), shell=True, **kw)
    return subprocess.run(cmd, **kw)


def abrir(path):
    try:
        if os.name == 'nt':
            os.startfile(str(path))
        elif sys.platform == 'darwin':
            subprocess.run(['open', str(path)])
        else:
            subprocess.run(['xdg-open', str(path)])
    except Exception:
        print('  (abrí el archivo a mano para escucharlo):', path)


def descargar(url, destino, minimo_mb):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > minimo_mb * 1_000_000 * 0.5:
        print(f'  ya estaba: {destino.name}')
        return True
    tmp = destino.with_suffix(destino.suffix + '.part')
    ultimo = [-1]
    def prog(b, bs, total):
        if total > 0:
            p = min(100, int(b * bs * 100 / total))
            if p // 10 != ultimo[0]:
                ultimo[0] = p // 10
                print(f'  {destino.name}: {p}%')
    try:
        urllib.request.urlretrieve(url, tmp, prog)
        tmp.replace(destino)
        return True
    except Exception as ex:
        print(f'  NO se pudo descargar {destino.name}: {ex}')
        tmp.unlink(missing_ok=True)
        return False


def instalar_piper(voces):
    print('\n=== Piper (voces descargables) ===')
    r = run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'piper-tts'])
    if r.returncode != 0:
        print('NO se pudo instalar piper-tts con pip. Probá:  python -m pip install piper-tts\n'
              '(si tu Python es muy nuevo, probá con Python 3.11 o 3.12).')
        return []
    ok = []
    for vid, reg, nom, cal, mb, desc in voces:
        print(f'\nDescargando {desc} (~{mb} MB)...')
        u = f'{BASE}/{reg}/{nom}/{cal}/{vid}.onnx'
        a = descargar(u, DESTINO / f'{vid}.onnx', mb)
        b = descargar(u + '.json', DESTINO / f'{vid}.onnx.json', 0)
        if a and b:
            ok.append((vid, desc))
    return ok


def probar_piper(vid, desc):
    out = DESTINO / f'prueba_{vid}.wav'
    r = subprocess.run([sys.executable, '-m', 'piper', '-m', str(DESTINO / f'{vid}.onnx'), '-f', str(out)],
                       input=FRASE, text=True, encoding='utf-8', capture_output=True)
    if r.returncode != 0 or not out.exists():
        print(f'  FALLO la prueba de {vid}:', (r.stderr or '')[-300:])
        return False
    print(f'  OK {desc}: {out}')
    if not SIN_PRUEBA:
        abrir(out)
    return True


def instalar_kokoro():
    print('\n=== Kokoro / HyperFrames (em_alex y em_santa) ===')
    node = shutil.which('node.exe') or shutil.which('node')
    npx = shutil.which('npx.cmd') or shutil.which('npx')
    if not node or not npx:
        print('Falta Node.js 22+ (nodejs.org). Instalalo, cerrá y abrí la terminal y volvé a correr esto.')
        return []
    DESTINO.mkdir(exist_ok=True)
    txt = DESTINO / 'frase_prueba.txt'
    txt.write_text(FRASE, encoding='utf-8')
    ok = []
    for vid, desc in KOKORO:
        out = DESTINO / f'prueba_{vid}.wav'
        print(f'\nGenerando {vid} ({desc}); la primera vez baja el modelo (~340 MB), puede tardar...')
        r = run([npx, '--yes', 'hyperframes', 'tts', str(txt), '--voice', vid, '--output', str(out)])
        if r.returncode == 0 and out.exists() and out.stat().st_size > 4000:
            print(f'  OK {vid}: {out}')
            ok.append((vid, desc))
            if not SIN_PRUEBA:
                abrir(out)
        else:
            print(f'  FALLO {vid}. Revisa los mensajes de arriba (internet, Node 22+).')
    return ok


def instalar_edge():
    print('\n=== edge-tts (Jorge - Mexico, por internet) ===')
    r = run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'edge-tts', 'kokoro-onnx', 'soundfile'])
    if r.returncode != 0:
        print('NO se pudo instalar edge-tts con pip. Proba:  python -m pip install edge-tts')
        return []
    txt = DESTINO / 'frase_prueba.txt'
    txt.write_text(FRASE, encoding='utf-8')
    out = DESTINO / 'prueba_es-MX-JorgeNeural.mp3'
    r = subprocess.run([sys.executable, '-m', 'edge_tts', '--voice', 'es-MX-JorgeNeural', '--file', str(txt), '--write-media', str(out)], capture_output=True, text=True)
    if r.returncode == 0 and out.exists() and out.stat().st_size > 1000:
        print(f'  OK es-MX-JorgeNeural: {out}')
        if not SIN_PRUEBA:
            abrir(out)
        return [('es-MX-JorgeNeural', 'Jorge - Mexico')]
    print('  FALLO Jorge (necesita internet):', (r.stderr or '')[-200:])
    return []


def main():
    print('Instalador de voces masculinas en espanol')
    print('Carpeta de voces:', DESTINO)
    DESTINO.mkdir(parents=True, exist_ok=True)
    hechas = []
    if not SOLO_KOKORO and not SOLO_EDGE:
        voces = PIPER + (EXTRAS if EXTRA else [])
        for vid, desc in instalar_piper(voces):
            if probar_piper(vid, desc):
                hechas.append(f'{vid} (Piper)')
    if not SOLO_PIPER and not SOLO_EDGE:
        hechas += [f'{v} (Kokoro)' for v, _ in instalar_kokoro()]
    if not SOLO_PIPER and not SOLO_KOKORO:
        hechas += [f'{v} (edge-tts)' for v, _ in instalar_edge()]
    print('\n================ RESUMEN ================')
    if hechas:
        print('Voces listas:')
        for h in hechas:
            print('  -', h)
        print('\nAhora corre cualquier render_video_TEMA.py: te mostrara estas voces para elegir.')
    else:
        print('No quedo ninguna voz instalada. Revisa los mensajes de arriba y volve a correr el script.')
        sys.exit(1)


if __name__ == '__main__':
    main()
