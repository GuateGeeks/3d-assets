# Pilotos comparables y resultados reutilizables

Aplicar al comparar varios autores o configuraciones sobre un mismo brief.
El [workflow iterativo](../../../../creation-lab/docs/ITERATIVE-WORKFLOW.md)
es la referencia vigente para roles y correcciones; no modifica resultados previos.
El [piloto de célula animal](../../../../creation-lab/benchmarks/animal-cell-20261022/README.md)
y sus [resultados](../../../../creation-lab/benchmarks/animal-cell-20261022/RESULTS.md)
son evidencia de un caso, no una clasificación permanente de modelos.

## Congelar condiciones

Usa contextos de autor independientes con el mismo brief y contrato. Registra
modelo y esfuerzo solicitados, herramientas realmente utilizadas, semilla,
versiones y parámetros de construcción/render. Si los modelos escriben Python
procedural para Blender, descríbelos como autores de código; no atribuyas el
resultado a un proveedor de texto a 3D que no se ejecutó.

Cada run conserva el generador ejecutado y snapshots/hashes del harness y QA.
Un hash del archivo actual no identifica una versión anterior ya ejecutada.
Congela el harness antes del lote; si cambia, registra qué runs usaron cada
versión y si el cambio afecta comparabilidad. Nunca actualices una primera
versión para hacerla coincidir con una reparación posterior.

El próximo piloto contempla solo Sol, Sol+Luna y solo Luna. Usa la misma
biblioteca versionada, brief, herramientas, límites y rondas. Recomienda al menos
tres autorías independientes por condición; volver a ejecutar un script no crea
una autoría nueva. Registra modelo/esfuerzo solicitado y efectivo de coordinador,
autores, correctores y revisor; valores desconocidos se declaran, no se infieren.
La revisión usa un contexto distinto de los autores y observa imágenes. Define
una evaluación externa común y declárala separada de la revisión interna del modo.

Fija de antemano el alcance y número de reparaciones: por defecto dos rondas
totales por sesión compartidas entre etapas, aparte del primer blockout y primer
detail en el workflow nuevo, conservando fallos y gates. Una escalada
Sol `high` por diagnóstico difícil cuenta como intervención declarada.
El piloto de célula admitió
una reparación técnica por autor; no es un límite universal. Conserva resultados
iniciales y finales, motivo, código y tiempo de cada intervención. Un coordinador
que corrige estética cambia la condición y debe declarar esa intervención.

## Evaluar evidencia exacta

El revisor recibe IDs de condición, brief y renders; oculta la correspondencia
de autores cuando sea viable. Abre las seis imágenes del run evaluado y registra
sus hashes. Una reparación que cambia el GLB o los renders exige evidencia
nueva; puede conservar la puntuación si la reinspección lo justifica, sin
presentar los hashes viejos como revisión del artefacto nuevo. Si falta una vista,
declara el alcance incompleto en vez de simular una revisión completa.

Separa formato GLB, fidelidad de reimportación, apariencia y contenido del brief.
En material educativo, una envoltura opaca puede ocultar estructuras cuyos IDs
existen; una forma ambigua puede confundir incluso si la composición es agradable.
La revisión científica se limita a rasgos visibles, no a anatomía oculta ni a
precisión microscópica. Las referencias, el nivel y el idioma pertenecen al brief.

Publica tanto los gates como las puntuaciones. Si hay una recomendación
predeterminada en el visor, elígela entre las condiciones que cumplen todos los
gates requeridos, no solo por el mayor total numérico.

## Medir y entregar

Distingue tiempo de autoría/inferencia de construcción, render, reapertura,
validación y empaquetado. Registra host compartido y concurrencia observada;
no infieras costo, tokens ni latencia de modelo a partir del tiempo de Blender.

Un clon sin `.local` no contiene los runs aunque sí tenga sus informes. Entrega
generadores, dependencias reproducibles y comandos, e identifica qué artefactos
se versionan o se restauran desde un paquete verificado. No anuncies que el visor
puede mostrar modelos ausentes. Regenerar hoy no reproduce los bytes históricos:
mantén separados resultados publicados, nuevos runs y nuevas revisiones.

Verifica inventario y hashes del paquete. Explica si omite evidencia referenciada
por un manifiesto original; no lo presentes entonces como una copia íntegra del
run. Al distribuir resultados fallidos, conserva sus dictámenes para evitar que
"archivo disponible" se interprete como "aprobado para clase".
