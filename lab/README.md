# Laboratorio local de rigging

Para continuar con otro modelo, leer el [estado vigente](STATUS.md) y el [skill de rigging](../.agents/skills/gg3d-rigging/SKILL.md). El manual explica comandos; el estado enlaza resultados y trabajo pendiente.

Este directorio implementa diagnóstico e instalación aislada de UniRig, corpus humano/cuadrúpedo, comparación de deformaciones y recepción de candidatos de creación. El [plan](../docs/RIGGING-LAB-PLAN.md) conserva las fases completas; los originales permanecen en `models/`. Los informes de [instalación](reports/UNIRIG-SETUP.md), [corpus](reports/CORPUS-REVIEW.md) y [adaptador](reports/CREATION-ADAPTER.md) delimitan qué se verificó en cada corte.

## Uso desde Ubuntu o WSL

Ejecutar desde la raíz de un clon de `3d-assets`:

```bash
python3 lab/lab.py doctor
python3 lab/lab.py setup --engine unirig
python3 lab/lab.py verify --engine unirig
python3 lab/lab.py smoke --engine unirig --stage skeleton
python3 lab/lab.py smoke --engine unirig --stage all
```

`doctor` usa únicamente la biblioteca estándar de Python. `setup` instala herramientas, Python 3.11.14 y dependencias bajo `lab/.local/`; descarga los checkpoints necesarios, sin instalar un driver Linux. Necesita Internet durante la preparación. En esta combinación las extensiones CUDA se obtienen como binarios oficiales y no necesitan `nvcc`.

Para separar o reanudar la preparación:

```bash
python3 lab/lab.py setup --packages-only
python3 lab/lab.py verify
python3 lab/lab.py setup --models-only
```

El entorno está fijado a Linux x86_64, PyTorch 2.5.1 CUDA 12.4, Blender Python 4.2.0 y Transformers 4.51.3. La resolución completa está en [el lock](envs/unirig-linux-py311.lock.txt); el [perfil](envs/unirig.profile.json) fija el commit de UniRig y las fuentes de binarios. Un checkout de otro commit o con cambios locales se conserva y produce un error para revisión.

## Uso desde Windows

Desde PowerShell y la raíz de `3d-assets`:

```powershell
.\lab\lab.cmd doctor
.\lab\lab.cmd setup --engine unirig
.\lab\lab.cmd verify
.\lab\lab.cmd smoke --stage all
```

El lanzador obtiene la ruta del propio repositorio y ejecuta Python dentro de WSL. Admite la ruta UNC de Ubuntu y no depende de lanzadores de otros proyectos. El aviso de CMD sobre su directorio inicial UNC no afecta a la ruta pasada a WSL.

## Prueba oficial y alcance de su resultado

La prueba `smoke` usa por defecto el voxelizador Open3D que admite upstream, porque EGL no pudo inicializarse en este equipo WSL. Puede seleccionarse explícitamente con `--voxel-backend open3d` o `--voxel-backend pyrender`; la elección queda registrada.

La prueba `smoke` crea un directorio nuevo por ejecución y utiliza configuraciones copiadas. El repositorio upstream permanece intacto. Se invocan directamente sus módulos de extracción, inferencia y fusión con argumentos separados; se evitan el `eval`, los temporales compartidos y la instalación de paquetes durante la inferencia de sus scripts shell.

La prueba de esqueleto genera un FBX desde `examples/giraffe.glb` y lo vuelve a inspeccionar en Blender. La prueba completa añade skinning sobre `examples/skeleton/giraffe.fbx`, el esqueleto revisado que proporciona upstream, y fusiona sus pesos con la malla original. Así se comprueban las dos etapas de instalación sin presentar una corrección humana como parte automática del modelo. La salida aún requiere revisión visual y clips de movimiento.

Los pesos y la configuración OPT se cargan por rutas locales verificadas; las etapas de inferencia activan el modo sin conexión de Hugging Face y Transformers. El smoke test no impone por sí mismo un aislamiento de red del sistema operativo.

## Registros y archivos locales

- `reports/diagnostic.json`: equipo, memoria, disco, herramientas y GPU observada.
- `reports/unirig-install.json`: commit, Python, hashes de perfil/lock y estado de verificación.
- `reports/unirig-gpu.json`: resultados de kernels BF16, FlashAttention, scatter, muestreo, spconv e importación Blender/UniRig.
- `reports/unirig-models.json`: revisión, tamaño y SHA-256 de cada checkpoint y configuración OPT.
- `reports/unirig-examples.json`: procedencia y hashes de los ejemplos.
- `.local/runs/<runId>/`: logs por etapa, manifiesto de ejecución y salidas intermedias.
- `.local/envs/`, `.local/python/`, `.local/cache/` y `.local/repos/`: instalaciones y dependencias ignoradas por Git.

