---
name: gg3d-benchmark
description: Diseña y reporta una comparación controlada y repetible de flujos y modelos para creación 3D.
---

# Benchmark de flujos

Para composición, componentes y correcciones lee el
[workflow iterativo Sol/Luna](../../../creation-lab/docs/ITERATIVE-WORKFLOW.md).
Es la referencia única de roles, dos rondas por defecto y gates separados;
los perfiles propuestos aún no demuestran superioridad medida.


Si el usuario solicita un único caso, entrega un piloto de ese brief y no lo
presentes como el M7 completo. Una muestra por condición compara esos artefactos;
no demuestra superioridad general de un modelo. Lee el
[protocolo de piloto y relevo](references/pilot-and-handoff.md) al ejecutar una
comparación, reparar una condición o distribuir sus resultados.

Consulta [criterios](../../../creation-lab/docs/ACCEPTANCE.md), [hitos](../../../creation-lab/docs/IMPLEMENTATION-PLAN.md) y [recomendaciones de modelos](../../../creation-lab/docs/MODELS.md). Por defecto la comparación futura usa solo Sol, Sol+Luna y solo Luna con la misma biblioteca, herramientas, presupuestos y rondas; respeta otros modelos solicitados explícitamente en un protocolo aislado. Recomienda al menos tres autorías independientes por condición para un piloto. Reejecutar el mismo generador no crea una autoría nueva. Para el M7 completo, usa seis briefs: dos low-poly, dos hard-surface detallados, uno orgánico y una escena. Fija semillas, referencias, límites, versiones, tiempo y repeticiones; conserva runs, fallos, gasto con telemetría disponible e intervención humana observada; no infieras costo a partir de tiempos de Blender. Prefiere condiciones ligeras y CPU cuando sea práctico.

En el [benchmark Claude](../../../creation-lab/benchmarks/claude-animal-cell/RESULTS.md),
confirma el modelo resuelto en los transcripts del runtime, no solo por alias. Antes del
lote, comprueba que cada vista común realmente muestra lo que promete (el `wireframe`
del worker casi no se ve a 768 px). Da al revisor un validador de su JSON y a los autores
un directorio propio: un scratchpad de sesión es compartido entre subagentes. El `usage`
de los transcripts subestima la salida; repórtalo como cota inferior.

Oculta la identidad del modelo durante la calificación visual cuando sea viable. Mantén condiciones comparables y separa cumplimiento técnico, calidad visual, editabilidad, exportación, tiempo, intervención y costo. Registra ausencias y exclusiones. Compara los sistemas completos aparte de las comparaciones de modelos.

Los identificadores de partes no demuestran visibilidad ni contenido correcto.
Para material educativo, registra también un dictamen de contenido ligado a las
vistas observadas. Una puntuación total alta no anula un gate fallido. Diagnostica
discrepancias de exportación con [gg3d-export-qa](../gg3d-export-qa/SKILL.md).

Para orquestar autores por modelo, fija antes contrato, kit de primitivas cerradas y un verificador puro de módulos: así autores baratos entregan piezas acotadas en paralelo. Separa el costo de autores, revisores y coordinador; en la [prueba de la escuela](../../../creation-lab/benchmarks/school-flat-20261023/RESULTS.md) el coordinador pesó entre 46 y 75 % del costo estimado. Los transcripts registran la salida de forma parcial: toma el máximo por mensaje, estima la salida visible como cota inferior y declara tarifas y su fecha. Una sola revisión por gate varía entre revisores; en comparaciones usa doble revisión o calibración y reporta el desacuerdo. Si dos condiciones comparten coordinador, congela sus mensajes y declara lo que la segunda heredó.

Las asignaciones recomendadas no son resultados medidos. No inventes datos ni afirmes superioridad de Claude u otro proveedor sin evidencia suficiente y comparable. No actives llamadas API pagadas automáticamente. Si la automatización no existe, describe el protocolo y marca ejecución `NOT_RUN`.

Para comparación de motores de rigging sigue [gg3d-rigging](../gg3d-rigging/SKILL.md); los seis briefs de creación no son el corpus humano/cuadrúpedo. Distingue smoke con esqueleto oficial revisado de autorig con esqueleto propio, y usa la misma entrada preparada y procedencia. Una sola carga GPU a la vez. El pico de memoria de dispositivo incluye otras aplicaciones y un tiempo con verificación de checkpoints no es latencia pura de inferencia. No presentes los dos tiempos iniciales del corpus como un benchmark repetido ni una comparación ejecutada con SkinTokens.
