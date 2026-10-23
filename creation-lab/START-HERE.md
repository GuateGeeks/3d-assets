# GuateGeeks 3D · Inicio

Este laboratorio añade creación de assets a `3d-assets`. El catálogo y el
laboratorio de rigging siguen siendo componentes separados del mismo proyecto.

1. Lee [estado y evidencia](docs/STATUS.md).
2. Ejecuta el diagnóstico y el canario descritos en [README](README.md).
3. Usa los [criterios de aceptación](docs/ACCEPTANCE.md) antes de entregar.
4. Usa `lab/lab.py ingest --candidate` y después `rig --candidate` según la
   [guía de integración](docs/INTEGRATION.md) para transferir un candidato a rigging.
5. Sigue los [hitos](docs/IMPLEMENTATION-PLAN.md) para conceptos y producción.

El núcleo tiene una CLI local; los prompts M2–M7 preparan trabajo posterior,
no representan capacidades artísticas ya demostradas. El canario solo prueba
el circuito técnico. No es el robot educativo final ni un concepto aprobado.

## Entorno de este equipo

Blender nativo verificado: `D:\SteamLibrary\steamapps\common\Blender\blender.exe`,
5.2.3 LTS. El entorno de UniRig usa su propio Blender Python 4.2 en WSL.
No actualizar uno para hacer coincidir versiones con el otro.

Desde la raíz de `3d-assets`, con Python 3.10 o posterior:

```powershell
python creation-lab/create.py doctor --blender 'D:\SteamLibrary\steamapps\common\Blender\blender.exe'
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

La [selección de modelos](docs/MODELS.md) preserva las recomendaciones de la
investigación. No requiere iniciar llamadas de API ni cambiar tu modelo global.
La [auditoría de dependencias](docs/DEPENDENCIES.md) distingue paquetes preparados,
código revisado y herramientas realmente probadas.

## Conexión MCP del proyecto

La entrada local está preparada en `../.codex/config.toml`. Para cargar los
skills y el puente, abre la carpeta `3d-assets` como proyecto. El lanzador
inicia y administra su propia sesión Blender sin interfaz, con un puerto local
efímero; no utiliza una escena abierta del usuario. Su inicio, consulta y cierre
ya se probaron. La aplicación aún no ha cargado esa entrada en este turno.
Consulta [DEPENDENCIES](docs/DEPENDENCIES.md) para el alcance y los probes.
