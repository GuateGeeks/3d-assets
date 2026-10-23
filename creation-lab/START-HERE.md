# GuateGeeks 3D · Inicio

Este laboratorio añade creación de assets a `3d-assets`. El catálogo y el
laboratorio de rigging siguen siendo componentes separados del mismo proyecto.

1. Lee [estado y evidencia](docs/STATUS.md).
   Para nuevas creaciones usa el [flujo iterativo Sol/Luna](docs/ITERATIVE-WORKFLOW.md):
   componentes, blockout con imágenes, revisión independiente y detalle.
2. Ejecuta el diagnóstico y el canario descritos en [README](README.md).
3. Usa los [criterios de aceptación](docs/ACCEPTANCE.md) antes de entregar.
4. Usa `lab/lab.py ingest --candidate` y después `rig --candidate` según la
   [guía de integración](docs/INTEGRATION.md) para transferir un candidato a rigging.
5. Sigue los [hitos](docs/IMPLEMENTATION-PLAN.md) para conceptos y producción.

Para un clon nuevo, empieza por [SETUP](../SETUP.md). El
[piloto educativo](benchmarks/animal-cell-20261022/README.md) incluye fuentes,
GLB, evidencia restaurable y un visor local que funciona sin instalar Blender.
Las calificaciones históricas pertenecen a sus runs; una ejecución nueva necesita
sus propias verificaciones y revisión.

El núcleo tiene una CLI local; los prompts M2–M7 preparan trabajo posterior,
no representan capacidades artísticas ya demostradas. El canario solo prueba
el circuito técnico. No es el robot educativo final ni un concepto aprobado.

## Entorno de este equipo

Blender nativo verificado: `D:\SteamLibrary\steamapps\common\Blender\blender.exe`,
5.2.3 LTS. El entorno de UniRig usa su propio Blender Python 4.2 en WSL.
No actualizar uno para hacer coincidir versiones con el otro.

Desde la raíz de `3d-assets`, con Python 3.10 o posterior:

```powershell
python creation-lab/create.py doctor --blender '/ruta/absoluta/a/blender'
python creation-lab/create.py --help
```

Si `python` es un alias de Microsoft Store, selecciona un intérprete real o usa
el lanzador que documenta README. La ubicación de Blender es local al equipo,
no un requisito para otros clones.

## Skills y agentes

Abre la carpeta `3d-assets` como proyecto para descubrir sus skills locales.
Invoca `$gg3d-pipeline` para coordinar; los otros seis skills cubren dirección
artística, low-poly, detalle, QA visual, exportación y benchmark.
Los skills preparados estarán disponibles al siguiente turno con ese ámbito.

La [selección de modelos](docs/MODELS.md) usa Sol/Luna por defecto y conserva la
asignación inicial como historia. No inicia llamadas de API ni cambia tu modelo global.
La [auditoría de dependencias](docs/DEPENDENCIES.md) distingue paquetes preparados,
código revisado y herramientas realmente probadas.

## Conexión MCP del proyecto

El ejemplo distribuido es `registry/codex-mcp.example.toml`. Sigue
[SETUP](../SETUP.md#skills-y-puente-mcp-opcional) para restaurar el runtime y crear
tu configuración local; `.codex/config.toml` no se versiona. Para descubrir los
skills, abre la carpeta `3d-assets` como proyecto. El lanzador opcional
inicia y administra su propia sesión Blender sin interfaz, con un puerto local
efímero; no utiliza una escena abierta del usuario. Su inicio, consulta y cierre
ya se probaron en el equipo original; comprueba la conexión en cada instalación.
Consulta [DEPENDENCIES](docs/DEPENDENCIES.md) para el alcance y los probes.
