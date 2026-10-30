# GuateGeeks · Biblioteca 3D

Galería de **1173 modelos GLB** para Code Studio y Sócrates, organizados en **23 áreas**. Incluye miniaturas locales, vista 3D con cámara y animaciones, búsqueda en español y filtros por área, fuente, kit, licencia y movimiento. Los créditos se consultan en cada ficha.

## Laboratorio local de rigging

El [plan del laboratorio](docs/RIGGING-LAB-PLAN.md) define el flujo completo dentro
de este proyecto: seleccionar modelos, prepararlos, generar rigs con UniRig,
evaluar SkinTokens en el equipo local, corregir, animar, revisar en la galería
y producir paquetes versionados. Reutilizará el catálogo y el visor existentes,
con áreas propias para trabajo experimental y derivados revisados.

El [laboratorio](lab/README.md) aporta instalación aislada de UniRig, comprobación
CUDA, corpus humano/cuadrúpedo con poses comparables y recepción de candidatos
de creación con escala restaurada. El [estado vigente](lab/STATUS.md) y el
[skill de rigging](.agents/skills/gg3d-rigging/SKILL.md) enlazan evidencia y pendientes.
Los resultados de cada comprobación se conservan en `lab/reports/`. La implementación
en Code Studio o Sócrates comenzará después de completar y validar todo el flujo
en `3d-assets`.

## Personajes del campus en Blender

El [puente Blender](procedural-web/README.md) exporta a `.blend` los alumnos del campus del
cotizador (rig rígido de 12 huesos) con sus poses como acciones, y devuelve el retoque a los
módulos de datos del cotizador con procedencia: `python3 procedural-web/pw.py doctor`. Lo
describe el [skill gg3d-blender-web](.agents/skills/gg3d-blender-web/SKILL.md).