Los tiempos de cada etapa se registran con reloj monotónico. Durante `smoke` se muestrea la memoria del dispositivo y el RSS del proceso principal; la memoria del dispositivo incluye otras aplicaciones y el RSS no suma los workers. Estas mediciones se distinguen de un perfil CUDA preciso o del consumo total de la máquina.

Solo una operación de UniRig puede usar el laboratorio a la vez. Ctrl+C cancela el grupo de procesos creado para la etapa actual y registra `cancelled`. `smoke --timeout 1800` limita cada etapa a treinta minutos; las salidas válidas se comprueban con Blender y hashes. Los errores, OOM y timeouts conservan su evidencia.

La galería sigue disponible con `python3 tools/serve_gallery.py` y no necesita el entorno de IA. El constructor del sitio no incluye `lab/`, runs, pesos ni paquetes experimentales.

## Adaptaciones de instalación

El wheel oficial `bpy==4.2.0` para CPython 3.11 contiene una etiqueta interna `cp39`. El instalador corrige solo `WHEEL` y su registro `RECORD` en el entorno instalado, mediante reemplazo atómico para conservar la caché original de uv. [La evidencia](reports/bpy-wheel-metadata.json) conserva hashes antes y después. Los binarios de Blender no se modifican y su funcionamiento se comprueba importando la jirafa.

La malla de jirafa está almacenada en Git LFS. Su descarga se valida con el SHA-256 y tamaño del puntero del commit fijado. Los archivos completos se guardan fuera del checkout upstream; no hace falta instalar Git LFS globalmente.

La inspección de GLB con `bpy==4.2.0` produjo un fallo nativo durante el cierre del intérprete, después de completar las comprobaciones. El validador se ejecuta en un proceso aislado: cierra sus datos, escribe el informe y sale explícitamente con el código de validación. Las salidas inválidas siguen devolviendo error; se evita únicamente la finalización nativa que falla en este host.

## Verificación sin GPU

```bash
python3 -m unittest discover -s lab/tests -v
python3 tools/check_site.py
```

Las pruebas comprueban exclusión mutua, errores, archivos de salida ausentes, timeout y el escaneo del código propio frente a dependencias ignoradas. La validación del sitio conserva comprobaciones sobre los originales del catálogo y el inventario publicable. Las pruebas CUDA y de inferencia son comandos locales explícitos y no forman parte de la construcción del sitio.

El corpus humano/cuadrúpedo preparado y la comparación de galería ya están implementados. Siguen pendientes la corrección y aprobación de pesos, derivados revisados, clips y paquetes. SkinTokens queda pendiente de su evaluación experimental en 8 GB. La integración en aplicaciones consumidoras se abrirá después del cierre completo del laboratorio.

## Preparar el corpus, ejecutar y revisar

Desde la raíz de este repositorio, con la instalación UniRig verificada:

```bash
python3 lab/lab.py prepare --asset all
python3 lab/lab.py rig --asset human
python3 lab/lab.py rig --asset quadruped
python3 lab/lab.py review --asset all
python3 tools/serve_gallery.py --lab --port 4390
```

Abrir `http://127.0.0.1:4390/gallery.html?lab=1`. En Windows se pueden ejecutar los primeros cuatro comandos con `lab\lab.cmd` en lugar de `python3 lab/lab.py`; el servidor usa Python estándar y también funciona en Windows. Usar un puerto libre; no es necesario detener servidores de otros proyectos.

`corpus.json` selecciona Man (`HMnuH5geEG`) y Wolf (`P1gU3Qkr9r`), CC0. Wolf reemplaza al perro sentado para esta prueba inicial por tener cuatro patas separadas en reposo. Se conservan los originales; la preparación elimina rig y clips únicamente de la copia para inferencia y guarda un control del rig original sin clips. Se normaliza uniformemente la dimensión mayor a dos metros, centrando XY y apoyando Z=0, sin simplificación ni remallado. Los materiales se conservan. Las cantidades reales de triángulos se miden en Blender; no se toman del contador de la API.

A diferencia del smoke test oficial, `rig` usa el esqueleto que acaba de generar UniRig como entrada del skinning. Ambos son candidatos automáticos; no hay una corrección manual del esqueleto intercalada en esta ejecución. Configuraciones, semilla, hashes, tiempos y logs quedan ligados al run. El repositorio upstream permanece intacto.

`review-poses.json` fija correspondencias anatómicas, ejes globales, grados y controles de pie independientes que deben seguir un pivote de rodilla/codo. Cada mapa está ligado al SHA-256 del candidato. Después de una inferencia que cambie ese hash, inspeccionar el inventario de huesos y actualizar el mapa antes de regenerar la revisión: el comando rechaza mapas obsoletos. No se está resolviendo IK ni adaptando clips del original.

