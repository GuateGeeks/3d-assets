# Preparar un clon de 3d-assets

Clonar el repositorio completo y ejecutar los comandos desde su raíz:

```sh
git clone https://github.com/GuateGeeks/3d-assets.git
cd 3d-assets
python tools/serve_gallery.py --port 4376
```

Usar `python3` si ese es el nombre de Python en el sistema. La galería necesita
Python >=3.10 y un navegador con WebGL. Incluye modelos, miniaturas, visor,
fuentes, kits, licencias y scripts; no requiere npm, claves ni runtime de IA.
Abrir http://127.0.0.1:4376/gallery.html. Para construir y comprobar:

```sh
python tools/build_site.py
python tools/check_site.py
python creation-lab/registry/verify_sources.py
python tools/check_skills.py
python -m unittest discover -s creation-lab/tests -v
python -m unittest discover -s lab/tests -v
```

Las pruebas Blender/CUDA que requieren una instalación real se omiten cuando
falta su entorno; una omisión no significa que hayan pasado. Node es opcional
para `node --check gallery/app.js` y `node --check gallery/lab.js`.

## Creación

La CLI usa stdlib. Instalar Blender por separado y comprobar su ruta:

```sh
python creation-lab/create.py doctor --blender "/ruta/absoluta/a/blender"
python creation-lab/create.py canary --brief creation-lab/examples/canary.json --blender "/ruta/absoluta/a/blender"
```

En Windows, reemplazar la ruta por la de `blender.exe`. La versión observada es
5.2.3 LTS; el puente MCP opcional requiere >=5.1. Consultar
[START-HERE](creation-lab/START-HERE.md) y el [manual](creation-lab/README.md)
para revisar imágenes, cerrar evidencia y entregar un candidato. El canario
comprueba infraestructura; no genera personajes arbitrarios desde texto.

## Benchmark educativo incluido

El piloto de célula animal conserva diez ejecuciones de seis condiciones en
archivos ZIP versionados, con hashes, fuentes Blender, GLB, renders y fallos.
Se pueden restaurar y abrir sin Blender, GPU, npm ni una cuenta de IA:

```sh
python creation-lab/benchmarks/animal-cell-20261022/restore.py
python creation-lab/benchmarks/animal-cell-20261022/serve.py --port 4393
```

Abrir http://127.0.0.1:4393. La restauración coloca la evidencia bajo `.local/`
y comprueba su integridad. Las seis propuestas no están todas aprobadas para
clase: consultar [resultados y alcance](creation-lab/benchmarks/animal-cell-20261022/RESULTS.md).
El [manual del benchmark](creation-lab/benchmarks/animal-cell-20261022/README.md)
explica cómo ejecutar otras condiciones con Blender, instalar el validador
opcional fijado por npm y guardar nuevos informes sin sobrescribir los históricos.

## UniRig y comparación de deformaciones

Se requiere Ubuntu/WSL Linux x86_64, Git, conexión durante setup y una GPU NVIDIA
con driver compatible. El perfil probado usa RTX 3060 Ti de 8 GB y CUDA 12.4;
consultar [diagnóstico y restricciones](lab/reports/UNIRIG-SETUP.md).
Desde Linux/WSL:

```sh
python3 lab/lab.py doctor
python3 lab/lab.py setup --engine unirig
python3 lab/lab.py verify --engine unirig
python3 lab/lab.py smoke --stage all
python3 lab/lab.py prepare --asset all
python3 lab/lab.py rig --asset human
python3 lab/lab.py rig --asset quadruped
python3 lab/lab.py review --asset all
python3 tools/serve_gallery.py --lab --port 4390
```

Desde Windows usar `lab\lab.cmd` en lugar de `python3 lab/lab.py` para ejecutar
en WSL. Abrir http://127.0.0.1:4390/gallery.html?lab=1. Setup restaura el commit,
Python, paquetes y checkpoints fijados en `lab/envs/`, bajo `lab/.local/`;
no instala drivers. Los pesos se descargan desde sus fuentes verificadas y
conservan sus condiciones de uso. Ejecutar una inferencia a la vez.

El [estado](lab/STATUS.md) distingue resultados históricos de trabajo pendiente.
Un clon nuevo debe generar sus propios runs y ajustar el mapa de poses a los
hashes producidos, según [lab/README.md](lab/README.md). Los grandes entornos,
pesos, cachés y candidatos experimentales locales no se versionan; el benchmark
educativo tiene su propio paquete de evidencia explícito, descrito arriba.
SkinTokens todavía no tiene una instalación local validada ni un instalador;
su evaluación sigue pendiente en el [plan](docs/RIGGING-LAB-PLAN.md).

## Puente Blender para el cotizador

El puente está integrado en `procedural-web/`. Requiere un checkout compatible del
cotizador con `asesor/lab/campus-people.js`, los módulos
`asesor/lab/paper/meshy/primaria-meshy*-data.js`, sus dependencias de Node y Blender
(o un Python con `bpy`). Opera desde WSL/Linux; para Blender de Windows usa la
ruta `/mnt/.../blender.exe`. No instala ni modifica esos entornos.

