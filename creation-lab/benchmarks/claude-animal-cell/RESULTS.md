# Resultados · benchmark Claude, célula animal (v1)

23–24 de octubre de 2026. Comparación **exploratoria** y aislada de Claude Haiku,
Sonnet y Opus como autores de código procedural Blender para un mismo brief
educativo, con la biblioteca `components`, el worker, el QA y una revisión ciega
asistida por Opus comunes. Datos completos en [results.json](results.json);
protocolo y enmiendas en [protocol.json](protocol.json).

**Resumen.** Opus 3/3 y Sonnet 3/3 réplicas terminaron en PASS técnico, visual y
de contenido; Haiku 0/3 (tres BLOCKED con las dos correcciones agotadas). Opus
aprobó blockout y detalle al primer intento en las tres réplicas (83.3 ± 2.3
puntos); Sonnet necesitó 0, 1 y 2 correcciones de blockout (80.0 ± 1.0). Con
tres réplicas por familia, un solo brief y un revisor de la familia Opus, esto
describe estos nueve intentos; no es un ranking general de modelos.

## Modelos y condiciones observados

| Rol | Alias solicitado | ID resuelto (runtime) | Esfuerzo |
| --- | --- | --- | --- |
| Autores Haiku (R5, R6, R7) | `haiku` | `claude-haiku-5-5` | `medium` |
| Autores Sonnet (R2, R3, R9) | `sonnet` | `claude-sonnet-5-5` | `medium` |
| Autores Opus (R1, R4, R8) | `opus` | `claude-opus-5-5` | `medium` |
| Revisor ciego (26 contextos nuevos) | `opus` | `claude-opus-5-5` | `medium` |
| Coordinador (esta sesión) | — | `claude-opus-5-5` | `high` |

Proveedor: API de Anthropic (`api.anthropic.com`) mediante Claude Code 2.1.299
(desktop). El ID y el esfuerzo salen del `prefix.json` del runtime y del campo
`message.model` de **cada** respuesta en los transcripts; ningún agente cambió de
modelo (35 contextos, 0 discrepancias) y ninguno usó subagentes, web ni skills.
Asignación R1–R9 aleatoria (`secrets.SystemRandom`), oculta al revisor.

## Tabla por réplica

`b`/`d` = run de blockout/detalle; letras = técnica/visual/contenido
(P = PASS, F = FAIL); entre paréntesis la puntuación de detalle (máx. 100).

| Réplica | Familia | Estado final | Secuencia | Corr. | Puntos | Triángulos | Mat. | Mallas | GLB, bytes |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| R1 | Opus | PASS | b:PPP → d:PPP(86) | 0 | 86 | 36 756 | 19 | 22 | 863 764 |
| R4 | Opus | PASS | b:PPP → d:PPP(82) | 0 | 82 | 39 224 | 18 | 20 | 1 286 612 |
| R8 | Opus | PASS | b:PPP → d:PPP(82) | 0 | 82 | 38 068 | 16 | 17 | 894 528 |
| R2 | Sonnet | PASS | b:PPP → d:PPP(79) | 0 | 79 | 25 564 | 17 | 18 | 690 888 |
| R3 | Sonnet | PASS | b:PFF → b:PPP → d:PPP(80) | 1 | 80 | 26 920 | 17 | 32 | 947 524 |
| R9 | Sonnet | PASS | b:PFF → b:PPF → b:PPP → d:PPP(81) | 2 | 81 | 26 812 | 17 | 18 | 771 464 |
| R5 | Haiku | BLOCKED | b:PFF → b:PPP → d:PFF(67) → d:PPF(74) | 2 | — | 14 012 | 16 | 20 | 249 716 |
| R6 | Haiku | BLOCKED | b:PFF → b:PFF → b:PFF | 2 | — | 10 588 | 13 | 14 | 375 064 |
| R7 | Haiku | BLOCKED | b:PFF → b:PFF → b:PPP → d:PPF(75) | 2 | — | 20 680 | 16 | 17 | 603 756 |

Los 26 runs pasaron el gate técnico: 13 partes, presupuestos (≤45 000 triángulos,
≤24 materiales, ≤350 mallas, ≤8 MiB), dimensión mayor 0.300 m (R5 0.2998 m) en
tolerancia, sin degenerados, `.blend` reabierto y GLB reimportado en procesos
limpios con comparación de superficies. Ningún fallo fue técnico; todos los
FAIL son visuales o de contenido.

