# 01 · Núcleo funcional M1

Lee el [workflow iterativo](../docs/ITERATIVE-WORKFLOW.md): Sol `medium`
coordina y define la composición, Luna `medium` resuelve tareas delimitadas y componentes, y
Sol `medium` revisa imágenes en un contexto distinto del autor; Sol `high` queda
para diagnóstico difícil. Registra modelo/esfuerzo solicitados y reales de todos
los roles, sin sustitución silenciosa. Reutiliza componentes fiables antes del
detalle. Dos correcciones totales por sesión se comparten entre etapas, aparte
de la primera ejecución blockout y la primera detail; conserva todos los fallos.
Esta asignación es una propuesta operativa, no una superioridad medida.

Implementa y ejecuta el flujo headless mínimo del laboratorio conforme a [aceptación](../docs/ACCEPTANCE.md) y [contrato de integración](../docs/INTEGRATION.md). M1 es un canario técnico funcional: no lo confundas con la producción ni con la aprobación de concepto.

Primero ejecuta `python creation-lab/create.py doctor [--blender EXE | --bpy-python PYTHON]`. Prepara un brief JSON válido con ID, dimensiones en metros, frente/ejes, presupuesto y procedencia; valida con `brief --input brief.json`. Usa el brief como fuente de verdad y ejecuta `canary --brief PATH` con Blender nativo disponible o un `bpy` 4.2 ya existente. No descargues nada, no llames APIs y no alteres UniRig.

El canario funcional debe construir y guardar `.blend`, reabrirlo en proceso limpio, producir las cinco vistas reales `front`, `side`, `back`, `three-quarter` y `wireframe`, exportar GLB y reimportarlo en otro proceso limpio. Comprueba dimensiones con tolerancia declarada, ejes, geometría finita, presupuesto, materiales y que GLB no dependa de archivos externos. Mantén cada run y sus hashes; nunca reemplaces evidencia previa.

Continúa con `validate RUN` y `report RUN`. La revisión visual exige abrir las cinco vistas fuente y la imagen `reimport-three-quarter.png`; registra los seis pares exactos `VIEW=SHA256` del manifiesto con `review RUN --decision PASS|FAIL --reviewer NAME --notes TEXT --opened-images --evidence VIEW=SHA256`, repetido una vez por cada nombre de vista. El CLI comprueba los seis hashes. Ejecuta después `handoff REVIEW_RUN` usando el run que creó `review`. El handoff no publica ni promueve el asset.

Separa los gates `technical`, `visual` y `content`; conserva también `rights`/procedencia como requisito. Limita el contenido del canario a su brief técnico, sin atribuirle exactitud educativa. Para estos dictámenes usa únicamente `PASS`, `FAIL`, `BLOCKED` y `NOT_RUN`. Los hashes prueban integridad, no calidad artística. El canario técnico no pide aprobación de concepto ni blockout de producción. No solicites aprobación para los pasos técnicos autorizados; el gate que requiere aprobación explícita del usuario es el concepto y blockout del primer asset de producción antes del detalle.

Aceptación: run inmutable con brief, fuente `.blend`, cinco PNG fuente y captura PNG de la reimportación, GLB, logs, métricas, reimport limpio, hashes y reporte reproducible; fallos conservan evidencia y estados separados. Consulta [plan de hitos](../docs/IMPLEMENTATION-PLAN.md); capacidades futuras no se atribuyen a esta M1.
