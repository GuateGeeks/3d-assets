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
pesos, cachés, renders y candidatos experimentales locales no se versionan.
SkinTokens todavía no tiene una instalación local validada ni un instalador;
su evaluación sigue pendiente en el [plan](docs/RIGGING-LAB-PLAN.md).

## Skills y puente MCP opcional

Abrir el proyecto en la raíz `3d-assets` y leer [AGENTS.md](AGENTS.md).
Los diez skills y sus referencias están en `.agents/skills/`; no requieren
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
