# 07 · Benchmark reproducible (M7)

Lee el [workflow iterativo](../docs/ITERATIVE-WORKFLOW.md),
[aceptación](../docs/ACCEPTANCE.md), [plan](../docs/IMPLEMENTATION-PLAN.md),
[perfiles](../docs/MODELS.md) y [protocolo de piloto](../../.agents/skills/gg3d-benchmark/references/pilot-and-handoff.md).
Distingue capacidades verificadas, workflow propuesto y benchmark pendiente;
si la automatización requerida no existe, entrega protocolo y ejecución `NOT_RUN`.

Compara solo Sol, Sol+Luna y solo Luna con el mismo brief, referencias, biblioteca
versionada de componentes, herramientas, semillas, presupuestos y dos rondas de
corrección máximas. Fija las condiciones antes de autoría. Usa `medium` por defecto;
una escalada Sol `high` para diagnóstico difícil se declara como intervención y no
se oculta dentro de una condición controlada. Registra modelo/esfuerzo solicitados
y reales de todos los roles; si falta un modelo, registra `BLOCKED` sin sustitución.

Para un piloto se recomiendan al menos tres autorías independientes por condición.
Un rerun de un generador no cuenta como otra autoría. El M7 completo mantiene seis
briefs: dos low-poly, dos hard-surface detallados, uno orgánico y una escena. Un
piloto sobre un brief no demuestra capacidad general ni reemplaza ese alcance.

El revisor usa un contexto distinto de los autores, abre las seis imágenes y
registra hashes y observaciones por parte/requisito de contenido. Define una
misma evaluación externa para comparar condiciones y declara el modelo/esfuerzo
del revisor; separa esa evaluación de la revisión interna de cada modo. Oculta
identidad de autores cuando sea viable. Conserva fallos iniciales, reparaciones,
intervención humana, tiempo observado y telemetría disponible. No infieras costo,
tokens o latencia del modelo a partir de tiempos de Blender.

Reporta por separado gates técnico, visual y de contenido; conserva también
procedencia/derechos, editabilidad y exportación. Un total numérico no anula un
gate fallido. No alteres dictámenes ni calificaciones históricas ni relajes gates.
No hagas llamadas API pagadas sin configuración y autorización aplicables.

Aceptación: condiciones y autorías trazables, evidencia bruta conservada,
evaluación independiente documentada y alcance explícito de lo no ejecutado.
Las asignaciones propuestas no demuestran superioridad antes de medir.