## Agregados por familia

| Familia | PASS final | 1.er blockout aceptado | Llegó a detalle | 1.er detalle aceptado | Correcciones (media) | Puntos finales |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Opus | 3/3 | 3/3 | 3/3 | 3/3 | 0.0 | 83.3 (82–86, sd 2.3) |
| Sonnet | 3/3 | 1/3 | 3/3 | 3/3 | 1.0 (0–2) | 80.0 (79–81, sd 1.0) |
| Haiku | 0/3 | 0/3 | 2/3 | 0/2 | 2.0 | — (último detalle 74–75, gates fallidos) |

Sonnet y Opus obtienen puntuaciones cercanas; las diferencias de 3 puntos están
dentro de la variación observada entre revisores (ver limitaciones). El contraste
claro de esta muestra está en la tasa de aceptación y en las correcciones.

## Fallos que cerraron las réplicas Haiku

- **R6**: tres blockouts rechazados. La pared frontal tapaba el interior y luego
  citoplasma, lisosomas y citoesqueleto no se distinguían; el RER quedaba separado
  del núcleo y el Golgi más cerca que el RER.
- **R7**: blockout aprobado en la segunda corrección; su único detalle falla el
  check RER/REL: el RER es una lente con ribosomas amontonados, no cisternas junto
  al núcleo.
- **R5**: blockout aprobado en la primera corrección; el detalle v1 tenía un RER
  verde parecido a un cloroplasto y filamentos que atravesaban orgánulos; v2 aún
  falla RER/REL (ribosomas libres tocando el REL) y citoesqueleto.

Las revisiones completas, con vista, defecto y cambio pedido, están en cada
sesión (`reviews/`) y en `blind/*/review.json`.

## Tiempo y uso observados

| Familia | Tiempo activo del autor, s (media) | Salida observada, tokens (cota inferior, media) | Blender por réplica, s (media) |
| --- | ---: | ---: | ---: |
| Opus | 657 (529–739) | 26 124 | 275 |
| Sonnet | 587 (465–731) | 14 334 | 385 |
| Haiku | 780 (589–1 027) | 43 446 | 432 |

- Revisión: 26 revisiones Opus, 63 s activos de media; 2 borradores rechazados por
  el validador y corregidos por el mismo revisor (conservados).
- **Coste: NOT_AVAILABLE.** Los transcripts guardan casi siempre el `usage` del
  inicio del stream; `outputTokensLowerBound` toma el máximo por `message.id` y una
  estimación de salida visible (caracteres de texto y `tool_use` / 3.5). El
  razonamiento interno no aparece en los transcripts, así que la salida real es
  mayor. No comparar estas cifras como coste.
- El tiempo activo excluye las esperas entre etapas (enmienda 1.5); incluye lectura,
  escritura y pruebas en Python puro, no Blender. El tiempo de Blender
  (build + reapertura con seis renders + reimportación) es del host, no del modelo.
- Coordinación: 33 min el 23 de octubre más 20 min el 24, tras una pausa por límite de
  sesión (09:08 hora de Guatemala). La misma sesión coordinadora continuó con otra
  cuenta del mismo usuario; ningún autor ni revisor fue sustituido. Tokens del
  coordinador: NOT_AVAILABLE por separado.

## Validación del visor y formato

