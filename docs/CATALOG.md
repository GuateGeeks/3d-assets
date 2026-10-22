# Biblioteca 3D de GuateGeeks · Poly Pizza

Biblioteca compartida para **GuateGeeks Code Studio** y **Sócrates**, descargada el **22 de octubre de 2026** mediante la API oficial Poly Pizza v1.1 y el skill solicitado. Los archivos viven aquí para evitar duplicarlos entre aplicaciones. Esta entrega prepara los recursos y su inventario; la importación en las aplicaciones y la publicación se realizan por separado.

Comenzar por [INDEX.md](../INDEX.md), [index.csv](../index.csv) o [index.json](../index.json). Los índices JSON secundarios contienen IDs que se resuelven en `index.json`; las rutas de archivos siempre son relativas a esta carpeta.

## Contenido

- `models/<ID>/model.glb`: archivo original, sin conversión, con materiales y dependencias incorporados cuando corresponden.
- `models/<ID>/source.json`: respuesta original de la API para auditar autoría, licencia y atribución.
- `models/<ID>/metadata.json`: ficha normalizada con asociaciones temáticas, SHA-256, licencia y características GLB inspeccionadas.
- `models/<ID>/LICENSE.txt`: licencia, enlace, atribución original, procedencia y declaración de cambios.
- [ATTRIBUTIONS.md](../ATTRIBUTIONS.md): créditos completos por modelo.
- `indices/areas/`: 23 temas para ciencias, matemática, lenguaje, ciudadanía, arte, educación física, productividad y creación STEAM.
- `indices/subjects/`: diez áreas educativas de referencia; L1/L2/L3 agrupan las tres áreas de Comunicación y Lenguaje.
- `indices/products/`: bibliotecas candidatas para Code Studio y Sócrates; no constituyen paquetes ya integrados.
- `indices/licenses/`: agrupación por licencia exacta.
- `indices/animation/`: modelos con esqueleto, con clips y estáticos; un modelo animado puede usar transformaciones sin esqueleto.
- [COVERAGE.md](../COVERAGE.md): coincidencias semánticas y necesidades que requieren revisión; incluye el contexto guatemalteco.
- [audit.json](../audit.json): comprobaciones cruzadas de archivos, índices, CSV, créditos y fuentes.
- `indices/categories/`: categorías originales de Poly Pizza.
- `indices/review/`: recursos señalados para evaluación e inconsistencias entre la API y el GLB.
- [selection.json](../selection.json): términos, asociaciones e ideas de actividad utilizadas para seleccionar recursos.
- `sources/search/`: respuestas de búsqueda, para reproducir y auditar la selección sin consumir la API.
- [download-issues.json](../download-issues.json): búsquedas vacías, errores o modelos que no pudieron guardarse completos.
- [validation.json](../validation.json): conteos y verificación de integridad.

## Licencias e inspección de uso

La selección **no filtra por licencia**. Se conserva `licenseRaw` exactamente como lo devuelve cada ficha y se normaliza por separado en `license`. El skill menciona CC0 y CC BY 4.0 como ejemplos; eso no sustituye la licencia real. La descarga encontró también CC BY 3.0.

`attribution` conserva la cadena original de la API. `modifications` registra que el GLB permanece sin cambios. `attributionRequired`, `commercialUse`, `derivatives` y `shareAlike` son indicadores preliminares derivados de la licencia identificada. `null` significa que la licencia no pudo interpretarse. **Todos los registros tienen `reviewStatus: pending`**: los indicadores no equivalen a aprobación de distribución ni resuelven derechos de marcas, personas u otros materiales incorporados. `reviewFlags` señala componentes de terceros mencionados, marcas, fantasía/combate y revisión anatómica o cultural. La presencia o ausencia de estas señales no acredita derechos ni pertinencia educativa. El propio modelo puede mencionar componentes externos en `description`; conservar esos avisos al evaluar su uso.

Para CC BY, la atribución debe acompañar al recurso en el producto que lo utilice, con su enlace de licencia y los cambios que se hagan. CC0 no exige atribución de copyright; se conserva de todos modos la procedencia. Las capturas de [CC BY 3.0](../sources/cc-by-3.0.html), [CC0 1.0](../sources/cc0-1.0.html), [términos del servicio](../sources/terms.html) y [documentación API](../sources/api-v1.1.html) permiten revisar las fuentes. Para términos vigentes, consultar los enlaces originales en el manifiesto de fuentes.

## Alcance educativo

La selección organiza recursos candidatos para las áreas del CNB y la creación STEAM en Code Studio y Sócrates.

Las asociaciones de `areas`, `subjects`, `products` y las propuestas de actividad son sugerencias de organización. No acreditan competencias, indicadores ni cobertura completa del CNB. Los modelos low poly permiten crear escenas y actividades; su precisión anatómica, científica, histórica, cultural y de escala debe evaluarse según la lección. Una pirámide genérica no se presenta automáticamente como patrimonio maya ni un reloj genérico como representación validada del Cholq'ij. Los modelos de electrónica o robots son elementos visuales; no sustituyen las piezas reales de Arduino, SMARS, micro:bit o LEGO.

La selección inicial usa hasta tres resultados relevantes por consulta. Prefiere coincidencias en el título y, cuando no hay coincidencias, toma un resultado semántico de la API. No constituye una copia completa del catálogo. Los resultados de cada consulta, incluidos los no descargados, quedan en `sources/search/`.

## Verificación y mantenimiento

Se comprueban SHA-256, tamaño, cabecera GLB v2, límites/alineación de chunks, JSON, presencia de geometría y ausencia de dependencias externas sin descargar. `gltf.skins`, `gltf.joints`, `gltf.animations` y `gltf.animationNames` se leen del archivo real; `apiAnimated` conserva la declaración de Poly Pizza por separado. Esta verificación no acredita renderizado, accesibilidad, rendimiento en equipos escolares ni exactitud educativa.

Con Python 3.10 o posterior, sin dependencias adicionales:

```sh
python tools/catalog.py verify
```

El comando verifica todos los archivos y regenera los índices sin conexión. Para reanudar o ampliar la descarga, editar `selection.json`, proporcionar `POLY_PIZZA_KEY` en el entorno del proceso y ejecutar:

```sh
python tools/catalog.py download
```

La herramienta reutiliza búsquedas, fichas y modelos ya descargados; no actualiza silenciosamente sus licencias. Para actualizar una búsqueda o ficha, respaldar y retirar explícitamente su caché antes de repetir la descarga. La clave solo se utiliza en la cabecera enviada a `api.poly.pizza`; no se guarda en esta biblioteca ni se envía al CDN. Las consultas son secuenciales y los errores 429/5xx se reintentan con espera.

El código de la herramienta y los índices son trabajo de organización de GuateGeeks. Los modelos **conservan sus licencias individuales**; no se les asigna una licencia global por pertenecer a esta carpeta.
