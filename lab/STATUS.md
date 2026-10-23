# Estado y relevo del laboratorio de rigging

Actualizado el 22 de octubre de 2026. Este es un mapa de capacidades y evidencia, no un recibo permanente de disponibilidad. En un clon nuevo pueden faltar todos los archivos de `lab/.local/`; consulta el perfil, ejecuta diagnóstico y verifica recibos antes de continuar. El [manual](README.md), el CLI real y los informes por run gobiernan la ejecución.

| Área | Estado documentado | Evidencia y alcance |
| --- | --- | --- |
| UniRig local | Instalación, CUDA y smoke verificados | [Instalación](reports/UNIRIG-SETUP.md), [perfil](envs/unirig.profile.json), [recibo](reports/unirig-install.json). El smoke usa skin sobre esqueleto oficial revisado. |
| Corpus humano/cuadrúpedo | Preparación, esqueleto propio, pesos y GLB completados | [Informe](reports/CORPUS-REVIEW.md), `rig-human.json` y `rig-quadruped.json`. Man 29 huesos/228.897 s, Wolf 38/160.762 s observados; no son benchmarks repetidos. |
| Galería de deformación | Comparación y poses estáticas implementadas | Cinco poses por modelo, cámaras vinculadas, esqueletos, métricas y notas exportables; [QA](reports/corpus-ui-qa.json). Cero clips nuevos. |
| Calidad del corpus | Pendiente de aprobación final | Humano: revisar rodilla izquierda y codos antes de clips. Wolf conserva silueta en la inspección inicial; falta dictamen final. [Hallazgos](review-findings.json) ligados a GLB y mapa. |
| Entrada de creación | Ingestión y restauración de escala/apariencia verificadas | [Adaptador](reports/CREATION-ADAPTER.md), [recibo](reports/creation-adapter-validation.json), [contrato](../creation-lab/docs/INTEGRATION.md). Canario de 0.30 m, cero clips; no certifica anatomía ni un robot de producción. |
| Pruebas | El corpus cerró con 10; el corte posterior del adaptador registra 26, incluidas 5 de Blender CPU | Son evidencias de cortes distintos. Consultar [recibo del adaptador](reports/creation-adapter-validation.json) y ejecutar pruebas adecuadas al cambio; no anunciar las 26 como reevaluación de toda la calidad visual. |
| SkinTokens | Evaluación local pendiente | No hay inferencia local verificada en este laboratorio. No considerar resuelta su necesidad de memoria en 8 GB. |
| Clips y derivados aprobados | Pendientes | Corrección/revisión de pesos y pivotes precede a clips, normalización final de jerarquía y empaquetado. |
| Code Studio / Sócrates | Integración posterior | El trabajo y las validaciones se completan en `3d-assets`. |

## Continuar desde aquí

1. Leer `AGENTS.md`, [gg3d-rigging](../.agents/skills/gg3d-rigging/SKILL.md) y los informes del asset concreto. Identificar trabajo concurrente antes de editar.
2. Para el corpus, revisar/corregir rodilla y codos del humano en una variante nueva; inspeccionar de nuevo anatomía y pesos de ambos modelos. Conservar el baseline y sus mapas.
3. Para creación, usar `ingest` y `rig --candidate` con la entrega revisada. Mantener coordenadas físicas y apariencia; definir un mapa anatómico propio antes de incorporar un nuevo rig a la galería.
4. Registrar dictamen ligado a hashes. Crear clips cuando esté permitido por el alcance y la calidad revisada; exportar notas o pasar el validador no produce aprobación automática.

`reports/latest-*.json`, `reports/review-*.json` y los manifiestos de trabajo apuntan al último resultado. La evidencia se conserva en runs independientes. No reparar en silencio un export revisado ni reescribir un informe histórico para reflejar una prueba posterior.

Al cerrar otro corte, actualizar esta tabla con fecha, evidencia y límites nuevos. Actualizar skills solo si cambian decisiones, comandos o invariantes; conservar cifras cambiantes en los informes y este estado.