- `serve.py` (loopback, puerto 4397): 66/66 comprobaciones HTTP. La página, el
  bundle model-viewer, los 9 GLB y los 54 renders son idénticos byte a byte a la
  evidencia, y no expone fuentes ([detalle](#repetir)).
- Interacción del visor (rotación, etiquetas): **NOT_RUN**; no había automatización
  de navegador disponible en esta sesión.
- Khronos glTF Validator: **NOT_RUN** (sin Node/npm en el host). La reimportación
  limpia en Blender sí pasó en los 26 runs; eso no sustituye al validador.
- Segundo juicio humano o docente: **NOT_RUN**.

## Enmiendas y desviaciones registradas

Todas están en `protocol.json` con hashes previos y nuevos; ninguna cambió gates,
presupuestos, worker ni renders.

1. **v1.1**: la vista `wireframe` del worker congelado (alambre de 0.18 mm) casi no
   muestra aristas a 768 px. Se aclaró al revisor que no es un defecto del autor.
   La primera revisión (R7 v1) se ingirió sin cambios; sus otros defectos eran reales.
2. **v1.2 y v1.3**: dos reglas de `iterate.py` (visual PASS exige 13 partes visibles;
   `views` nunca vacío) quedaron explícitas tras rechazos del validador.
3. **v1.4**: `bench.py lint-review` para que el revisor valide su JSON.
4. **v1.5**: `receipts_v2.py`, `results.py` y `serve.py` (archivos nuevos;
   `bench.py` sigue congelado).
5. Varios autores (R1, R4, R6, R8) escribieron scripts de prueba en el scratchpad
   compartido de la sesión, fuera de su carpeta. El coordinador los movió a la
   evidencia. La auditoría de transcripts no muestra lecturas cruzadas, listados del
   directorio ni lecturas del archivo de estado del coordinador que estuvo segundos
   allí. Se consideran infracciones de procedimiento, no contaminación de autoría.
6. Blender de Windows escribió `__pycache__` en los runs (la variable no cruza
   WSLENV); quedó sellado en cada manifiesto e igual en todos los runs.

## Limitaciones

- n = 3 por familia, un brief y un revisor-modelo: exploratorio. La variación entre
  revisores es visible: el mismo check de apertura frontal pasó en unas revisiones
  y falló en otras para cortes horizontales parecidos, y el revisor es de la misma
  familia que la condición Opus (posible sesgo).
- Mide creación **asistida por componentes** con un contrato y un bucle de revisión;
  no generación desde cero ni flujos Haiku/Sonnet/Opus de extremo a extremo.
- El presupuesto compartido de dos correcciones favorece a quien acierta pronto:
  R9 y R7 llegaron al detalle sin correcciones restantes.
- Las aprobaciones son de rasgos visibles en seis renders; no son revisión docente
  externa ni precisión ultraestructural.
- El piloto Sol/Luna/Astra de 2026 no tuvo bucle visual ni biblioteca común; sirve
  solo como contexto histórico. Esta comparación no permite afirmar que Claude
  supere a esos modelos; haría falta reejecutarlos con este protocolo.

## Recomendación limitada

Para este brief, bajo este protocolo, Opus `medium` produjo candidatos aceptados
sin correcciones y Sonnet `medium` llegó al mismo resultado con más rondas de
blockout; Haiku `medium` no llegó a un candidato aceptado con dos correcciones.
Si se usa una familia Claude como autor en un experimento posterior, Opus o
Sonnet son las opciones respaldadas por estos nueve intentos. Antes de generalizar,
conviene repetir con más briefs, un segundo revisor (humano o de otra familia) y
reproducir las condiciones Sol/Luna con este mismo protocolo.

## Archivos y evidencia

- Versionados aquí: brief, perfil, contratos, `bench.py`, `receipts_v2.py`,
  `results.py`, `serve.py`, `protocol.json`, `results.json`, este informe.
- Locales (ignorados, `creation-lab/.local/claude-animal-cell-20261023/batch/`):
  26 runs sellados con generador exacto, snapshots de código y biblioteca, `.blend`,
  GLB, `parts.json`, seis renders, logs y manifiestos; 26 paquetes ciegos con su
  revisión; `coordinator/` con mapping, registros, mensajes, recibos del runtime
  (`receipts/`, `receipts-v2/`) e índice de integridad (`integrity-index.json`:
  1 523 archivos, 804 MiB, SHA256 `84db91a6…bc8975d6`). No se generó un paquete
  distribuible; no se publicó nada en la galería ni se hizo commit o push.

## Repetir

Ver [README](README.md). Para regenerar los informes desde la evidencia local:

```sh
python creation-lab/benchmarks/claude-animal-cell/receipts_v2.py --transcripts ~/.claude/projects/PROYECTO/SESION
python creation-lab/benchmarks/claude-animal-cell/results.py --output /ruta/nueva/results.json
python creation-lab/benchmarks/claude-animal-cell/serve.py --root creation-lab/.local/claude-animal-cell-20261023/batch --port 4397
```
