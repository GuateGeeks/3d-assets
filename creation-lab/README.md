# GuateGeeks Creation Lab

Flujo aditivo para crear recursos originales con evidencia local. No modifica originales, catálogo, galería ni el laboratorio UniRig. La CLI usa exclusivamente Python stdlib; Blender es un proceso externo opcional. Cada comando crea un directorio nuevo en `.local/runs/` (o `--runs-root`), con hashes y un marcador `COMPLETE`. El canario conserva snapshots exclusivos de la CLI y worker en `code/`, y ejecuta todas las etapas desde ese worker congelado. Los comandos nunca reescriben runs cerrados; alterar un archivo invalida su evidencia. Los runs incompletos no son evidencia válida.

Desde la raíz de `3d-assets`, Python 3.10 o posterior:

```powershell
python creation-lab/create.py doctor --blender 'D:\SteamLibrary\steamapps\common\Blender\blender.exe'
python creation-lab/create.py brief --input creation-lab/examples/canary.json
python creation-lab/create.py canary --brief creation-lab/examples/canary.json --blender 'D:\SteamLibrary\steamapps\common\Blender\blender.exe'
python creation-lab/create.py validate '<run>'
python creation-lab/create.py report '<run>'
python creation-lab/create.py handoff '<run>'
python -m unittest discover -s creation-lab/tests -v
```

`doctor` busca Blender en PATH y, en Windows, ubicaciones comunes de Steam y Blender Foundation. Siempre registra la versión real mediante `bpy`. Una instalación encontrada no garantiza que pueda ejecutarse bajo el sandbox. Se puede elegir explícitamente `--bpy-python /ruta/al/python-con-bpy` en vez de `--blender`; la herramienta no instala ni actualiza ese entorno. No se inicia Blender MCP. La CLI y worker funcionan independientemente de MCP.

Para un backend Linux desde Windows: `creation-lab/create.cmd doctor --bpy-python lab/.local/envs/unirig/bin/python` o `powershell -NoProfile -File creation-lab/launch.ps1 ...`. El launcher usa arrays de argumentos y WSL sin `sh -c`; las rutas de argumentos pertenecen a Linux. Para Blender nativo, ejecutar directamente Python de Windows con `create.py`, sin el launcher WSL. No requiere cambios globales de seguridad o configuración.

El brief JSON v1 define `assetId`, `description`, `dimensionsM` (ancho X, profundidad Y, altura Z), `budgets`, `provider`, `seed` y `provenance`. Su único `profile` implementado es `lowpoly-canary` (por defecto); los briefs de producción highdetail permanecen planificados. El ejemplo mide 0.18 × 0.19 × 0.30 m, tiene presupuesto máximo de 6,000 triángulos evaluados, 2 materiales y texturas de hasta 2,048 px por lado. Se permiten presupuestos inferiores. Texturas ausentes son válidas: este canario usa materiales planos. `provider.mode` acepta `manual` y `configured`; son configuración guardada, sin llamadas API. `credentialEnv` guarda solo el nombre de una variable y rechaza claves o cabeceras. No incluir secretos en descripciones ni notas.

`canary` siempre construye el mismo objeto original sencillo de tres bloques con chaflanes; el brief controla dimensiones y presupuestos, no genera libremente el objeto descrito. `seed` queda registrado para procedencia; este generador determinista no usa aleatoriedad. Este canario verifica infraestructura antes de producir personajes u objetos complejos.

La prueba real usa Cycles CPU, 2 hilos, 8 muestras y cinco PNG de 256 px: frontal, lateral, trasero, tres cuartos y wireframe, más una sexta imagen comparativa del GLB reimportado. Guarda `source.blend`, exporta `asset.glb`, reabre el `.blend` en otro proceso, genera allí las cinco vistas y reimporta GLB en una escena vacía en un tercer proceso. `render-provenance.json` registra la fuente reabierta y su hash. Mide triángulos, materiales utilizados, imágenes, geometría finita, bordes no manifold, transformaciones y límites en metros antes/después. Los bordes se miden también en copia soldada a 1 µm, porque glTF separa vértices en discontinuidades de normales/material; la malla importada permanece intacta. Compara estado inicial tanto con reapertura como con reimportación: geometría mundial cuantizada a 0.01 mm, firma de triángulos orientados con material asociado (rotación cíclica equivalente; inversión distinta) y Base Color/roughness/metallic de materiales a tolerancia 0.0001. Verifica GLB 2.0 autocontenido, PNG y tolerancia dimensional de 1% (mínimo 0.1 mm). El timeout de cada fase es 300 s, configurable con `--timeout`. En fallback wheel bpy, solo se evita el fallo conocido de teardown después de reportar éxito/error y hacer flush; no se ignoran errores de etapa.

`technical`, `visual` y `rights` usan `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN` por separado. El canario puede pasar técnicamente y continuar `BLOCKED` globalmente por revisión visual pendiente. La declaración de origen original y licencia `CC0-1.0` permite el gate de derechos del canario; otra licencia requiere revisión externa y mantiene ese gate `BLOCKED`. No es una revisión legal automática. Código de salida: 0 cuando el comando termina sin fallo técnico (aunque quede visual pendiente), 1 si hay `FAIL`, 2 si hay error de entrada o bloqueo técnico. Leer siempre el manifiesto.

Abrir e inspeccionar **las cinco imágenes fuente y la comparación reimportada** antes de registrar una revisión:

```text
python creation-lab/create.py review <run> --decision PASS --reviewer Nombre --notes "Silueta, vistas y materiales inspeccionados" --opened-images --evidence front=<sha256> --evidence side=<sha256> --evidence back=<sha256> --evidence three-quarter=<sha256> --evidence wireframe=<sha256> --evidence reimport-three-quarter=<sha256>
```

Los hashes están en `manifest.json`. La CLI verifica coincidencia exacta; `--opened-images` es una declaración explícita del revisor, no detección automática de apertura. Nunca convierte existencia de renders en QA visual aprobada. `review`, `validate`, `report` y `handoff` crean un nuevo run enlazado a su padre, y vuelven a comprobar la evidencia original. El handoff debe usar el run de revisión para conservar el veredicto.

`handoff` crea `candidate.json` con GLB y `.blend` hashados, procedencia/licencia, dimensiones, ejes Blender +Z arriba/-Y frente y conversión glTF +Y arriba, métricas y QA. Solo es candidato; no copia ni promueve recursos. El [adaptador de rigging](docs/INTEGRATION.md) recibe esa entrega con `lab/lab.py ingest --candidate`, registra la normalización de la dimensión mayor a 2 m y restaura las coordenadas originales después de UniRig. `eligibleForPromotion` requiere todos los gates PASS; no autoriza ni efectúa publicación. La deformación del rig nuevo requiere su propia revisión.

Los tests stdlib prueban contratos de entrada, rutas con espacios, aislamiento, integridad y errores. No simulan Blender. La evidencia Blender se obtiene ejecutando el canario real y permanece en runs locales ignorados; los reportes/documentación curados deben referenciar sus hashes.
