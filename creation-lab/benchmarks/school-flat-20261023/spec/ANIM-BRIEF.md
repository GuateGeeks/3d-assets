# Encargo · paso de animación (Blender 5.2.3 LTS)

Escribe `anim_worker.py` en tu carpeta de autor. No ejecutes Blender: el
coordinador lo corre (una sola instancia a la vez) y te devuelve logs si falla.

## Entrada

Un `source.blend` producido por el runner del laboratorio (`creation-lab/scripts/iteration_worker.py`):
mallas finales facetadas con `obj['part_id']`, más cámara ortográfica, luces y
mundo de presentación ya configurados (Cycles CPU, 24 muestras, 768 px). Los
objetos animados llevan propiedades personalizadas (ver `CONTRACT.md`, sección
Animación): `anim_clip` (str), `anim_kind` (str), `anim_pivot` (3 floats, mundo),
`anim_axis` ('X'|'Y'|'Z'), `anim_params` (grupo de propiedades: números, texto
o listas planas de números). Clips esperados y autoplay: `brief.json` → `animations`.

## Uso

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python anim_worker.py -- animate SOURCE.blend BRIEF.json OUTDIR
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python anim_worker.py -- verify OUTDIR/animated.glb BRIEF.json OUTDIR
```

Rutas absolutas. `OUTDIR` existe y está vacío al empezar `animate`. No escribas fuera de `OUTDIR`.

### `animate`
1. Abre SOURCE.blend (`load_ui=False`, `use_scripts=False`). No modifiques geometría
   salvo **re-pivotar**: para cada objeto animado, traslada la malla con
   `obj.data.transform(Matrix.Translation(-pivot))` y pon `obj.location = pivot`
   (solo si el objeto está en identidad). Comprueba que el bbox de mundo de cada
   objeto no cambia (tolerancia 1e-6 m) y regístralo.
2. Construye la animación por objeto a `fps` del brief (24): una acción por objeto
   y clip, con keyframes muestreados (p. ej. cada frame o cada 2) que formen un
   bucle exacto de duración `period` (primer y último frame iguales). Implementa
   los `kind` de la tabla del contrato (hinge, spin, sway, swing, bounce, drift,
   path, walk). `path/walk`: interpolación lineal por distancia, giro en Z para
   mirar al avance (`forward` indica el frente local, por defecto '-Y'), con giros
   suaves en las esquinas. `hinge`: 0→angle (25 % del periodo), espera, vuelve.
3. Mete cada acción en una pista NLA del objeto cuyo **nombre sea exactamente el
   clip** y deja `animation_data.action = None`, para que el exportador glTF fusione
   en una sola animación por clip todos los objetos del mismo clip.
4. Guarda `OUTDIR/animated.blend` y exporta `OUTDIR/animated.glb`: GLB, Y-up,
   `export_extras=True`, sin cámaras ni luces, solo mallas, animaciones en modo
   pistas NLA, con muestreo. Los nombres de opciones cambian entre versiones:
   filtra los kwargs contra `bpy.ops.export_scene.gltf.get_rna_type().properties`
   y registra los aplicados y descartados.
5. Renderiza con la cámara y luces ya presentes en la escena, a 768 px, cuatro
   instantes (`t` = 0, 0.8, 1.6, 2.4 s) en `OUTDIR/renders/anim-<frame>.png`.
6. Escribe `OUTDIR/anim-result.json`: versión de Blender, clips → objetos,
   duración en frames/segundos por clip, kwargs del exportador, comprobación de
   re-pivotado, sha256 de animated.blend/animated.glb/renders y `status` PASS/FAIL
   con lista de checks.

Blender 5.x usa acciones con *slots*/capas: `action.fcurves` puede no existir.
Para tocar F-curves usa `bpy_extras.anim_utils.action_get_channelbag_for_slot(action, slot)`
con fallback a `action.fcurves`. Al crear una tira NLA desde una acción con slot,
asigna también `strip.action_slot` cuando exista. Escribe código defensivo y
claro; nada de `bpy.ops` que dependan del contexto de UI salvo los de
abrir/guardar/exportar/importar/render.

### `verify` (proceso nuevo)
Escena vacía (`read_factory_settings(use_empty=True)`), importa animated.glb y
comprueba: los nombres de animación importados (pistas NLA o acciones) contienen
cada clip del brief; cada clip anima ≥1 objeto; cada malla conserva `part_id`
en sus propiedades; número de mallas y triángulos coincide con `anim-result.json`
(guárdalos allí en `animate`). Escribe `OUTDIR/verify-result.json` con `status`.

Entrega: ruta y sha256 de `anim_worker.py` y un resumen breve de decisiones.

## Duración común por clip (aclaración incluida desde el inicio)

Dentro de un mismo clip los objetos pueden tener `period`, `kind` y `phase` distintos
(p. ej. árboles con periodos 3.0–3.8 s; estudiantes que caminan y otros que rebotan).
Por clip (salvo `hinge`): duración común D = period máximo; cada objeto usa
k = max(1, round(D/period)) ciclos con period efectivo D/k, de modo que todo el clip
cierra su bucle exactamente en D. Registra por objeto period pedido/efectivo. `hinge`
es solo apertura (frame 0 cerrada, último abierta), no bucle.
