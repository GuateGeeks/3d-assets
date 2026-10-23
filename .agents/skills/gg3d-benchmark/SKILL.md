---
name: gg3d-benchmark
description: Diseña y reporta una comparación controlada y repetible de flujos y modelos para creación 3D.
---

# Benchmark de flujos

Si el usuario solicita un único caso, entrega un piloto de ese brief y no lo
presentes como el M7 completo. Una muestra por condición compara esos artefactos;
no demuestra superioridad general de un modelo. Lee el
[protocolo de piloto y relevo](references/pilot-and-handoff.md) al ejecutar una
comparación, reparar una condición o distribuir sus resultados.

Consulta [criterios](../../../creation-lab/docs/ACCEPTANCE.md), [hitos](../../../creation-lab/docs/IMPLEMENTATION-PLAN.md) y [recomendaciones de modelos](../../../creation-lab/docs/MODELS.md). Para el M7 completo, usa seis briefs: dos low-poly, dos hard-surface detallados, uno orgánico y una escena. Fija semillas, referencias, límites, versiones, tiempo y repeticiones; conserva runs, fallos, gasto e intervención humana observada. Prefiere condiciones ligeras y CPU cuando sea práctico.

Oculta la identidad del modelo durante la calificación visual cuando sea viable. Mantén condiciones comparables y separa cumplimiento técnico, calidad visual, editabilidad, exportación, tiempo, intervención y costo. Registra ausencias y exclusiones. Compara los sistemas completos aparte de las comparaciones de modelos.

Los identificadores de partes no demuestran visibilidad ni contenido correcto.
Para material educativo, registra también un dictamen de contenido ligado a las
vistas observadas. Una puntuación total alta no anula un gate fallido. Diagnostica
discrepancias de exportación con [gg3d-export-qa](../gg3d-export-qa/SKILL.md).

Las asignaciones recomendadas no son resultados medidos. No inventes datos ni afirmes superioridad de Claude u otro proveedor sin evidencia suficiente y comparable. No actives llamadas API pagadas automáticamente. Si la automatización no existe, describe el protocolo y marca ejecución `NOT_RUN`.

Para comparación de motores de rigging sigue [gg3d-rigging](../gg3d-rigging/SKILL.md); los seis briefs de creación no son el corpus humano/cuadrúpedo. Distingue smoke con esqueleto oficial revisado de autorig con esqueleto propio, y usa la misma entrada preparada y procedencia. Una sola carga GPU a la vez. El pico de memoria de dispositivo incluye otras aplicaciones y un tiempo con verificación de checkpoints no es latencia pura de inferencia. No presentes los dos tiempos iniciales del corpus como un benchmark repetido ni una comparación ejecutada con SkinTokens.
