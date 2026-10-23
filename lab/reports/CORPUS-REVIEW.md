# Corpus humano/cuadrúpedo: inferencia y revisión de deformaciones

Fecha: 22 de octubre de 2026. Este corte está implementado en `3d-assets`; todavía no se han creado clips ni promovido derivados a una biblioteca aprobada.

## Resultado

UniRig completó esqueleto, skinning del esqueleto generado, fusión con materiales y reapertura del GLB en ambos modelos. Los 342 originales mantienen sus hashes. La galería local compara el control original, la entrada sin rig y el candidato; ofrece cámaras vinculadas, cinco poses estáticas por modelo, esqueletos, métricas y exportación de notas. Se abre con `python3 tools/serve_gallery.py --lab --port 4390`.

| Modelo del corpus | Run | Tiempo completo | Huesos UniRig | Vértices con pesos | Sin peso / sin normalizar | Pico muestreado GPU |
| --- | --- | --- | --- | --- | --- | --- |
| Humano · Man | `20261022T213527Z-159dbb54` | 228.897 s | 29 | 4019 | 0 / 0 | 7530 MiB |
| Cuadrúpedo · Wolf | `20261022T213933Z-02f44d2c` | 160.762 s | 38 | 4037 | 0 / 0 | 7440 MiB |

Los tiempos incluyen verificación de checkpoints, extracción, inferencias, fusión y validación. Son dos ejecuciones observadas, no un benchmark repetido ni una promesa de latencia. La memoria corresponde al dispositivo completo, incluido el escritorio y otras aplicaciones, con muestreo aproximado cada segundo.

## Preparación y procedencia

Se eligieron Man (`HMnuH5geEG`) y Wolf (`P1gU3Qkr9r`), de Quaternius, CC0. El perro (`24WsfFi7Q8s`) está sentado: se conserva para un caso difícil posterior. Wolf ofrece cuatro extremidades separadas para este primer control de cuadrúpedo. La copia de inferencia está en reposo sin rig ni animaciones; un segundo GLB conserva el rig original como control, sin sus clips. Se normaliza uniformemente a dos metros de dimensión mayor, centro XY y suelo Z=0. No se diezma ni remalla; se conservan materiales.

La preparación mide 3967 vértices/1851 triángulos para Man y 3994/1962 para Wolf. Los contadores del API original no se usan como verdad geométrica. Los vértices importados de los GLB candidatos incluyen splits de atributos; no deben interpretarse como remallado. El inspector Blender también cuenta su Icosphere auxiliar de 42 vértices, que no pertenece al GLB exportado. El número de vértices con pesos excluye ese auxiliar.

Los manifiestos `rig-human.json` y `rig-quadruped.json` conservan hashes, licencias, normalización y procedencia. `skinningInput` coincide con el SHA-256 del esqueleto generado del mismo run. A diferencia del ejemplo oficial de instalación, aquí no se emplea un esqueleto corregido por upstream. La revisión intermedia manual del esqueleto sigue pendiente; los rigs completos son candidatos automáticos.

## Hallazgos antes de clips

El humano necesita revisar pesos en rodilla izquierda y codos. En el cuadrúpedo, la inspección inicial conserva la silueta general en patas, cuello y cola, con dictamen final todavía pendiente. Ninguno está aprobado para un paquete final.

| Modelo | Pose | Estiramiento máximo control | Estiramiento máximo UniRig |
| --- | --- | --- | --- |
| Humano · Man | Codos · 60° | 1.46× | 2.85× |
| Humano · Man | Hombros · 35° | 1.23× | 1.49× |
| Humano · Man | Rodilla izquierda · 45° | 1.14× | 3.90× |
| Humano · Man | Cuello · 20° | 1.15× | 1.45× |
| Cuadrúpedo · Wolf | Codos delanteros · 40° | 1.54× | 1.49× |
| Cuadrúpedo · Wolf | Rodilla trasera izquierda · 35° | 1.26× | 1.28× |
| Cuadrúpedo · Wolf | Cuello · 20° | 1.32× | 1.42× |
| Cuadrúpedo · Wolf | Cola · 25° | 1.44× | 1.59× |

