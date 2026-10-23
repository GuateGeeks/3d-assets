# Estado del workflow 3D

22 de octubre de 2026 · preparación integrada en `3d-assets`.

El núcleo de creación ya funciona con Blender nativo 5.2.3 LTS. La entrega
incluye instrucciones permanentes, siete skills propios de creación, un skill
de rigging, dos adaptadores de recetas y ocho prompts por hitos,
perfiles de modelos y un contrato candidato para el laboratorio de rigging.
El detalle de comandos está en [README](../README.md).

| Capacidad | Estado comprobado |
| --- | --- |
| Diagnóstico Blender Windows | PASS, 5.2.3 LTS, build e13b728c6880 |
| Skills del proyecto | PASS: ocho propios y dos adaptadores validados; [evidencia](../../lab/reports/skills-validation.json) |
| Brief y procedencia | PASS para perfil lowpoly-canary; proveedor de imágenes no ejecutado |
| Canario headless | PASS: guardar, reabrir, renderizar, exportar y reimportar |
| QA visual del canario | PASS, seis imágenes abiertas y comparación GLB inspeccionada |
| Handoff candidato | PASS como manifiesto; no equivale a ingestión ni publicación |
| Ingestión de candidatos de creación | PASS: entrega real recibida en WSL, con evidencia copiada y normalización explícita |
| Restauración de escala y apariencia | PASS en fixture con textura y en inferencia UniRig real; [informe y evidencia](../../lab/reports/CREATION-ADAPTER.md) |
| Producción M2-M7 | NOT_RUN: skills, prompts y criterios preparados |
| Piloto de célula animal | Ejecutado: seis condiciones y diez runs; D 87/100 y A 85/100 pasan técnica, visual y biología visible; [resultados](../benchmarks/animal-cell-20261022/RESULTS.md) |
| Relevo desde un clon nuevo | Skills, scripts, locks y diez runs restaurables incluidos; [instalación](../../SETUP.md) y [verificación del repositorio](repository-handoff.json) |
| API de imágenes y comparación con Claude | NOT_RUN; sin gasto iniciado |
| Puente MCP oficial | PASS en proceso propio: consulta, creación, render y limpieza; entrada local configurada, carga en este chat NOT_RUN |

## Evidencia técnica y visual

Los runs están en `../.local/runs/` y se conservan localmente, ignorados por Git.
El diagnóstico real es `20261022T214745170298Z-5aea46366b`.

El canario `20261022T215722341157Z-a9e0139899` tiene 132 triángulos,
dos materiales y dimensiones medidas 0.180000007 × 0.189999998 × 0.300000012 m.
Su revisión visual es `20261022T215833688856Z-e6dcb4714e`; el handoff candidato
es `20261022T215851655676Z-dc714b4214`. Cada manifiesto conserva hashes, versión, comandos y linaje. El run final incluye snapshots del código ejecutado; los anteriores permanecen conservados.

El primer intento `20261022T214800285373Z-857334a383` se conserva como FAIL:
el conteo topológico bruto interpretaba los vértices separados por normales
y materiales del GLB como bordes abiertos. La corrección mide una copia soldada
a 1 micrómetro y registra también el conteo bruto; no modifica la exportación.
Una prueba real con Blender distingue ese caso de un agujero verdadero.

Las seis imágenes son frente, lateral, espalda, tres cuartos, wireframe y tres
cuartos del GLB reimportado. El canario es una baliza geométrica de tres bloques;
no representa el robot educativo final ni aprobación de diseño del usuario.

## Convivencia con el trabajo activo

El laboratorio de rigging completó la preparación e inferencia de Man y Wolf,
con galería de poses estáticas; el humano necesita revisar rodilla/codos antes
de clips. El [estado de rigging](../../lab/STATUS.md) conserva el relevo actual. Este corte añade `creation-lab/`, skills e
instrucciones propias; conserva sus archivos, modelos originales y entorno.
El adaptador `ingest` / `rig --candidate` usa runs independientes y conserva los
punteros del corpus y de la galería. Lee [INTEGRATION](INTEGRATION.md) para usarlo.

## Siguiente corte

El [benchmark de célula animal](../benchmarks/animal-cell-20261022/README.md)
entrega seis GLB y fuentes Blender, trece partes en español, visor local y
evidencia de seis vistas finales por condición. Compara tres modelos autores
con esfuerzos `medium` y `high`, en contextos independientes. Cinco condiciones
pasan el gate técnico final y dos pasan además revisión visual/biológica. No
equivale al M7 completo de seis briefs ni a una clasificación estadística de
modelos. Los fallos y las reparaciones únicas se conservan con hashes; no se
promovieron estos experimentos al catálogo.

1. Revisar anatómicamente los candidatos nuevos antes de añadirlos a la galería
   o producir clips; la ingestión y la restauración de escala están implementadas.
2. Implementar M2 y presentar conceptos y blockout del robot de 0.30 m para
   revisión antes del detalle.
3. Seguir M3-M7 con sus presupuestos y evidencia, sin convertir los prompts
   preparados en afirmaciones de ejecución.


## Verificación inicial del núcleo (histórica)

En ese corte se aprobaron doce pruebas, incluidas dos con Blender real. Astra recalculó 43 comprobaciones sin fallos y cerró los hallazgos del núcleo. El verificador del catálogo confirmó entonces integridad de 342 modelos y del sitio existente. Consulta [REVIEW](REVIEW.md) y [validation.json](validation.json). El catálogo posterior y la entrega reproducible se comprueban por separado en [repository-handoff.json](repository-handoff.json).


La prueba final del lanzador MCP configurado, `registry/launcher-probe-20261022T220620Z-9ee77265/report.json`, pasó conexión, modificación, render y cierre. La igualdad completa de píxeles con el render inspeccionado confirma el cubo encuadrado; véase `registry/mcp-render-comparison.json`. Ambos procesos y el puerto terminaron cerrados. La captura del viewport permanece NOT_RUN. Consulta [DEPENDENCIES](DEPENDENCIES.md) para fuentes, licencias, runtime y alcance de la conexión.
