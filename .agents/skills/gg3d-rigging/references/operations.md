# Operación: hechos comprobados y recuperación

Ámbito: instalación local observada el 22-10-2026; no son restricciones universales de UniRig. Consulta el [perfil](../../../../lab/envs/unirig.profile.json), [lock](../../../../lab/envs/unirig-linux-py311.lock.txt), [instalación](../../../../lab/reports/UNIRIG-SETUP.md) y [recibos](../../../../lab/reports/unirig-install.json) antes de adaptar otra máquina.

## Entorno y procesos

- RTX 3060 Ti 8192 MiB, Windows con CUDA en WSL2 Ubuntu. El Python de sistema 3.14 no es el entorno IA: se usa `lab/.local/envs/unirig/bin/python` 3.11.14, torch 2.5.1/cu124, numpy 1.26.4, transformers 4.51.3 y bpy 4.2.0.
- El commit y los checkpoints están fijados y hashados. Reutiliza los scripts de setup/probe y sus constraints; no actualices paquetes globalmente para resolver un import. Esta combinación usa wheels CUDA precompilados y no necesitó nvcc ni driver Linux adicional.
- `Run.execute` crea y cancela su propio grupo de procesos, conserva logs y limita cada etapa. El lock protege los comandos del laboratorio; no presupongas que detecta cargas de otras aplicaciones. Comprueba la memoria disponible sin cerrar procesos ajenos.
- Los picos muestreados son de la GPU completa, incluidos escritorio y otras aplicaciones; el RSS observado no suma todos los workers. Los tiempos incluyen preparación de checkpoints y validación. Conserva esa distinción al comparar.

## Fallos observados

| Síntoma | Causa y respuesta comprobada |
| --- | --- |
| Falta `raw_data.npz` aunque extraction termine con 0 | Upstream une output dir con el nombre de entrada; una entrada absoluta puede descartar el destino. El runner copia al workspace y pasa `--input=input/model.glb` o `input/reviewed.fbx` desde ese cwd. Mantén esos argumentos relativos. |
| `eglInitialize` falla en skinning WSL | El backend oficial alternativo Open3D funcionó. Conserva `--voxel-backend open3d` para este host y registra la elección; no declares pyrender roto en todos los equipos. |
| Wheel bpy CPython 3.11 contiene etiqueta interna cp39 | `fix_bpy_metadata.py` corrige WHEEL/RECORD instalados mediante reemplazo atómico, sin mutar binarios ni el inode compartido de la caché uv. Reutiliza su recibo, no edites la caché a mano. |
| SIGSEGV al cerrar Python después de una inspección GLB | En este bpy, el worker aislado valida, escribe/flush su informe y usa `os._exit(código_real)`. No conviertas un crash previo a la validación o un código distinto de cero en éxito. |
| Aparece una Icosphere o cambian conteos/límites al importar un rig | bpy puede crear geometría para visualizar huesos. Para nuevas inspecciones usa `disable_bone_shape=True` en importación glTF o filtra el auxiliar. Contrasta el JSON GLB desde disco. No cambies evidencia histórica para ocultar el conteo auxiliar. |
| Se descarga un texto pequeño en vez de la jirafa | El ejemplo usa Git LFS. El instalador valida tamaño y SHA del contenido completo respecto al puntero del commit; no pases el puntero como malla. |
| El navegador ve otro sitio/404, pero WSL devuelve 200 | Comprueba listeners y propietario en ambos hosts: puede haber otro servidor Windows en ese puerto. Usa un puerto libre y el host accesible desde el navegador, sin detener proyectos ajenos ni cambiar protecciones de red. |

Las configuraciones upstream se copian por run; no edites el checkout instalado para parchear un solo asset. El runner usa checkpoints/OPT locales verificados y modo offline de Hugging Face/Transformers durante inferencia; esto no es un aislamiento de red del sistema operativo.

## Transferir escala y apariencia

Para un candidato nuevo, sigue el [contrato](../../../../creation-lab/docs/INTEGRATION.md) y la [evidencia del adaptador](../../../../lab/reports/CREATION-ADAPTER.md). El GLB es la frontera entre Blender nativo 5.2 y bpy 4.2; conserva el `.blend` fuente sin abrirlo con una versión incompatible.

La preparación registra normalización e inversa; la restauración aplica la inversa a la jerarquía completa, incluidos huesos. No basta escalar el nodo de malla de un skin: verifica coordenadas físicas con `jointWorld × inverseBind × POSITION` y una reimportación limpia. Compara geometría evaluada, UV, asignaciones/conexiones de texturas, materiales y normales flat/smooth. Restaurar escala no debe ocultar una alteración de apariencia causada por el motor.

El adaptador admite geometría estática con QA y derechos aprobados. Rechaza evidencia incompleta, symlinks, referencias fuera del ámbito, hashes distintos y metadatos preparados falsos. `rig --candidate` no cambia los punteros del corpus ni su inventario visual. El canario de 0.30 m pasó restauración; su anatomía/deformación sigue sin certificar.

## Verificación proporcionada al cambio

Para documentación/skills, valida frontmatter, referencias y comandos `--help`; no gastes GPU. Para cambios del runner/adaptador, usa las pruebas relevantes de `lab/tests` (incluyen CPU Blender real cuando está disponible) y el verificador del sitio. No ejecutes la prueba de exclusión del lock mientras haya una inferencia activa.

```bash
python3 -m unittest discover -s lab/tests -v
python3 tools/check_site.py
# Si cambió el frontend publicable, construir antes de comprobar que _site coincide:
python3 tools/build_site.py
python3 tools/check_site.py
# Opcional, con Node y el paquete Khronos local ya verificado:
node lab/scripts/validate_review.cjs lab/.local/tools/gltf-validator/package
```

No descargues herramientas solo para repetir una comprobación documental. El build utiliza un inventario explícito y no publica runs. Consulta las exclusiones reales de `check_site.py`: que un directorio esté ignorado por Git no implica que esté excluido del escaneo de fuentes. Si otro trabajo está construyendo `_site`, no lo reconstruyas para esta comprobación; registra por separado integridad de fuentes y estado de la copia generada.
