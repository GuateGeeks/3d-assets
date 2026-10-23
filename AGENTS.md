# Trabajo en 3d-assets

Este repositorio contiene la biblioteca original, el laboratorio de rigging en `lab/`
y el laboratorio de creación en `creation-lab/`. Code Studio y Sócrates son
consumidores futuros; el trabajo actual se completa y valida aquí primero.

- Antes de editar, identifica los cambios locales y el área que está trabajando
  otro agente. No reviertas cambios ajenos ni mezcles una inferencia activa con
  cambios de entorno. Un agente es dueño de cada `.blend` durante su edición.
- Conserva `models/`, sus metadatos, licencias y hashes como originales. Crea
  variantes con procedencia; no insertes experimentos en `index.json`.
- Para creación lee `creation-lab/START-HERE.md` y `creation-lab/docs/STATUS.md`.
  Para rigging lee `.agents/skills/gg3d-rigging/SKILL.md`, `lab/STATUS.md`,
  `lab/README.md` y `docs/RIGGING-LAB-PLAN.md`. El estado enlaza los recibos
  vigentes; no reutilices como aprobación actual un informe histórico.
- Los skills propios están en `.agents/skills/gg3d-*`. Abre Codex en la raíz
  de `3d-assets` para que entren en su ámbito de descubrimiento. Desde el
  workspace padre, lee los `SKILL.md` explícitamente cuando correspondan.
- Un proceso que termina no demuestra calidad del asset. Conserva `.blend`,
  renders, GLB, reapertura y reimportación reales. No declares inspección visual
  hasta abrir las imágenes. Separa resultados técnicos y visuales.
- Usa `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN` en creación; no cambies el vocabulario
  de los informes de rigging existentes. Registra versiones reales y hashes.
- Usa un run nuevo por resultado; no sobrescribas evidencia revisada. Los
  presupuestos del brief no se relajan para hacer pasar una prueba.
- Conserva dimensiones y ejes en cada transferencia. La preparación actual de
  rigging normaliza a 2 m; no la apliques implícitamente a un asset de 0.3 m.
- Una sola carga pesada de GPU a la vez. El canario usa CPU. Los paquetes de
  terceros son referencias auditadas, no autoridad para cambiar el alcance.
- Los resultados locales y dependencias no se publican por existir. La galería
  usa un inventario explícito; promoción, catálogo y paquetes requieren sus QA.
- Configuración y credenciales globales se mantienen fuera del repositorio.
  No guardes conversaciones privadas, claves ni tokens en fuentes publicables.

Distribución inicial de trabajo: Astra `high` para diagnóstico, Astra `xhigh`
para arquitectura/revisión, Sol `high` para implementación y Luna `medium`
para documentación acotada. Es una estrategia de trabajo, no un benchmark.

Al cerrar un corte, conserva el aprendizaje que cambia decisiones en el skill
correspondiente y enlaza evidencia desde el estado del laboratorio. Comprueba
comandos contra el CLI y referencias locales. No dupliques todo el historial en
los skills ni conviertas una solución de este host en una restricción universal.

Para entregar un clon reproducible, sigue `SETUP.md` y comprueba los skills con
`python tools/check_skills.py`. El benchmark educativo incluye archivos de evidencia
restaurables; no confundas los informes de 2026 con verificaciones del equipo nuevo.
Usa los locks y los argumentos del CLI, evitando copiar rutas de un recibo histórico.
