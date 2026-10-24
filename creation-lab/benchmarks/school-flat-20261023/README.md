# Escuela Flat/Minimal · prueba orquestada y comparación solo-Opus

Diorama 3D de una escuela en estilo **Flat Shaded / Minimalist**, animado (9 clips) e
interactivo en la web (14 partes seleccionables, puerta, día/noche). Prueba aislada
pedida por el usuario el 23 de octubre de 2026 para medir la orquestación por modelo
de Claude; no cambia el flujo de producción Sol/Luna y no entra al catálogo ni a la galería.

Dos condiciones con el mismo brief, kit inicial, contratos, runner y revisores:

| Condición | Autores | Carpeta |
| --- | --- | --- |
| Orquestada | Haiku 5.5 ×3 (entorno, patio, vida), Sonnet 5.5 ×3 (edificio, animación, web) | [conditions/orquestada](conditions/orquestada/) |
| Solo-Opus | Opus 5.5 ×6, mismos encargos | [conditions/opus](conditions/opus/) |

Coordinador Opus 5.5 `high` (brief, kit, composición, Blender, integración) y revisores
Opus 5.5 `medium` en contexto nuevo con las imágenes abiertas. Resultados, costos y
aprendizajes: [RESULTS.md](RESULTS.md). Sesgos declarados: [conditions/opus/DESIGN.md](conditions/opus/DESIGN.md).

## Contenido

| Ruta | Qué es |
| --- | --- |
| `spec/` | Brief, contrato de módulos, kit de primitivas facetadas (`kit-initial.py` y `kit.py` con la paleta corregida), encargos de animación y web, `check_module.py` (comprobación pura sin Blender), `assemble.py`, `build_web.py`, perfiles de modelos |
| `conditions/<c>/generators/` | Generadores ensamblados de cada run (kit + módulos con su sha256 + compositor). Cada uno contiene el código literal de los autores |
| `conditions/<c>/anim_worker.py` | Paso de animación final (metadatos `anim_*` → acciones NLA → GLB animado) |
| `conditions/<c>/viewer.html` | Visor three.js final, con el marcador `<!--SCHOOL_DATA-->` |
| `conditions/<c>/evidence/` | `session.json`, manifiestos y checks de cada run, revisiones ingeridas, revisión final de animación/web, resultados de animación y verificación |
| `conditions/<c>/agents.json`, `receipts.json`, `CHANGELOG.md` | Contextos reales, modelos y tokens por agente, decisiones del coordinador |
| `fixtures/<c>.zip` | Entregables finales: `detail/` (source.blend, asset.glb, parts.json, seis renders) y `anim/` (animated.blend, animated.glb, cuatro fotogramas) |
| `restore.py`, `receipts.py`, `cost_estimate.py` | Restaurar fixtures con hashes; recibos y costo estimado desde transcripts de Claude Code |

## Ver el modelo

Desde la raíz de `3d-assets`, con Python 3.10+ (no requiere Blender):

```sh
python creation-lab/benchmarks/school-flat-20261023/restore.py --check
python creation-lab/benchmarks/school-flat-20261023/restore.py
```

Restaura en `creation-lab/.local/benchmarks/school-flat-20261023/<condición>/`. Para construir
la página web autocontenida (GLB en base64 + partes + clips):

```sh
D=creation-lab/.local/benchmarks/school-flat-20261023/opus
python creation-lab/benchmarks/school-flat-20261023/spec/build_web.py \
  creation-lab/benchmarks/school-flat-20261023/conditions/opus/viewer.html \
  $D/anim/animated.glb $D/detail/parts.json \
  creation-lab/benchmarks/school-flat-20261023/spec/brief.json $D/index.html
```

`index.html` sigue el contrato de Artifact (sin doctype ni `<body>`); para abrirlo como archivo
local envuélvelo con `<!doctype html><meta charset="utf-8">` y sírvelo por HTTP. Usa three.js
0.170.0 desde jsDelivr.

## Reproducir

`iterate.py` en modo `benchmark` (perfil `spec/profile-*.json`, condición `orchestrated` u
`opus-only`) y Blender 5.2.3 LTS. Ejecutar un generador guardado repite la geometría; no vuelve a
llamar a los modelos ni renueva las revisiones. El paso de animación:

```sh
blender --background --factory-startup --disable-autoexec --python-exit-code 1 \
  --python creation-lab/benchmarks/school-flat-20261023/conditions/opus/anim_worker.py -- \
  animate RUN/source.blend creation-lab/benchmarks/school-flat-20261023/spec/brief.json OUTDIR_VACÍO
```

y después `-- verify OUTDIR/animated.glb BRIEF OUTDIR` en un proceso nuevo. Una sola instancia de
Blender a la vez. Las rutas absolutas dentro de manifiestos y resultados son procedencia del equipo
original, no instrucciones de configuración.

Geometría procedural original, sin modelos ni imágenes externos; CC0-1.0 según el brief.
