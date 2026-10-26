# Componentes y áreas de trabajo 3D

Integración local del 26 de octubre de 2026. Las carpetas `3d-assets*` son worktrees
del repositorio `GuateGeeks/3d-assets`: comparten historial Git, pero cada una tiene
su checkout y sus archivos ignorados. Un merge no traslada esos archivos locales.

## Componentes

| Área | Responsabilidad | Entrega |
| --- | --- | --- |
| `models/`, índices, `gallery/`, `tools/` | Originales, procedencia, consulta y publicación por inventario explícito | Catálogo y sitio estático |
| `creation-lab/` | Recetas Python/Blender, componentes, composición, detalle y QA | Fuente Blender, GLB y candidato revisado |
| `lab/` | Preparación, UniRig, pesos y revisión de deformaciones | Candidatos articulados; clips sujetos a revisión |
| `procedural-web/` | Ida y vuelta entre personajes del cotizador y Blender | Módulos JS de geometría, pivotes y clips |
| `.agents/skills/` | Contratos e instrucciones reutilizables | Guías operativas verificadas por `tools/check_skills.py` |

Creación entrega a rigging mediante el [contrato de candidatos](../creation-lab/docs/INTEGRATION.md).
El [puente web](../procedural-web/README.md) adapta los 12 huesos, clases de color y
poses del cotizador; no es un conversor genérico de personajes. El cotizador sigue
siendo dueño de su publicación. Code Studio y Sócrates permanecen como integraciones
posteriores. El puente MCP opcional es otra herramienta independiente.

## Historial reconciliado

| Área local | Punto inicial | Papel tras la integración |
| --- | --- | --- |
| `3d-assets` | `43f7297`, `claude/conciliacion-20261025` | Checkout principal en `main`, con creación, experimentos y puente |
| `3d-assets-blender` | `43f7297` más cambios locales | Puente registrado en `5a1e242`; rama actualizada por fast-forward al corte integrado |
| `3d-assets-animal-cell-wip` | `1773760` | Referencia histórica conservada; su trabajo ya está integrado en `main` |
| `3d-assets-release-20261022` | `8f4a59a`, detached HEAD | Corte histórico conservado, sin desplazarlo a una versión nueva |

Se consultó `origin/main` mediante fetch (`af1fa40`) y se fusionó su historial con
la rama de conciliación. Después se fusionó el puente con un merge explícito.
Se conservó también la exclusión local de `meshy_output/`. No se reescribieron
commits ni se eliminaron ramas o worktrees. `main`, conciliación y puente quedan
alineados localmente; actualizar las referencias locales no publica cambios en GitHub.

## Evidencia y reproducibilidad

- Los benchmarks de célula inicial, célula Claude y escuela, y la reconstrucción
  del estudiante conservan sus archivos y dictámenes históricos.
- Antes de integrar se inventariaron 6.273 archivos de modelos, benchmarks,
  experimentos, informes de rigging e índices mediante SHA-256.
- Los 202 archivos locales del puente se copiaron sin alterar bytes ni recibos.
  Los originales permanecen en el worktree Blender; las copias y las pruebas nuevas
  residen en `procedural-web/.local/`. Se conserva la configuración de este equipo,
  cuyo receptor es `cotizador-meshy`; un clon nuevo necesita su propia configuración.
- El respaldo previo, los parches, inventario completo y logs de esta integración
  permanecen localmente en `lab/.local/integration-20261026/`.
- El [informe del corte](integration-20261026.json) registra comprobaciones nuevas
  y límites. La integridad de archivos y las pruebas técnicas no sustituyen revisión
  visual, biológica ni de deformación.

Los ZIP versionados de los benchmarks pueden verificarse con sus `restore.py --check`;
[SETUP](../SETUP.md) explica instalación y uso. Los grandes entornos, los runs locales
y la configuración de equipo no se publican ni se incorporan automáticamente al catálogo.

## Alcance de la validación de este corte

El puente pasó sus cuatro pruebas, incluida la ida y vuelta real con `bpy` 4.2 y
la comparación de articulaciones de ambos personajes con Three.js. Se verificaron
12 skills, 255 archivos vendorizados y los paquetes restaurables de los tres
benchmarks. La suite de creación pasó con tres probes Blender opt-in omitidos.

El checkout de trabajo contiene enlaces temporales históricos de Chromium en
`creation-lab/.local/claude-school-20261023/web/detail-v1/qa/.prof-desk/`.
El escáner estricto los rechaza; se conserva ese resultado y no se debilita el
control ni se eliminan los perfiles. Una copia limpia del contenido integrado pasó
construcción, integridad de los 1.045 modelos, rutas, exclusión de laboratorios,
escaneo de material privado y la suite de rigging (seis pruebas dependientes del
entorno local omitidas; esas seis sí pasaron en el checkout original).
