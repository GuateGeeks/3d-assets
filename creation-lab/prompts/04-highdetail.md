# 04 · Master detallado y derivado optimizado (M4)

Lee el [workflow iterativo](../docs/ITERATIVE-WORKFLOW.md): Sol `medium`
coordina y define la composición, Luna `medium` resuelve tareas delimitadas y componentes, y
Sol `medium` revisa imágenes en un contexto distinto del autor; Sol `high` queda
para diagnóstico difícil. Registra modelo/esfuerzo solicitados y reales de todos
los roles, sin sustitución silenciosa. Reutiliza componentes fiables antes del
detalle. Dos correcciones totales por sesión se comparten entre etapas, aparte
de la primera ejecución blockout y la primera detail; conserva todos los fallos.
Esta asignación es una propuesta operativa, no una superioridad medida.

Lee [aceptación](../docs/ACCEPTANCE.md) y usa el robot low-poly o blockout aprobado como fuente de identidad. Mantén un master detallado editable separado de su derivado optimizado. Conserva diseño, escala y proporciones; si aún no existe aprobación explícita de concepto/blockout, solicita esa revisión antes de detallar.

Limita el derivado a ≤40000 triángulos y ≤4 materiales, con texturas ≤2048 px. Crea UV y bake cuando hagan falta. Conserva silueta y partes significativas al optimizar. Verifica las métricas del GLB exportado.

Produce evidencia clay, wireframe, vistas generales y closeups. Usa por defecto hasta dos rondas de corrección totales por sesión compartidas con blockout, aparte de la primera ejecución de cada etapa, cada una con defectos observados, evidencia conservada y cambios documentados. Si el límite se agota con gates pendientes, registra el bloqueo sin rebajar criterios. Reabre fuente y derivado en proceso limpio y compara materiales, texturas, ejes y dimensiones. Mantén ejecución técnica autorizada sin nuevas solicitudes de aprobación; documenta QA visual aparte.

Aceptación: master separado y editable, derivado dentro de presupuestos comprobados, identidad conservada, evidencia real y estado técnico/visual trazable.

Dictamina técnica, apariencia visual y contenido por separado. En material educativo, abre las vistas y comprueba visibilidad/identificación de cada parte y sus relaciones; IDs y etiquetas no bastan. Conserva derechos/procedencia y no uses límites del robot para otro brief. Para rigging conserva escala física, materiales y procedencia; la aceptación geométrica no aprueba deformaciones.