Se comparan aristas de más de 2 mm en las mallas normalizadas, antes/después de la pose. Los mapas anatómicos, grados y ejes están en `lab/review-poses.json`, ligados al hash de cada candidato. Los controles de pie independientes del rig original acompañan el giro alrededor del pivote de rodilla/codo: omitirlos generaba estiramientos artificiales. Esta corrección pertenece al diagnóstico; no se modificó el original ni se ejecutó un solver IK. Los pivotes de los rigs siguen siendo aproximaciones anatómicas distintas.

El mínimo de razón de arista de UniRig en la rodilla humana es 0,13×: junto al máximo 3,90× justifica inspeccionar y corregir pesos antes de crear clips. El máximo no es una calificación global: no mide penetraciones, contacto con suelo ni volumen. Los hallazgos ligados al SHA-256 están en `lab/review-findings.json` y se muestran en la galería.

## Galería y verificación

Se hornearon 40 GLB estáticos (2 modelos × 5 poses × 2 rigs × vistas opaca/esqueleto). El inventario local añade 2 entradas sin rig y 2 candidatos completos: 44 GLB, sin animaciones. Los candidatos originales permanecen en sus runs. Cada regeneración tiene un run propio y conserva sus vistas, manifiesto y diagnósticos sin sobrescribir la revisión anterior. Las notas se vinculan al run de inferencia y al de revisión. El inventario se entrega mediante tokens y verifica hashes; no expone paths de instalación, pesos ni cachés. GET y HEAD bloquean rutas privadas y aliases por symlink. No hay endpoints de escritura. Las notas se guardan en el navegador y se exportan a JSON, sin aprobar automáticamente un candidato.

El validador Khronos `2.0.0-dev.3.10` devuelve 0 errores y 2 advertencias `NODE_SKINNED_MESH_NON_ROOT`, una por candidato completo. Las 40 poses y las dos entradas sin rig no presentan esa advertencia. La jerarquía de los candidatos se conserva como salida cruda de UniRig y requiere normalización al preparar un derivado aprobado. La validez de formato no aprueba su deformación.

La revisión visual se realizó en navegador con escritorio y móvil a 390×844: modelos completos, controles, esqueletos, cámaras sincronizadas por teclado, persistencia de notas y exportación con hashes verificados. El catálogo original sigue mostrando 342 modelos; Man conserva sus 11 clips. Último run de revisión: `20261022T220402Z-eab41af6`. Capturas locales y hashes en `lab/.local/qa/`; registro en `corpus-ui-qa.json`. El detector de diseño solo señaló Inter, tipografía heredada que se conserva según `gallery/DESIGN.md`.

Se corrigió un error de consola del visor al compilar su WebAssembly añadiendo únicamente `wasm-unsafe-eval` a CSP; se conserva el bloqueo de eval de JavaScript y de scripts externos. La diferencia está documentada por [MDN, script-src](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/script-src). No se observaron errores nuevos de consola tras la corrección.

Pruebas: 10 comprobaciones automáticas de locks, fallos, timeouts, publicación, aislamiento HTTP, UTF-8, hashes y ausencia de clips. `corpus-tests.json`, `corpus-gltf-validation.json`, `corpus-build.json` y `corpus-library-validation.json` conservan resultados. El build estático excluye `lab/`, los runs y las vistas experimentales. No se publicó ni desplegó el sitio.

## Siguiente trabajo

Corregir y volver a medir los pesos de rodilla/codos del humano; revisar pivotes, simetría, contactos y volúmenes de ambos candidatos en Blender y galería. Incorporar un dictamen explícito ligado a los hashes y después preparar los primeros clips. SkinTokens, empaquetado y aplicaciones consumidoras permanecen en fases posteriores.