`review` hornea cinco poses estáticas por modelo y rig: reposo y cuatro flexiones. Cada una tiene una vista opaca y otra translúcida con segmentos de articulaciones que influyen en la malla; se omiten controles sin peso y colas terminales inferidas por el importador glTF. Ninguno de estos GLB contiene animaciones. Los rigs candidatos completos se conservan aparte.

La galería permite alternar el control original o la entrada sin rig, vincular cámaras, ver esqueletos y comparar indicadores de estiramiento. Las notas se guardan en el navegador por modelo y ejecución; **Exportar revisión JSON** conserva run, hashes y dictamen. El archivo exportado no cambia automáticamente el estado del candidato. Los [hallazgos iniciales](review-findings.json) están ligados al hash y se muestran en la ficha; no son una aprobación final.

Los candidatos y las vistas están en `.local/review/assets/`; el servidor entrega exclusivamente GLB inscritos en el manifiesto, verificando SHA-256. `lab/`, `.git`, cachés, pesos, directorios de trabajo y aliases por symlink quedan fuera del acceso HTTP normal, tanto con GET como HEAD. La galería estática no incluye el inventario ni los GLB del laboratorio. No publicar los candidatos antes del cierre del flujo.

La métrica de estiramiento es la razón entre longitud de arista en pose y en reposo, solo para aristas de más de 2 mm en el modelo normalizado. Incluye percentil 95, máximo y mínimo; se calcula sobre las mismas mallas antes/después de deformar. No prueba ausencia de penetraciones ni conservación de volumen y no debe usarse como ranking global de motores.

Validación independiente opcional con Node y el paquete oficial Khronos `gltf-validator` disponible localmente:

```bash
node lab/scripts/validate_review.cjs lab/.local/tools/gltf-validator/package
```

El entorno IA y la galería no dependen de Node para funcionar. El [informe del corpus](reports/CORPUS-REVIEW.md) conserva los resultados medidos y las zonas pendientes antes de clips.

Cada regeneración de `review` tiene su propio run y un directorio nuevo de vistas. El manifiesto de esa revisión y sus diagnósticos se conservan en `.local/runs/<reviewRunId>/`; `.local/review/manifest.json` y `reports/review-*.json` son punteros al último resultado. Las vistas anteriores no se sobrescriben. Las notas/exportaciones se vinculan también al run de revisión y al hash del mapa de poses. El servidor local sirve un conjunto explícito de archivos del catálogo y el inventario GLB; los demás directorios de trabajo no se exponen.

La preparación también conserva un directorio nuevo por ejecución en `.local/corpus/<asset>/<prepareRunId>/`, con su licencia y manifiesto. El manifiesto de trabajo `prepared.json` apunta a la última preparación; las inferencias anteriores siguen usando sus rutas y hashes originales.

## Recibir assets de creation-lab

El [adaptador](../creation-lab/docs/INTEGRATION.md) recibe un `candidate.json`
cerrado y revisado. La creación y el rigging tienen revisiones distintas: aceptar
el diseño fuente no aprueba los pesos ni las deformaciones del rig generado.
El [informe del adaptador](reports/CREATION-ADAPTER.md) conserva la prueba completa
con UniRig, las dimensiones restauradas y la evidencia visual.

```bash
python3 lab/lab.py ingest --candidate creation-lab/.local/runs/<handoff>/candidate.json
# Usar la ruta preparedManifest que imprime el comando anterior:
python3 lab/lab.py rig --candidate lab/.local/runs/<ingest>/creation-prepared.json --stage all
```

En Windows usar `.\lab\lab.cmd` con los mismos argumentos y rutas WSL.
El receptor verifica hashes y revisiones, copia la evidencia y prepara la
geometría estática en un run nuevo. Registra la matriz de normalización a 2 m
de dimensión mayor y su inversa. Tras UniRig, `restored/restored.glb` recupera
el espacio original, conservando los materiales y los pesos; su validación
incluye exportación y reimportación. Los originales `.blend` y GLB, la licencia
y la procedencia se conservan en la entrega copiada.

`rig --candidate` es alternativo a `rig --asset`. No añade IDs a `corpus.json`,
no sustituye preparaciones humano/cuadrúpedo ni actualiza sus informes o el
inventario de galería. Comparte el lock y los checkpoints de UniRig. Las entradas
de creación con rig, clips o morph targets quedan fuera del contrato estático.
Para revisar deformaciones de un candidato nuevo hace falta su mapa anatómico;
las correspondencias del corpus existente no se aplican automáticamente.
