# GuateGeeks · Biblioteca 3D

Galería de **342 modelos GLB** para Code Studio y Sócrates, organizados en **23 áreas**. Incluye miniaturas locales, vista 3D con cámara y animaciones, búsqueda en español y filtros por área, licencia y movimiento. Los créditos se consultan en cada ficha.

## Laboratorio local de rigging

El [plan del laboratorio](docs/RIGGING-LAB-PLAN.md) define el flujo completo dentro
de este proyecto: seleccionar modelos, prepararlos, generar rigs con UniRig,
evaluar SkinTokens en el equipo local, corregir, animar, revisar en la galería
y producir paquetes versionados. Reutilizará el catálogo y el visor existentes,
con áreas propias para trabajo experimental y derivados revisados.

Estado: planificación. La instalación y las herramientas del laboratorio están
pendientes. La implementación en Code Studio o Sócrates comenzará después de
completar y validar el flujo en `3d-assets`.

**Galería publicada:** [guategeeks.com/3d-assets](https://guategeeks.com/3d-assets/)

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

- **68 modelos CC0 1.0** y **274 CC BY 3.0**.
- **12 modelos con esqueleto** y **13 con animaciones** comprobadas dentro del GLB.
- [Índice navegable de archivos](INDEX.md), [CSV](index.csv), [créditos](ATTRIBUTIONS.md) y [cobertura pendiente](COVERAGE.md).
- `models/<ID>/`: GLB original, metadatos del catálogo, ficha normalizada y licencia.
- [LICENSE.md](LICENSE.md): alcance de licencias de los modelos, la interfaz y los componentes.

Los estados de revisión y las observaciones sobre precisión científica, identificación cultural o animaciones de terceros se conservan en las fichas. La asociación a un área es una propuesta para revisión docente, no una acreditación curricular.

## Actualizar el catálogo

`tools/catalog.py` permite verificar los modelos o ampliar la selección de `selection.json`. Para descargar se proporciona `POLY_PIZZA_KEY` solo en el entorno del proceso. `tools/setup_gallery.py` recupera las dependencias fijadas y las miniaturas nuevas. La publicación utiliza los archivos ya guardados; no consulta la API de Poly Pizza.

```sh
python tools/catalog.py verify
python tools/setup_gallery.py
python tools/build_site.py
python tools/check_site.py
```

El historial completo de fuentes públicas de búsqueda se conserva en `sources/search/`. El proceso de publicación copia un inventario explícito de archivos y excluye contexto de conversaciones, credenciales y directorios de trabajo.
