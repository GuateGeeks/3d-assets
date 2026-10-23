# 07 · Benchmark reproducible (M7)

Lee [aceptación](../docs/ACCEPTANCE.md), [plan](../docs/IMPLEMENTATION-PLAN.md) y [perfiles recomendados](../docs/MODELS.md). Ejecuta el benchmark solo si el código disponible implementa esa capacidad; de lo contrario entrega protocolo y marca ejecución `NOT_RUN`.

Usa seis briefs: dos low-poly, dos hard-surface detallados, uno orgánico y una escena. Fija semillas, referencias, límites, herramienta/modelo, tiempo y número de repeticiones. Conserva cada run, fallo, intervención humana, tiempo observado y gasto observable. Compara los sistemas completos por separado de comparaciones de modelos.

Cuando sea viable, oculta identidad del modelo durante la calificación visual. Mide por separado calidad visual ciega, cumplimiento, editabilidad, exportación, tiempo, intervención y costo. Si un competidor no está disponible o no hay presupuesto, registra `NOT_RUN`; no hagas llamadas API ni incurras en gasto sin configuración y autorización explícitas.

Los modelos y esfuerzos de [MODELS.md](../docs/MODELS.md) son recomendaciones para asignar tareas, no evidencia de superioridad. No declares superioridad de Claude u otro proveedor sin resultados comparables suficientes. Reporta datos observados, fallos y límites de inferencia.

Aceptación: seis casos y repeticiones trazables con condiciones comparables, datos brutos conservados, ceguera documentada y resultados técnicos y visuales separados.
