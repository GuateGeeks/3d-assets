---
name: gg3d-rigging
description: Prepara y riggea assets en el laboratorio local de 3d-assets con UniRig, recibe candidatos de creation-lab y compara esqueletos, pesos y deformaciones antes de clips. Usar para operar o reparar lab/ y su galería; la creación geométrica pertenece a gg3d-pipeline.
---

# Rigging local de GuateGeeks

Para un GLB que ya tiene skin o clips, empieza por la ruta de inspección Blender de
[gg3d-studio](../gg3d-studio/SKILL.md); conserva su rig. No lo entregues al contrato
estático de candidatos para quitarle huesos o animación. Studio delega `ingest`
y `rig --candidate` al runner existente, conservando su bloqueo y restauración.
SkinTokens tiene un adaptador separado y preflight de memoria; revisa el estado
actual de Studio antes de declarar una inferencia disponible.

Trabaja desde la raíz de `3d-assets`; no dependas del workspace padre. Lee primero [AGENTS.md](../../../AGENTS.md), el [estado vigente](../../../lab/STATUS.md) y la sección pertinente del [manual](../../../lab/README.md). El estado enlaza evidencia fechada; comprueba `lab/lab.py --help`, recibos y hashes antes de afirmar que una capacidad sigue operativa.

Para recibir geometría del workflow Sol/Luna, consulta el
[workflow iterativo](../../../creation-lab/docs/ITERATIVE-WORKFLOW.md): conserva
escala física, materiales y procedencia de cada componente. No implica que el
workflow propuesto esté validado por el benchmark histórico.

## Elegir la entrada

- **Corpus existente:** `human` = Man, `quadruped` = Wolf. Conserva originales y catálogo. Las copias pierden rig/clips para inferencia; el control conserva su rig sin clips. Se normalizan explícitamente a 2 m de dimensión mayor, centro XY y suelo Z=0.
- **Geometría nueva revisada:** usa `ingest --candidate` y después `rig --candidate` con el `preparedManifest` devuelto. Lee el [contrato de transferencia](../../../creation-lab/docs/INTEGRATION.md). No agregues el asset como otro ID del corpus ni reutilices su mapa anatómico.
- **Rig mecánico:** decide por función si necesita articulaciones rígidas; el canario de tres bloques no demuestra que un autorig orgánico sea adecuado para un robot de ruedas.
- **Modelo educativo por partes:** puede necesitar selección o vistas separadas sin deformación. Reutiliza el QA de geometría, escala y materiales cuando corresponda; un modelo de orgánulos no necesita UniRig solo por pasar por `creation-lab`.

## Operar lo ya implementado

En WSL/Linux, según el encargo y el estado real:

```bash
python3 lab/lab.py doctor
# Solo si falta instalación o su verificación está obsoleta:
python3 lab/lab.py setup --engine unirig
python3 lab/lab.py verify --engine unirig
# Corpus:
python3 lab/lab.py prepare --asset all
python3 lab/lab.py rig --asset human
python3 lab/lab.py rig --asset quadruped
python3 lab/lab.py review --asset all
python3 tools/serve_gallery.py --lab --port 4390
```

No repitas setup/inferencia para un cambio documental. En Windows el lanzador es `.\lab\lab.cmd`; sus argumentos de archivos son rutas WSL. El servidor usa Python estándar y puede correr en el host al que accede el navegador. `4390` es un ejemplo: comprueba disponibilidad y propietario antes de reutilizar un puerto o proceso.

Para geometría de creación:

```bash
python3 lab/lab.py ingest --candidate creation-lab/.local/runs/<handoff>/candidate.json
python3 lab/lab.py rig --candidate lab/.local/runs/<ingest>/creation-prepared.json --stage all
```

`--asset` y `--candidate` son excluyentes. Una carga GPU a la vez mediante el lock del laboratorio. Conserva logs y códigos reales de error/OOM/timeout; no cambies el entorno durante una inferencia activa. Los runs, configuraciones y exports revisados no se sobrescriben. Los archivos `latest-*`, los manifiestos de trabajo y el inventario de galería son punteros, no la única evidencia.

Antes de cambiar instalación, workers Blender, coordenadas o el runner, consulta [operación y fallos comprobados](references/operations.md). Para comparar poses o cambiar la galería, consulta [revisión de deformaciones](references/deformation-review.md).

## Validar pivotes de un rig rígido

Para un personaje web de rig rígido (cotizador), UniRig sirve como segunda opinión sobre los
pivotes, no como rig final.

- **Fuera del contrato de creación.** Ejecuta los mismos pasos de `rig`, de extracción a mezcla, en un run propio de `lab/.local/runs`. Prepara el workspace con `lab/scripts/prepare_smoke.py --input`, respeta el lock y deja una nota del experimento.
- **Lectura.** Lleva las articulaciones a unidades de altura y compáralas con las medidas. En el alumno Meshy coincidieron rodilla y cuello; cadera y codo se ajustaron a su predicción.
- **Hombro.** Su hombro es una clavícula para pesos suaves: no lo uses como pivote rígido.

## Interpretar y cerrar

`smoke` genera un esqueleto pero calcula pesos sobre el esqueleto revisado de la jirafa oficial. `rig` del corpus/candidato usa su propio esqueleto generado: no atribuyas al smoke una prueba de calidad automática de extremo a extremo.

Comprueba salida real, reapertura, pesos, materiales, dimensiones, hashes y procedencia. Mantén separados éxito técnico, diagnóstico visual y aprobación final. Conserva el vocabulario existente de rigging (`success`, `passed`, `pending`, etc.); `PASS/FAIL/BLOCKED/NOT_RUN` corresponde a creación y a sus recibos de origen.

El cierre incluye run de inferencia y revisión, cambios de preparación, mapas ligados a hashes, resultados de pruebas, advertencias y zonas pendientes. Actualiza [STATUS](../../../lab/STATUS.md) con enlaces a la evidencia, sin convertir tiempos aislados en benchmarks. SkinTokens sigue experimental pendiente de evaluación local; no inventes flags ni disponibilidad de memoria.

La aceptación de una fuente de creación, un export sin errores o una nota exportada desde la galería no aprueban el rig. Crea clips, promueve derivados o integra aplicaciones cuando el alcance autorizado y el dictamen de deformaciones lo permitan. El laboratorio sigue en `3d-assets`; Code Studio y Sócrates son consumidores posteriores.
