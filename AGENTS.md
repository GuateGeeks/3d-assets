# Trabajo en 3d-assets

La entrada común para nuevas creaciones, escenas y proveedores es
[studio/README.md](studio/README.md) con [estado/evidencia](studio/docs/STATUS.md)
y el skill [gg3d-studio](.agents/skills/gg3d-studio/SKILL.md). No confundir un
adapter implementado con una cuenta conectada o una inferencia verificada.
Mantén Studio, sus dependencias y runs fuera del inventario público; los módulos
privados de consumidores no se copian a este repositorio.

Este repositorio contiene la biblioteca original, el laboratorio de rigging en `lab/`
el laboratorio de creación en `creation-lab/` y el puente del cotizador en
`procedural-web/`. Para este último lee `.agents/skills/gg3d-blender-web/SKILL.md`
y `procedural-web/README.md`; conserva sus runs y configura el checkout receptor
explícitamente. Code Studio y Sócrates son
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

El workflow de producción usa solo Sol/Luna por defecto: Sol `medium` para composición y
coordinación, Luna `medium` para tareas delimitadas, componentes y variantes,
y otro contexto Sol `medium` para revisión independiente con imágenes abiertas.
Escala a Sol `high` únicamente para diagnóstico difícil. Registra modelo y esfuerzo
solicitados y reales de todos los roles; si no están disponibles, registra el bloqueo,
sin sustituirlos silenciosamente. Los perfiles son planificación, no enforcement
remoto ni resultados de benchmark. El modo `claude` de `iterate.py` (IDs Claude
exactos) existe solo por elección explícita y no cambia el default Sol/Luna. Lee el
[workflow iterativo](creation-lab/docs/ITERATIVE-WORKFLOW.md) para el protocolo. Una petición explícita de benchmark con otros modelos define
una condición aislada; conserva el default de producción y registra sus diferencias.

Reutiliza componentes fiables de `creation-lab/components` y resuelve blockout,
escala y composición antes del detalle. Por defecto, permite dos rondas de
corrección totales por sesión, compartidas entre etapas y aparte de la primera
ejecución blockout y la primera detail; conserva fallos y evidencia nueva por ronda. No relajes gates ni presupuestos para cerrar: técnica, visual y
contenido se dictaminan por separado; procedencia/derechos sigue siendo requisito.
Conserva escala física, materiales y procedencia al transferir a rigging.
Esta mejora de proceso aún necesita comparación controlada; no implica superioridad
medida sobre el piloto histórico.

Al cerrar un corte, conserva el aprendizaje que cambia decisiones en el skill
correspondiente y enlaza evidencia desde el estado del laboratorio. Comprueba
comandos contra el CLI y referencias locales. No dupliques todo el historial en
los skills ni conviertas una solución de este host en una restricción universal.

Para entregar un clon reproducible, sigue `SETUP.md` y comprueba los skills con
`python tools/check_skills.py`. El benchmark educativo incluye archivos de evidencia
restaurables; no confundas los informes de 2026 con verificaciones del equipo nuevo.
Usa los locks y los argumentos del CLI, evitando copiar rutas de un recibo histórico.