**Galería publicada:** [guategeeks.com/3d-assets](https://guategeeks.com/3d-assets/)

El [mapa de componentes y áreas de trabajo](docs/WORKSPACES.md) explica creación, rigging,
puente web y la conservación de experimentos tras la integración del 26 de octubre de 2026.

Para preparar un clon con scripts, skills y dependencias opcionales, seguir
[SETUP.md](SETUP.md). El [laboratorio de creación](creation-lab/START-HERE.md)
y el de rigging se ejecutan dentro de este repositorio.

## Abrir localmente

Requiere Python 3.10 o posterior, sin dependencias de Python ni npm.

```sh
python tools/serve_gallery.py --port 4376
```

Abrir [la galería local](http://127.0.0.1:4376/gallery.html). Se utiliza HTTP local para cargar GLB; abrir el archivo con `file://` no permite todos los recursos del navegador. El visor, la tipografía, las miniaturas y los modelos se guardan en el repositorio y funcionan sin conexión.

## Preparar y comprobar el sitio

```sh
python tools/build_site.py
python tools/check_site.py
```

`_site/` es el resultado para alojamiento estático. Tiene una entrada `index.html`, galería, modelos, índices y páginas de créditos/cobertura. Todas las rutas son relativas, incluyendo el despliegue bajo `/3d-assets/`. No necesita claves ni servicios externos en ejecución.

## Desplegar en GitHub Pages

1. En **Settings → Pages → Build and deployment**, seleccionar **GitHub Actions** como origen.
2. En **Actions → Deploy gallery to GitHub Pages**, ejecutar **Run workflow** sobre `main`.
3. La acción publica el artefacto `_site/` y muestra la URL del despliegue en el entorno `github-pages`.

La galería está publicada en **https://guategeeks.com/3d-assets/**, bajo el dominio existente de GuateGeeks. El repositorio es público y Pages utiliza GitHub Actions. El mismo `_site/` puede alojarse en cualquier servidor estático.

La validación se ejecuta automáticamente en cada push y pull request. El despliegue es manual. Las acciones están fijadas a revisiones concretas y la credencial de despliegue la proporciona `GITHUB_TOKEN` con permisos limitados de Pages/OIDC.

## Licencias e inventario

- **769 modelos CC0 1.0**, **274 CC BY 3.0**, **103 CC BY 4.0**, **10 CC BY-SA 4.0**, **4 CC BY-NC 4.0**, **3 CC BY-NC-SA 4.0** y **10 bajo NASA Media Usage Guidelines**, según [audit.json](audit.json).
- **32 modelos con esqueleto** y **40 con animaciones** comprobadas dentro del GLB.
- [Índice navegable de archivos](INDEX.md), [CSV](index.csv), [créditos](ATTRIBUTIONS.md) y [cobertura pendiente](COVERAGE.md).
- `models/<ID>/`: GLB original, metadatos del catálogo, ficha normalizada y licencia.
- [LICENSE.md](LICENSE.md): alcance de licencias de los modelos, la interfaz y los componentes.

Los estados de revisión y las observaciones sobre precisión científica, identificación cultural o animaciones de terceros se conservan en las fichas. La asociación a un área es una propuesta para revisión docente, no una acreditación curricular.

## Ampliación Kenney y OpenGameArt

Se incorporaron **651 modelos de seis kits completos**: Kenney Nature Kit (329), Food Kit (200), Modular Buildings (108), OpenGameArt Gear Pack (8), Animated LowPoly Robot (1) y Animated Animales Low Poly (5). Esta ampliación llevó el catálogo de 342 a 993 fichas. Los ZIP completos conservan los formatos alternativos, las versiones y las licencias suministradas por sus autores.

La galería ofrece **Agrupar variantes** y **Cada modelo**. Cada familia permite cambiar de variante desde su ficha; las coincidencias conocidas con el catálogo inicial se reúnen sin modificar sus originales. Agrupar una familia no afirma que sus piezas sean duplicados exactos. Los duplicados binarios compartirían ficha; no se encontraron entre las incorporaciones preparadas.

Ver [kits e inventarios](kits/index.json), [familias y coincidencias](kits/groups.json), [informe completo](enrichment/reports/complete-kits.json) y [comparación con el catálogo inicial](enrichment/reports/DUPLICATES-REVIEW.md). En el sitio publicado, [kits.html](https://guategeeks.com/3d-assets/kits.html) permite descargar los seis ZIP completos. Los índices JSON/CSV incluyen licencia, atribución, kit, grupo y cambios de preparación.

Los GLB nativos de Kenney conservan su geometría; cuando era necesario se incrustaron las imágenes originales. Los seis personajes animados se convirtieron desde BLEND, adaptando materiales antiguos a PBR y comprobando dimensiones y reimportación. Los originales se conservan para comparar fidelidad. Las miniaturas y hojas de contacto fueron inspeccionadas; la adecuación curricular sigue pendiente. La hormiga del piloto quedó excluida porque no superó las comprobaciones de conversión.

## Ampliación Poly Haven

Se incorporaron **28 modelos CC0** de laboratorio, óptica, electrónica, medición, accesibilidad, seguridad, jardinería, oficios y música. Los originales glTF de 1K y sus texturas se conservan por modelo; el GLB incrusta esos componentes sin decimar, reescalar ni modificar materiales, UV o rigs. El tornillo de banco conserva su rig mecánico. Este corte histórico llevó el catálogo a **1021 modelos**; el desglose vigente de todas las fuentes está en [Licencias e inventario](#licencias-e-inventario) y [audit.json](audit.json).

La adquisición usa la API oficial con identificador de aplicación, caché, comprobación MD5/SHA-256 y reintentos limitados. La galería funciona con archivos locales; no consulta la API ni utiliza sus imágenes de muestra. Los créditos preservan los autores individuales aunque CC0 no exija atribución.

[Selección](enrichment/polyhaven-selection.json), [informe](enrichment/reports/polyhaven-20261022.json), [comparación de duplicados y variantes](enrichment/reports/POLYHAVEN-DUPLICATES.md) y [familias](groups/polyhaven.json). No se encontraron coincidencias binarias ni geométricas con los 993 anteriores. Las familias funcionales permiten comparar microscopios, portátiles y llaves con versiones existentes sin afirmar que sean copias idénticas. La revisión curricular permanece pendiente.

El 30 de octubre de 2026 se añadieron **21 modelos y kits completos CC0** de tuberías y válvulas, conductos de ventilación, cables y tableros eléctricos, generador, cilindros de gas, envases químicos y herramientas. Poly Haven suma **49 fichas** y el catálogo completo **1173**. Se conservaron los 6533 archivos originales anteriores y se revisaron seis vistas por incorporación. Los kits mantienen todas sus piezas en el conjunto original; la descarga fuente permite reutilizarlas. [Selección](enrichment/polyhaven-science-selection-20261030.json) · [informe y lista](docs/POLYHAVEN-SCIENCE-20261030.md).

## Actualizar el catálogo

`tools/reindex.py` regenera todos los índices sin reescribir modelos ni sus metadatos. `tools/audit.py` comprueba la consistencia. `tools/catalog.py` permite verificar los modelos o ampliar la selección de `selection.json`. Para descargar se proporciona `POLY_PIZZA_KEY` solo en el entorno del proceso. `tools/setup_gallery.py` recupera las dependencias fijadas y las miniaturas nuevas. La publicación utiliza los archivos ya guardados; no consulta la API de Poly Pizza.

```sh
python tools/catalog.py verify
python tools/setup_gallery.py
python tools/build_site.py
python tools/check_site.py
```

El historial completo de fuentes públicas de búsqueda se conserva en `sources/search/`. El proceso de publicación copia un inventario explícito de archivos y excluye contexto de conversaciones, credenciales y directorios de trabajo.

## Revisar el laboratorio de rigging

El [laboratorio local](lab/README.md) ya prepara un humano y un cuadrúpedo del corpus y ejecuta UniRig sobre copias sin rig. La galería permite comparar controles y candidatos, poses estáticas y esqueletos antes de crear clips:

```sh
python tools/serve_gallery.py --lab --port 4390
```

Abrir `http://127.0.0.1:4390/gallery.html?lab=1` después de generar las vistas con los comandos del manual. El [informe del corpus](lab/reports/CORPUS-REVIEW.md) identifica los ajustes pendientes. Los resultados experimentales se guardan localmente y quedan excluidos del sitio publicado.

## Referencias científicas y nuevas fuentes

La ampliación de NASA, Smithsonian y Sketchfab incorpora 24 GLB nativos, licencias por archivo y 20 familias con variantes entre fuentes. La galería incluye Draco 1.5.6 local. El [informe de pendientes](sources/external/institutions/multisource-20261022/pending.json) identifica recursos excluidos y el acceso/derechos pendientes de Quaternius. No se modifican los 1021 originales anteriores.


## Ampliación educativa de Sketchfab · 29 de octubre de 2026

Se incorporaron **107 GLB nativos**: Sketchfab pasa de **8 a 115 referencias**, y el catálogo de **1045 a 1152**. Las incorporaciones abarcan las **23 áreas** y conservan autores, licencias, atribuciones, ZIP de originales y evidencias. Cinco candidatos descargados quedan retenidos por legibilidad o encuadre.

El [informe de revisión](docs/SKETCHFAB-20261029.md), el [inventario de 3150 candidatos](sources/external/institutions/sketchfab-20261029/discovery.json) y las [decisiones visuales](sources/external/institutions/sketchfab-20261029/review-notes.json) permiten inspeccionar selección y descartes. La búsqueda revisó 134 términos del plan y tres consultas de contexto; quedan páginas adicionales en Sketchfab. La asociación temática y la escala siguen pendientes de revisión docente.

Seis modelos con materiales heredados disponen de [vistas compatibles revisadas](gallery/compat/index.json). La galería las utiliza para conservar colores y texturas; el botón Descargar GLB entrega siempre el original. Estos derivados no aumentan el recuento del catálogo.
