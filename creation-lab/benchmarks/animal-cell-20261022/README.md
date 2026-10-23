# Célula animal · benchmark piloto

Seis propuestas originales para secundaria, con trece partes y explicaciones en
español. Cada autor generó código procedural de Blender a partir del mismo
[brief](brief.json) y [contrato](AUTHORING.md). Los archivos editables, GLB,
renders y recibos de los diez runs se distribuyen en `fixtures/` y se restauran
en `creation-lab/.local/benchmarks/animal-cell-20261022/`. Los informes de esta
carpeta describen el piloto original; ejecutar un script no renueva esa revisión.

## Explorar y usar

Desde la raíz de `3d-assets`, con Python 3.10 o posterior:

```powershell
python creation-lab/benchmarks/animal-cell-20261022/restore.py --check
python creation-lab/benchmarks/animal-cell-20261022/restore.py
python creation-lab/benchmarks/animal-cell-20261022/serve.py --port 4393
```

La restauración usa los ZIP versionados y sus hashes; no requiere Blender,
Node, servicios de IA ni descargas. El visor utiliza el bundle de model-viewer
y las fuentes de `gallery/vendor/`. Se sirve sólo en loopback. `--runs RUTA`
permite explorar una restauración alternativa. Sólo selecciona runs completos
con un marcador `COMPLETE` válido; una ejecución en curso no reemplaza la vista.
Son aproximadamente 65 MB comprimidos y 415 MB restaurados. La restauración
es idempotente para archivos idénticos y rechaza diferencias sin sobrescribir.
`COMPLETE` cierra la evidencia de una ejecución, también cuando su QA falla.
Las rutas de host dentro de manifiestos/logs son procedencia histórica, no
instrucciones para configurar otro equipo.

Abrir <http://127.0.0.1:4393>. El visor permite comparar propuestas, girar el
modelo, seleccionar las partes y descargar el GLB o el archivo de Blender.
Las etiquetas son interactivas; `parts.json` conserva las posiciones, nombres,
funciones y correspondencia con los objetos editables. El GLB también conserva
`part_id` en los extras de cada objeto.

La maqueta mide aproximadamente 30 cm. Los colores, cantidades y proporciones
son convenciones didácticas; no representan una micrografía ni una escala
microscópica exacta. Es una selección de estructuras de una célula animal
generalizada en interfase. Algunas células especializadas difieren de este
esquema y no se representa todo el inventario celular.

## Diseño de la comparación

| Variante | Modelo autor | Esfuerzo solicitado |
| --- | --- | --- |
| A | gpt-6.1-sol | high |
| B | gpt-6-luna | medium |
| C | gpt-6-astra | high |
| D | gpt-6.1-sol | medium |
| E | gpt-6-luna | high |
| F | gpt-6-astra | medium |

El [protocolo](protocol.json) fija semilla, presupuesto de geometría, cámara,
iluminación, Blender 5.2.3 LTS y render CPU. Los autores trabajaron en contextos
independientes; las asignaciones constan en [el recibo](authoring-receipt.json).
Hay una sola propuesta por condición: esto permite comparar estos seis
artefactos, no demostrar superioridad estadística de un modelo ni completar
el benchmark M7 de seis briefs distintos.

El tiempo registrado corresponde al proceso local de construir, reabrir,
renderizar y reimportar, con sus verificaciones. No mide latencia pura del
modelo. No se dispone de telemetría de tokens ni de costos. No se ejecutaron
proveedores externos de texto a 3D ni APIs de imágenes.

Una condición puede fallar visualmente aunque contenga trece identificadores
y pase las comprobaciones técnicas. Los defectos y las primeras ejecuciones
se conservan; el protocolo permite como máximo una reparación técnica por autor.

## Reproducir una condición

```powershell
python creation-lab/benchmarks/animal-cell-20261022/run.py A --blender '/ruta/absoluta/a/blender'
```

En Windows usa la ruta absoluta de `blender.exe`. El ejecutable debe existir
y se comprueba antes de crear un run. Blender 5.2.3 LTS es la versión usada en
el piloto; una versión distinta debe registrarse y evaluarse por separado.
`run.py` ejecuta el código final guardado en `conditions/A/generator.py`;
no vuelve a llamar al modelo autor. Los códigos iniciales están en sus runs
restaurados. La comprobación AST de imports/E/S es una revisión de higiene,
no un sandbox: sólo ejecutar generadores revisados y de procedencia conocida.

Cada ejecución crea una carpeta nueva con código, versiones, comandos, tiempos
y hashes. `COMPLETE` contiene el hash del manifiesto. Los artefactos existentes
no se sobrescriben. La comprobación adicional de formato requiere Node.js y
npm. Instalar la dependencia opcional fijada, localmente, desde la raíz:

