# Hitos de creación integrados con 3d-assets

Fecha de referencia: 22 de octubre de 2026, America/Guatemala.

La investigación define un laboratorio que debe demostrar sus resultados.
Se reconstruyen aquí sus requisitos a partir de la conversación disponible;
no se afirma haber recuperado ni ejecutado el ZIP mencionado allí.

| Hito | Resultado | Evidencia de salida | Prompt |
| --- | --- | --- | --- |
| M0 | Diagnóstico, fuentes fijadas y skills locales | Versión real, licencias, hashes, estados de herramientas | [00](../prompts/00-bootstrap.md) |
| M1 | Núcleo headless reproducible | Guardar/reabrir `.blend`, cinco vistas, GLB, reimportar, QA | [01](../prompts/01-core.md) |
| M2 | Brief, conceptos y blockout | Referencias con procedencia, tres conceptos, revisión registrada | [02](../prompts/02-concept.md) |
| M3 | Robot low-poly original | 0.30 m, ≤6000 triángulos, ≤2 materiales, texturas ≤2048 | [03](../prompts/03-lowpoly.md) |
| M4 | Master detallado y derivado optimizado | Identidad conservada; derivado ≤40000 triángulos, ≤4 materiales | [04](../prompts/04-highdetail.md) |
| M5 | Escena coherente | Presupuesto global, instancias, escala y materiales revisados | [05](../prompts/05-scene.md) |
| M6 | Prueba orgánica independiente | Volúmenes, continuidad, articulaciones y retopología evaluados | [06](../prompts/06-organic.md) |
| M7 | Benchmark reproducible | Seis briefs repetidos, fallos conservados y revisión ciega | [07](../prompts/07-benchmark.md) |

El estado actual vive en [STATUS](STATUS.md). Cada hito conserva sus propios
bloqueos: el canario headless puede pasar aunque MCP aún no esté conectado.
La prueba de MCP pertenece a una capacidad separada; no se declara aprobada
por tener una configuración de ejemplo.

## Relación con rigging

El flujo completo es solicitud → brief → conceptos → blockout revisado →
geometría → QA → candidato con procedencia → preparación de rigging →
esqueleto → pesos → deformación → clips → revisión → paquete.

El [plan existente](../../docs/RIGGING-LAB-PLAN.md) gobierna las etapas desde
preparación de rigging. `creation-lab` no repite instalaciones de UniRig ni
SkinTokens. Un objeto rígido o mecanismo articulado puede requerir pivotes
y jerarquía manual, en vez de autorigging orgánico.

El [adaptador de ingestión](INTEGRATION.md) recibe el manifiesto candidato y
ejecuta el rigging en runs propios, con normalización explícita y restauración
de coordenadas. La presentación de candidatos genéricos en la galería y su
revisión de deformaciones son etapas posteriores; la interfaz anatómica actual
de la galería conserva su corpus humano/cuadrúpedo.

## Trabajo entre agentes

Arquitectura define el contrato; implementación modifica sus archivos; revisión
comprueba artefactos reales. Divide por carpetas o runs, nunca por editores
simultáneos de la misma escena. Cada agente comunica versiones, comandos
ejecutados, evidencia y pruebas pendientes. La GPU permanece serializada.
