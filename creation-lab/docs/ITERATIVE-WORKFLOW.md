# Creación iterativa con Sol y Luna

El contrato Python/bpy y sus entregables pertenecen a la ruta Blender. La autoría
interactiva por código y la coordinación de proveedores viven en
[Studio](../../studio/README.md), con [gates por ruta](../../studio/docs/ACCEPTANCE.md).
Se comparten procedencia, revisión independiente, presupuestos y preservación de evidencia.

Este es el flujo predeterminado para nuevas creaciones procedurales en Blender. Los agentes
escriben Python; Blender construye, renderiza y exporta. Reejecutar un script
aprobado no requiere otra llamada a un modelo. El piloto de célula animal de
2026 conserva su protocolo original de primera versión y reparación técnica;
sus notas no son resultados de este flujo iterativo.

## Roles y alcance

Usa [MODELS](MODELS.md) y los perfiles de planificación. Sol `medium` coordina
y compone; Luna `medium` resuelve piezas, variantes y metadatos acotados. Otro
contexto Sol `medium` revisa las imágenes; Sol `high` atiende un diagnóstico
persistente. Verifica disponibilidad real; no cambies a otro proveedor/modelo
silenciosamente. El usuario puede solicitar una comparación explícita diferente.

`iterate.py` registra y comprueba los identificadores declarados por el
coordinador, sin invocar APIs ni cambiar el modelo de Codex. No puede atestiguar
qué backend respondió: conserva también los recibos reales del runtime cuando
estén disponibles. No inventes agent IDs, uso, tokens ni coste. Un script no
crea por sí mismo autores o revisores independientes.

| Modo | Coordinación | Autoría | Revisión dentro del flujo |
| --- | --- | --- | --- |
| `mixed` (predeterminado) | Sol | Sol o Luna | Sol, contexto independiente |
| `sol` | Sol | Sol | Sol, contexto independiente |
| `luna` | Luna | Luna | Luna, contexto independiente |

Los IDs admitidos son `gpt-6.1-sol` y `gpt-6-luna`. Para cambiar versiones,
actualiza política, pruebas y recibos de forma explícita. Una evaluación externa
común puede comparar los modos puros después, sin presentarla como parte de su
ejecución exclusiva. El [prompt de Claude](../prompts/08-claude-benchmark.txt)
describe una excepción de benchmark solicitada por el usuario. Los modos `sol`,
`mixed` y `luna` siguen rechazando otros IDs; una comparación así usa
`init --mode benchmark --profile ... --condition ...`, con IDs exactos por rol
congelados en la sesión. Nunca uses nombres falsos Sol/Luna. Ver el
[benchmark Claude](../benchmarks/claude-animal-cell/README.md).

## Brief, componentes y criterios

El brief JSON tiene `schemaVersion: 1`, `id`, `purpose`, `seed`, `parts` (IDs y
etiquetas únicas), `displayScale` en metros con dimensión mayor y tolerancia
relativa, cuatro `budgets` (`triangles`, `materials`, `meshObjects`, `glbBytes`)
y `provenance` (`author`, `origin`, `license`). Para educación añade funciones
y convenciones de color, proporción y escala.

Separa `blockoutChecks` (visibilidad, distribución y relaciones de los volúmenes)
de `contentChecks` o `biologicalChecks` (rasgos del resultado detallado). El
fallback de blockout comprueba solo distribución/visibilidad; escríbelo de forma
concreta para el encargo. Un blockout aprobado no valida crestas, poros o anatomía
que aún no se han construido. El [brief del demo](../components/demo-brief.json)
es un ejemplo completo y no representa una célula final.

Reutiliza [components](../components/README.md). Mantén el mismo perfil de corte
y resolución para envoltura/relleno, y calcula los anclajes sobre la superficie
que representan. No distribuyas ribosomas supuestamente adheridos con una fórmula
independiente de su cisterna. Las primitivas geométricas no certifican biología.

Cada generador define `build()` sin argumentos y devuelve `title`, `design_notes`
y `parts`, un mapa ID → `{"label_position": [x,y,z]}` en metros Blender. Las
mallas finales llevan `part_id`, materiales Principled y modificadores aplicados.
Usa Z arriba, frente -Y, aproximadamente centrado en origen. No añadas luces,
cámaras, texto 3D, red, exportación ni E/S: el worker común lo hace. Puede importar
`bpy`, `math`, `random`, `mathutils` y `components`. Se ejecuta código local
confiable; el filtro de imports no constituye un sandbox de seguridad.

## Secuencia reproducible

Ejecuta desde la raíz del repositorio. Sustituye rutas y `CONTEXTO_REAL` por los
valores de tu ejecución; no copies un recibo de otro equipo como autoría propia.

```sh
python creation-lab/iterate.py init --brief creation-lab/components/demo-brief.json --mode mixed --actor-id CONTEXTO_REAL --model gpt-6.1-sol --effort medium
```

La salida devuelve `session`. Usa esa carpeta como `SESION`:

