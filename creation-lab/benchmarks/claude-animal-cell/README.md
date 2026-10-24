# Benchmark Claude · célula animal (v1)

Comparación aislada, pedida explícitamente por el usuario, de Claude Haiku, Sonnet
y Opus como **autores de código procedural Blender** para el mismo brief educativo.
No cambia el flujo de producción, que sigue siendo Sol/Luna. El
[protocolo](protocol.json) está congelado con hashes de brief, perfil, contratos,
biblioteca `components`, worker, QA, CLI y adaptador de host.

| Elemento | Archivo |
| --- | --- |
| Brief (derivado del piloto; añade `blockoutChecks`) | [brief.json](brief.json) |
| Perfil de modelos por rol/condición | [profile.json](profile.json) |
| Contrato del autor | [AUTHORING.md](AUTHORING.md) |
| Instrucciones del revisor ciego | [REVIEWING.md](REVIEWING.md) |
| Herramienta del coordinador | [bench.py](bench.py) |
| Adaptador opcional WSL → `blender.exe` | [wsl-blender.sh](wsl-blender.sh) |
| Resultados | [RESULTS.md](RESULTS.md), [results.json](results.json) |

## Diseño

- 3 familias × 3 autorías independientes = 9 réplicas `R1`–`R9`, asignadas al azar.
  Cada réplica tiene su propio contexto de autor (subagente nuevo), su propia
  sesión `iterate.py` y escribe su propio generador. El mismo contexto hace el
  blockout, el detalle y sus correcciones. Reejecutar un script no es autoría.
- Esfuerzo común `medium` para los autores (soportado por las tres familias).
- Dos correcciones totales por sesión, además del primer blockout y primer detalle.
- El coordinador (Opus) organiza, ejecuta Blender de forma secuencial, construye los
  paquetes ciegos y reenvía el texto del revisor. No escribe geometría.
- Revisor: Opus 5.5 `medium`, contexto nuevo por run, paquete ciego (brief, seis
  imágenes, etiquetas) sin modelo autor, código ni mapping.

## `iterate.py` en modo benchmark

La CLI conserva Sol/Luna como únicos IDs de los modos `sol`, `mixed` y `luna`.
El modo `benchmark` exige un perfil con IDs exactos (rechaza alias como `opus`) y
una condición; el perfil queda congelado dentro del `session.json` sellado:

```sh
python creation-lab/iterate.py init --brief creation-lab/benchmarks/claude-animal-cell/brief.json \
  --mode benchmark --profile creation-lab/benchmarks/claude-animal-cell/profile.json --condition haiku \
  --output RUTA_NUEVA --actor-id CONTEXTO_REAL --model claude-opus-5-5 --effort high
```

Autor, revisor y coordinador se validan contra su rol y condición, incluido el
esfuerzo. `bench.py` envuelve esas llamadas para las nueve réplicas.

## Repetir desde un clon limpio

Requiere Python ≥3.10, Blender 5.2.3 LTS y Claude Code con acceso a las tres familias.
Desde la raíz de `3d-assets`:

```sh
python -m unittest discover -s creation-lab/tests -v
python creation-lab/benchmarks/claude-animal-cell/bench.py --root creation-lab/.local/MI-BATCH setup --coordinator-id CONTEXTO_REAL
```

`setup` crea nueve sesiones y un mapping aleatorio en `coordinator/mapping.json`.
Para cada réplica, inicia un subagente nuevo con el alias de su condición y
`effort: medium`, entrégale el texto de [AUTHORING.md](AUTHORING.md) y su carpeta,
y registra su ID real:

```sh
python creation-lab/benchmarks/claude-animal-cell/bench.py --root creation-lab/.local/MI-BATCH register --replica R1 --agent-id ID_REAL
python creation-lab/benchmarks/claude-animal-cell/bench.py --root creation-lab/.local/MI-BATCH run --replica R1 --stage blockout --generator creation-lab/.local/MI-BATCH/authors/R1/blockout-v1.py --blender /ruta/absoluta/blender
python creation-lab/benchmarks/claude-animal-cell/bench.py --root creation-lab/.local/MI-BATCH packet --replica R1
```

Entrega el paquete `blind/<id>/` y [REVIEWING.md](REVIEWING.md) a un revisor nuevo.
Después:

```sh
python creation-lab/benchmarks/claude-animal-cell/bench.py --root creation-lab/.local/MI-BATCH ingest --blind ID_CIEGO --reviewer-id ID_REAL
python creation-lab/benchmarks/claude-animal-cell/bench.py --root creation-lab/.local/MI-BATCH feedback --replica R1
python creation-lab/benchmarks/claude-animal-cell/bench.py --root creation-lab/.local/MI-BATCH status
python creation-lab/benchmarks/claude-animal-cell/bench.py --root creation-lab/.local/MI-BATCH receipts --transcripts ~/.claude/projects/PROYECTO/SESION
```

`ingest` compara los hashes que el revisor calculó con los renders del run y guarda
la revisión mediante `iterate.py`. `feedback` copia los renders propios y los
defectos al autor. `receipts` lee los transcripts de Claude Code: modelo de cada
respuesta, esfuerzo, tokens, tiempo activo y una auditoría heurística de lecturas,
subagentes y herramientas prohibidas.

En WSL con Blender de Windows, exporta `GG3D_WINDOWS_BLENDER=/mnt/.../blender.exe`
y pasa `--blender creation-lab/benchmarks/claude-animal-cell/wsl-blender.sh`.
En otros hosts usa el Blender nativo. Ejecuta un Blender a la vez (`flock` sirve).

Los runs, `.blend`, GLB y renders quedan en `creation-lab/.local/` (ignorado). Un
clon nuevo genera sus propios runs; regenerar no reproduce bytes ni revisiones.