```powershell
npm --prefix creation-lab/benchmarks/animal-cell-20261022 ci --ignore-scripts --no-audit --no-fund
node creation-lab/benchmarks/animal-cell-20261022/validate.cjs
```

El lock fija Khronos `gltf-validator` 2.0.0-dev.3.10 y su integridad. No depende
del runtime de UniRig. `--validator-module RUTA_ABSOLUTA` permite utilizar una
copia ya instalada. El validador comprueba el manifiesto y el hash del GLB y
falla si no encuentra artefactos: cero archivos no equivale a PASS.

## Evaluar un nuevo run sin cambiar el piloto

`validate.cjs`, `collect.py` y `check_viewer.py` escriben informes nuevos bajo
`.local/.../reports/` e imprimen su destino. Admiten destinos explícitos y
rechazan sobrescribir informes existentes:

```sh
node creation-lab/benchmarks/animal-cell-20261022/validate.cjs --output creation-lab/.local/mi-evaluacion/format-validation.json
python creation-lab/benchmarks/animal-cell-20261022/collect.py --format-report creation-lab/.local/mi-evaluacion/format-validation.json --report-dir creation-lab/.local/mi-evaluacion
python creation-lab/benchmarks/animal-cell-20261022/check_viewer.py --port 4393 --output creation-lab/.local/mi-evaluacion/viewer-http-validation.json
```

Una revisión sólo aplica al `runId` y a los hashes de imágenes que se abrieron.
Un run nuevo queda visual/biológicamente `NOT_RUN` hasta revisarlo; nunca hereda
el 87 de D ni la aprobación de otro run. Para revisiones nuevas,
`collect.py --reviews RUTA` recibe una carpeta de JSON A-F; `serve.py --reviews ARCHIVO`
recibe el `reviews.json` agregado. `--runs RUTA` es común a colección, validador,
visor y empaquetador. Las revisiones históricas no necesitan actualizarse.

Para empaquetar los seis runs seleccionados por el informe original:

```sh
python creation-lab/benchmarks/animal-cell-20261022/package.py
python -m unittest discover -s creation-lab/benchmarks/animal-cell-20261022 -p 'test_*.py' -v
```

El paquete verifica la evidencia antes de copiar. `--results ARCHIVO` permite
usar otro informe de seis condiciones y `--output RUTA_NUEVA` elige el destino.
Sólo incluye como vigentes las revisiones del `reviews.json` vecino que
coincidan con el run y sus hashes. El `LEEME.txt` identifica cada run y remite
a `benchmark/results.json` y `benchmark/reviews.json`. Las calificaciones y
evidencias del piloto se agrupan aparte en `benchmark/history/`.
Los checks HTTP cubren todas las descargas; no sustituyen abrir el visor y
comprobar rotación, etiquetas y encuadre. Los scripts `*_probe.py` y `diagnose.py`
son diagnósticos históricos dirigidos, no pasos necesarios de instalación.

## Relación con 3d-assets

El benchmark vive en `creation-lab`, usa la comprobación de geometría y
materiales del adaptador del laboratorio y conserva escala, ejes y procedencia
en sus recibos. Cada propuesta tiene objetos separados por estructura.
No necesita un esqueleto ni una inferencia de UniRig para su uso educativo.
Estos experimentos no se insertan automáticamente en el catálogo publicable.

## Fuentes educativas

Las funciones del brief son paráfrasis de fuentes abiertas consultadas:
[OpenStax: células eucariotas](https://openstax.org/books/biology-2e/pages/4-3-eukaryotic-cells),
[sistema de endomembranas](https://openstax.org/books/biology-2e/pages/4-4-the-endomembrane-system-and-proteins),
[citoesqueleto](https://openstax.org/books/biology-2e/pages/4-5-the-cytoskeleton),
[MedlinePlus: la célula](https://www.medlineplus.gov/genetics/understanding/basics/cell/)
y [NHGRI: mitocondrias](https://www.genome.gov/genetics-glossary/Mitochondria).

La zona pálida representa citosol; el citoplasma comprende citosol y orgánulos
fuera del núcleo. El núcleo contiene la mayor parte del ADN, no todo. El
nucléolo no tiene una membrana propia y las mitocondrias transforman energía
química para producir ATP. Estas distinciones deben conservarse al adaptar
las etiquetas para clase.

Geometría procedural original, sin modelos ni imágenes externos. La declaración
de procedencia y licencia CC0-1.0 se conserva en el brief y cada run.
