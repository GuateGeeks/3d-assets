# Dependencias de creación 3D

Revisión del 22 de octubre de 2026. Las fuentes se fijan por commit, licencia y
SHA-256 en [sources.lock.json](../sources.lock.json). La revisión estática cubre
procedencia, límites de ejecución, entradas/salidas y los hallazgos descritos aquí;
no certifica seguridad general ni resultados artísticos de terceros.

| Fuente | Selección | Estado |
| --- | --- | --- |
| [Rivello ai-skills-blender](https://github.com/SamuelAsherRivello/ai-skills-blender/tree/54b4f26b7c0e530b7158244f397b34e6c16d7b76/.codex/skills) | Nueve recetas Codex, MIT | Preparadas; runtime de sus scripts NOT_RUN |
| [LPM](https://github.com/ozanzeng/blender-LPM-skill/tree/687d0a46f1280bc7d11dbf83539840100ec909dc/skills/blender-lpm-skill) | Fuente MIT y adaptador de primitivas/paletas | Preparada; runtime de sus scripts NOT_RUN |
| [Blender Lab MCP 1.0.3](https://projects.blender.org/lab/blender_mcp/releases/tag/v1.0.3) | Puente preferido, GPL-3.0-or-later | Paquetes y prueba aislada PASS; configuración local creada, carga en este chat NOT_RUN |
| [mcp-for-blender](https://github.com/ahujasid/mcp-for-blender/tree/5a3618fccb2d982d0dd61e7a1879912c3100073b) | Alternativa MIT, revisión parcial | No instalado ni activado |
| [Hermes blender-automation](https://github.com/theheavenlyd3mon/hermes-profiles/blob/848635cc85293d0f30027d2f4c261aa095b2d51f/profiles/creative/skills/creative/blender-automation/SKILL.md) | Referencia bibliográfica | Sin redistribución: falta LICENSE raíz; frontmatter declara MIT |

## Recetas y adaptaciones

El helper oficial `skill-installer/scripts/install-skill-from-github.py` preparó
Rivello y LPM con `--method git`, `--ref <commit>` y destino local `vendor/`.
Se evitó el ZIP completo de Rivello, que contiene ejemplos binarios. No se
ejecutaron instaladores ni recetas upstream de esas dos fuentes.

Las entradas descubribles son `blender-codex-recipes` y `blender-lpm-recipes` en
`.agents/skills/`; los originales permanecen en `vendor/`. Los adaptadores delegan
brief, art direction y aceptación a las siete skills `gg3d-*`.

Rivello aporta alcance por colección, modelado por silueta, comparación visual y
exportación con reimportación. Se mantienen estas diferencias locales:

- Su política de preferir MCP no condiciona la CLI headless de GG3D.
- El contrato `documentation/models/` y la paleta fija del greybox pertenecen a
  su repositorio; aquí mandan el brief y el manifiesto de creation-lab.
- `audit_scene.py` cuenta slots de material, no materiales usados; el validador
  GG3D conserva su propio criterio. `verify_outputs.py` comprueba PNG, no estética.
- El helper setup lee TOML del cliente; está preparado para diagnósticos
  solicitados, no se ejecuta como efecto lateral de consultar una receta.

LPM aporta primitivas editables, simetría y paleta compacta. Sus rutas Unity/FBX
requieren adaptación a GLB. Hay limitaciones verificadas en el código fijado:

- `scripts/bl.py` aplica `wait(timeout)` después de consumir stdout hasta EOF:
  no garantiza el timeout durante una ejecución bloqueada. Tampoco establece
  `CREATE_NO_WINDOW`. El workflow utiliza el runner propio.
- `gate_report.py` informa dimensiones con un PASS incondicional y trata el
  exceso de materiales como WARN. No constituye aceptación GG3D.
- `make_turnaround.py` y `multiview_to_mesh.py` pueden leer `FAL_KEY` o claves de
  `~/.claude.json` y enviar imágenes a fal.ai; quedan fuera del flujo preparado.
- `hy3d_local_mv.py` llama `from_pretrained` y puede descargar modelos pesados;
  queda fuera del flujo preparado. No se invocaron APIs pagadas ni modelos.

## Puente oficial preparado

La [página oficial](https://www.blender.org/lab/mcp-server/) enlazó la release
`v1.0.3`; su tag se resolvió al commit
`2cea8d566dde07fbac28a61d698909d69724e853`. Se conservan el add-on ZIP y el paquete
MCPB originales con inventario de entradas y hashes. La licencia declarada tanto
en el manifiesto del add-on como en el del servidor es GPL-3.0-or-later. Se
incluye `vendor/blender-lab-mcp/COPYING.GPL-3.0.txt`; los avisos SPDX originales
permanecen en el código. El archivo MCPB conserva sus referencias y documentación
tal como las distribuye upstream, con las notas de licencia del manual dentro.

El manifiesto requiere Blender >=5.1.0 y el host del servidor Python >=3.10.
Blender nativo observado: `D:\SteamLibrary\steamapps\common\Blender\blender.exe`,
5.2.3 LTS. La versión real, PID y SHA-256 se registran en cada prueba; el build
hash de Blender es un identificador distinto del SHA-256 del ejecutable.

La arquitectura preparada es cliente MCP → stdio → servidor oficial → TCP
loopback → add-on de Blender. No se activa el transporte HTTP: el código de esa
ruta deshabilita protección de DNS rebinding y permite CORS universal. La ruta
`weak_sandbox.py` declara expresamente que no es un aislamiento de seguridad;
el add-on puede ejecutar Python arbitrario. Se limita la prueba a procesos
propios y archivos propios. No se presenta este puente como sandbox.

`registry/probe_official_mcp.py` crea un Blender headless con `--factory-startup`,
`--disable-autoexec`, directorios de preferencias temporales y puerto loopback
efímero. Inicia el servidor stdio con `CREATE_NO_WINDOW`, realiza handshake y
`tools/list`, verifica el PID antes de modificar, crea un cubo de 0.3 m, lo mide,
lo renderiza cuando corresponde al intento, lo elimina y cierra ambos procesos.
Cada intento conserva su informe y logs bajo `registry/mcp-probe-*/`. Un render
headless es evidencia de render; la captura de viewport/editor permanece NOT_RUN.

El primer intento falló por la carga de PyWin32 en instalación `--target`. Se
conservó la evidencia y se corrigió el launcher con `site.addsitedir`, que procesa
el `.pth` local de PyWin32. La instalación de wheels y los hashes exactos del
resolver están en `registry/mcp-runtime-install.json` y
`registry/mcp-runtime.lock.json`. El runtime local se ignora mediante
`vendor/.gitignore`; no se modificó el Python global ni la configuración global.

Las pruebas aisladas no conectan con el editor del usuario ni exponen herramientas
nuevas en este chat. Se registró una única entrada oficial en
`3d-assets/.codex/config.toml`, con `enabled = true` y el lanzador probado
`registry/launch_isolated_mcp.py`. Al cargar ese proyecto, el lanzador administra
su propia sesión Blender headless, preferencias temporales y puerto efímero.
Las herramientas habilitadas son ejecución de código y documentación Python;
las capturas del editor no están habilitadas en esta conexión headless.

El ejemplo `registry/codex-mcp.example.toml` conserva `enabled = false` para
revisión y portabilidad. Contiene marcadores de rutas absolutas para sustituir en cada
equipo. La configuración activa del host queda ignorada por Git; el verificador
comprueba fuentes distribuibles, no esa observación local. Para restaurar los
wheels hashados y repetir el probe, seguir [SETUP.md](../../SETUP.md). La configuración global no cambió. La carga por la
aplicación de esta entrada local permanece NOT_RUN en este turno: abrir la
carpeta `3d-assets` como proyecto y recargar sus herramientas cuando corresponda.
La limpieza está probada con cierre normal de stdin; matar forzosamente el
wrapper en Windows no constituye una prueba de su bloque finally.
La [documentación oficial de Codex](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
describe confianza del proyecto, registro de servidores y filtros de herramientas.
## Alternativas no activadas

La revisión parcial del fallback conserva README, LICENSE, pyproject, servidor,
gestor de add-on y add-on fijados. Incluye ejecución Python, proveedores externos,
descargas y telemetría gobernada por consentimiento. No se auditó exhaustivamente
su grafo de dependencias. No se registrará junto al puente oficial.

Hermes solo se referencia por URL, commit y hash del texto consultado. La
declaración MIT en su frontmatter no se trata como licencia raíz comprobada.
No se copió su skill ni se instaló su profile.

Para revisar integridad local sin red ni Blender:

```powershell
python creation-lab/registry/verify_sources.py
```

Ese comando verifica bytes preparados; no ejecuta skills ni equivale a una prueba
de Blender o de calidad visual.
