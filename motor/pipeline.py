"""FLUJO ÚNICO DEL DEVPANEL (el de Mapas, el más rápido y el que mejor funciona) — lo corren los pipelines de TODOS los plugins. (2026-11-21)
    borrador : tiempos ESTIMADOS desde el guion -> se graba la escena muda (20 fps) -> el usuario la revisa en el panel.
    voz/parte: voz real (la inicia el usuario) -> los tiempos pasan a ser REALES -> se regraba el borrador para que coincida -> «borrador con voz».
    conforme/unir: grabación FINAL (30 fps) + música + mezcla por escenas (voz, efectos, música) -> unión -> video listo.
Regla del plugin (plugin.json -> «tiempos»): «guion» = la escena se adapta a los tiempos del guion (así funciona Mapas); «juego» = el juego marca sus propios segundos y el guion se escribe desde sus eventos (no se estima ni se regraba).
La receta del plugin (su pipeline) es un diccionario con funciones opcionales:
    archivos      tuple  archivos que dibujan el video (huella: si no cambian, no se regraba)
    preparar(P)          antes de todo (armar game.js, copiar plantilla, comprobar que existe la escena)
    tras_tiempos(P)      después de que haya tiempos nuevos (estimados o reales), p. ej. escribir timeline.js
    escenas(P, fin)      -> lista [{n, titulo, desde, hasta}] para la mezcla (por defecto: escenas.json del proyecto o una sola escena)
    grabacion            "pagina" si la escena lleva HUD en HTML (se graba la página entera)
Uso en un pipeline de plugin:  sys.path.insert(0, DEVPANEL/motor); import pipeline; pipeline.correr({...})"""
import os, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import video as V
def correr(receta):
    P = V.Proyecto(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "borrador"); ET = P.ET; ARCH = tuple(receta.get("archivos", ("game.js",))); estima = P.TIEMPOS == "guion"
    if receta.get("grabacion") == "pagina": P.ENV["GRAB_MODO"] = "pagina"
    hook = lambda nombre, *a: receta[nombre](*a) if receta.get(nombre) else None
    if ET == "todo": sys.exit("La etapa «todo» está DESACTIVADA: el usuario revisa el borrador y aprueba antes de generar la voz. Usa «borrador»; cuando él marque «conforme» (botón del panel), corre «conforme» (= voz + unir).")
    hook("preparar", P)
    if ET == "tramo": P.tramo(sys.argv[3], sys.argv[4], ARCH); P.avance(40, "Tramo %s-%s s regrabado y pegado (el resto del video no se tocó)." % (sys.argv[3], sys.argv[4]), cierra=True); return
    if ET == "borrador":
        P.registrar("en_proceso", pct=5, msg="Borrador: preparando el video (aún sin video para ver)")   # el proyecto aparece en el panel DESDE EL PRINCIPIO
        if estima: P.avance(5, "Borrador: calculando los tiempos estimados desde el guion."); P.voz(["--borrador"]); hook("tras_tiempos", P)
        P.avance(15, "Borrador: grabando el video mudo%s." % (" con tiempos estimados (sin voz)" if estima else " (los tiempos los marca el juego)")); d = P.grabar(P.BORRADOR_RAPIDO, archivos=ARCH)
        P.registrar("borrador", dur=d, pct=40, msg="BORRADOR mudo con subtítulos en el panel: revísalo y avisa si estás conforme para generar la voz.")
        P.avance(40, "BORRADOR listo (%.0f s, sin voz). Revísalo en el panel (subtítulos): si estás conforme, genero la voz." % d); return
    if ET in ("voz", "parte", "conforme", "unir"):
        if ET != "unir":
            P.avance(45, "Voz: generando por partes (solo lo nuevo o cambiado)."); P.voz(["--parte"] + sys.argv[3:] if (ET in ("parte", "voz") and sys.argv[3:]) else []); hook("tras_tiempos", P); P.avance(70, "Voz lista y medida (%.0f s)." % P.tiempos()["dur"])
        elif P.tiempos().get("estimado"): sys.exit("Primero la etapa voz: los tiempos todavía son estimados.")
        if ET in ("voz", "parte"):   # SINCRONÍA: el borrador se regraba con los tiempos reales de la voz y se le pega la voz -> salida_mudo/borrador_voz.mp4
            P.avance(74, "Voz lista: regrabando el borrador con los tiempos REALES de la voz para que coincidan." if estima else "Voz lista: pegándola al borrador."); d = P.grabar(P.BORRADOR_RAPIDO, archivos=ARCH); P.borrador_con_voz()
            P.registrar("borrador", dur=d, pct=80, msg="BORRADOR CON VOZ sincronizada: revísalo y, si estás conforme, pulsa «Unir con la voz»."); P.avance(80, "BORRADOR CON VOZ listo (%.0f s): la voz y el video coinciden. Revísalo; si estás conforme, une." % d, cierra=True); return
        P.avance(72, "Unión: grabando el video de nuevo con lo último (reemplaza al anterior)." if ET != "unir" else "Unión: revisando si el video mudo coincide con los tiempos (si no, se graba de nuevo)."); fin = P.grabar(forzar=(ET == "conforme"), archivos=ARCH); P.borrador_con_voz(); P.musica(); P.sfx()
        esc = receta["escenas"](P, fin) if receta.get("escenas") else None
        if esc: V.js(P.R / "escenas.json", esc)
        rel, escenas = P.mezclar(fin)
        if not rel: sys.exit("No se pudo mezclar y unir el video final.")
        P.termina(rel, escenas, fin)