```sh
python creation-lab/iterate.py run --session SESION --generator creation-lab/examples/component-demo.py --stage blockout --blender /ruta/absoluta/blender --actor-id AUTOR_REAL --model gpt-6.1-sol --effort medium
python creation-lab/iterate.py review-template --session SESION --run RUN_ID --output revision-blockout.json
```

El primer autor produce una maqueta con los volúmenes necesarios. Abre las
seis imágenes reales y entrega la plantilla al revisor en contexto separado,
junto con el brief y las imágenes, sin el mapping de modelos si se evalúa a ciegas.
Completa su actor/modelo/esfuerzo, `openedImages`, cada parte, cada check, las
razones y defectos localizados por vista con el cambio solicitado. Conserva los
hashes de la plantilla. Los estados son `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`.

```sh
python creation-lab/iterate.py review --session SESION --input revision-blockout.json
python creation-lab/iterate.py status --session SESION
```

Solo `READY_FOR_DETAIL` permite pasar al detalle:

```sh
python creation-lab/iterate.py run --session SESION --generator /ruta/generador-detallado.py --stage detail --blender /ruta/absoluta/blender --actor-id AUTOR_REAL --model gpt-6.1-sol --effort medium
```

Repite plantilla/revisión con el nuevo `RUN_ID` y otro archivo de salida para
la plantilla (el comando no sobrescribe archivos). Una corrección usa el mismo
stage, un generador corregido y una carpeta de run nueva. Hay **dos correcciones
totales por sesión**, además del primer blockout y primer detalle; puede fijarse
otro presupuesto con `init --max-corrections` antes de empezar. No reinicies
sesiones para ocultar fallos o aumentar intentos en un benchmark.

Un fallo técnico antes de producir imágenes puede repararse desde su diagnóstico.
Si técnicamente pasó, revisa las imágenes antes de otra corrección visual. Agotado
el presupuesto, conserva `BLOCKED` y los defectos pendientes. No amplíes el límite
ni bajes tolerancias para conseguir PASS. Una aprobación anterior no se hereda
tras cambiar el asset. No se sobrescriben revisiones; un cambio exige otro run.

## Evidencia y entrega

Cada run conserva código, biblioteca, brief, worker, verificador de superficies,
comandos, logs, `.blend`, GLB, partes, seis imágenes y hashes. El renderer común
usa Cycles CPU, dos hilos, 24 muestras y 768 px. Los tiempos incluyen Blender,
render y QA; no son latencia del modelo. `modelUsage: null` significa no medido.

La revisión técnica incluye presupuestos, triángulos degenerados, reapertura y
reimportación con el QA de `lab/scripts/creation_geometry.py`: superficies
orientadas, normales, UV, materiales y límites en todos los ejes. La revisión
visual comprueba lectura, contraste y oclusión. La revisión de contenido comprueba
relaciones y rasgos observables; un ID o un nombre no demuestra anatomía. Una
parte oculta se marca `hidden`/`unclear`, nunca PASS por inferencia desde el código.

Los hashes vinculan la revisión a sus archivos, pero una declaración
`openedImages: true` sigue siendo responsabilidad del revisor. La herramienta
no sustituye su inspección ni una evaluación docente externa. El fixture de
tests usa datos sintéticos solo para comprobar contratos; no es evidencia visual.

`PASS` del detalle permite preparar la entrega según [INTEGRATION](INTEGRATION.md).
Esta CLI no publica el catálogo ni crea automáticamente el manifiesto candidato
del adaptador de rigging. Conserva fuentes y licencia; usa el contrato del
adaptador y su QA para una transferencia real. No normalices implícitamente una
maqueta a 2 m, ni crees un esqueleto para una célula que solo necesita partes.

Una sesión tiene un solo escritor. Si un proceso se interrumpe y deja
`.writer.lock`/un run sin `COMPLETE`, conserva los archivos y diagnostica el
proceso antes de recuperar: no borres el intento ni lo marques PASS a mano.
Después de confirmar que Blender y su runner han terminado, ejecuta:

```sh
python creation-lab/iterate.py recover --session SESION --run RUN_ID --stopped --reason "Motivo comprobado de la interrupción"
```

La opción `--stopped` es una declaración del operador, no una detección automática.
El comando no mata procesos: conserva el lock y el manifiesto parcial existentes,
sella el intento como FAIL y lo mantiene dentro del presupuesto. No recuperes un
run mientras otro proceso pueda seguir escribiéndolo. Un `request.json` ausente o
dañado requiere diagnóstico manual; no fabriques una autoría para reconstruirlo.

## Evaluar si mejora

Compara `sol`, `mixed` y `luna` usando el mismo brief, biblioteca congelada,
presupuestos, vistas y rondas. Empieza con al menos tres autorías independientes
por condición; más repeticiones y briefs amplían el alcance. Ejecutar tres veces
el mismo `generator.py` no son tres autorías. La semilla geométrica tampoco
controla la variación del modelo.

Reporta aceptación inicial/final, fallos críticos, revisiones, intervención,
archivos editables y uso observado. Conserva todos los intentos, incluso fallos.
Separa evaluación del autor, del flujo completo y del revisor. Estos cambios
son herramientas verificables; su mejora de calidad/coste requiere un benchmark
nuevo y no debe atribuirse a las notas históricas A–F.