```sh
mkdir -p procedural-web/.local
cp procedural-web/config.example.json procedural-web/.local/config.json
# Ajustar cotizador, blender, bpy y node a las rutas de este equipo.
python3 procedural-web/pw.py doctor
python3 procedural-web/pw.py export --model nino
python3 procedural-web/pw.py import --model nino --blend /ruta/al/nino.blend
python3 -m unittest discover -s procedural-web/tests -v
```

Las opciones globales, como `--cotizador` o `--engine bpy`, van antes de
`doctor`, `export`, `import` o `adopt`. `import` y `adopt` solo escriben en el
cotizador con `--apply`; una revisión sin esa opción sigue creando su recibo local.
Consulta el [contrato completo](procedural-web/README.md). Exporta, edita e importa
con la misma versión de Blender; `bpy` 4.2 no abre fuentes guardadas en 5.x.

Para verificar la ida y vuelta de ambos personajes y sus articulaciones:

```sh
GG_TEST_BPY=/ruta/al/python-con-bpy GG_COTIZADOR=/ruta/al/cotizador GG_NODE=/ruta/a/node python3 -m unittest discover -s procedural-web/tests -v
```

Sin esas variables se omite la prueba de integración. La configuración y los runs
permanecen ignorados en `procedural-web/.local/`; no forman parte de un clon ni del
sitio público. Los recibos históricos conservan sus rutas originales. El puente de
personajes es independiente del puente MCP opcional descrito a continuación.

## Skills y puente MCP opcional

Abrir el proyecto en la raíz `3d-assets` y leer [AGENTS.md](AGENTS.md).
Los skills y sus referencias están en `.agents/skills/`; `tools/check_skills.py`
comprueba el inventario actual y sus enlaces. No requieren
copiar instrucciones desde otro equipo. Las recetas vendorizadas conservan
commits, hashes, licencias y adaptadores. Su presencia no prueba ejecución.

El puente oficial Blender MCP puede restaurarse con **Python CPython 3.12 x64
de Windows**, pip y acceso a PyPI. El lock actual contiene wheels de ese perfil;
no usarlo como lock de Linux/macOS. La CLI de creación funciona sin MCP.

```powershell
py -3.12 creation-lab/registry/verify_sources.py
py -3.12 creation-lab/registry/restore_mcp_runtime.py
py -3.12 creation-lab/registry/probe_project_launcher.py --blender 'C:\Ruta\Blender\blender.exe'
```

El restaurador instala con hashes en `creation-lab/vendor/.runtime/`, copia el
servidor oficial y prueba imports antes de publicar el directorio. No reemplaza
un runtime existente. `--target <directorio-nuevo>` permite verificar una
restauración independiente; los launchers usan exclusivamente el destino por
defecto. No modifica Python global ni inicia Blender durante la instalación.
El probe posterior inicia y cierra su propia sesión headless.

Copiar `creation-lab/registry/codex-mcp.example.toml` a `.codex/config.toml`,
ajustar las tres rutas absolutas y habilitarlo solo al usar esa integración.
La configuración de cada equipo queda ignorada por Git. Según la
[documentación oficial de Codex](https://learn.chatgpt.com/docs/extend/mcp),
la configuración de proyecto se carga en proyectos de confianza y admite
servidores stdio con filtros de herramientas. El ejemplo queda deshabilitado;
el puente ejecuta Python en su propia sesión Blender y no es un sandbox.
Los informes históricos de pruebas no prueban disponibilidad MCP en otro chat.

La construcción pública usa una lista explícita de recursos. No publica los
laboratorios, la configuración local, los checkpoints ni sus resultados.
Code Studio y Sócrates siguen fuera de este corte.
# Flujo iterativo de creación

Para nuevas creaciones, consulta [la guía Sol/Luna](creation-lab/docs/ITERATIVE-WORKFLOW.md).
`python creation-lab/iterate.py --help` describe la CLI local, sin APIs de modelos.
La biblioteca [components](creation-lab/components/README.md) incluye un demo
paramétrico; su ejecución requiere Blender y las opciones explícitas de la guía.
Los tests de contratos/geometría se ejecutan con el mismo comando de creación:
`python -m unittest discover -s creation-lab/tests -v`. Los probes Blender son
opt-in mediante `CREATION_TEST_BLENDER` apuntando a su ejecutable.

## Studio: código interactivo, proveedores y escenas

Seguir [studio/README.md](studio/README.md) para instalar las dependencias Node fijadas,
construir el visor local e iniciar un proyecto. Python >=3.10 y Node >=22.12;
CI utiliza Node 24. La galería original sigue sin requerir npm para su uso.

Configurar los ejecutables opcionales en un JSON local y pasarlo con `--config`
antes del subcomando. Studio no instala Blender, UniRig ni pesos automáticamente,
y no activa pagos. SkinTokens necesita un executor elegible separado del equipo
local de 8 GiB. No sustituir el Python de UniRig por el del frontend.

`python -m unittest discover -s studio/tests -v` verifica contratos y fixtures sin
pagos/GPU. El fixture real de Blender es opt-in mediante `STUDIO_BPY_PYTHON`.
Los tests Chromium verifican interacción con renderizado software; las medidas
hardware y las inferencias reales tienen sus propios recibos. Revisar
[studio/docs/STATUS.md](studio/docs/STATUS.md) antes de reutilizar evidencia histórica.