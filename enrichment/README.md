# Preparación de la ampliación del catálogo

Estado actualizado al 22 de octubre de 2026: **seis kits completos descargados; 651 modelos incorporados**, además de los 342 originales. Kenney: 637; OpenGameArt: 14. ZIP originales, licencias e inventarios con hashes en `kits/`; familias y coincidencias en `kits/groups.json`. La galería permite revisar cada modelo o agrupar variantes. Véanse `reports/complete-kits.json`, `reports/kenney-oga-20261022.json` (piloto histórico) y `reports/DUPLICATES-REVIEW.md` (comparación con los 342 iniciales). El resto de esta página conserva el plan inicial; el alcance del piloto fue ampliado por el usuario a los seis kits completos.

El listado de fuentes de la investigación anterior sigue pendiente de recuperación. Las siete plataformas de `providers.json` son una selección provisional investigada en sus páginas oficiales; no se presentan como transcripción de aquel listado.

## Archivos preparados

- `providers.json`: fuentes, condiciones observadas, vías de adquisición, estado de acceso y siguiente acción. Que una página haya sido consultada no prueba que una descarga o una credencial funcionen.
- `baseline.json`: huella del índice de partida, cantidades y modelos de autores presentes en varias plataformas. Si cambia el índice, renovar esta referencia antes de importar.
- `priorities.json`: seis líneas de búsqueda vinculadas a las 23 áreas actuales. No demuestra disponibilidad de los objetos buscados.
- `candidate.schema.json`: contrato propuesto de metadatos para candidatos externos, separado de la versión 1 del catálogo público. La promoción del primer lote se documenta en sus metadatos y en el informe del lote.
- `.gitignore`: excluye `enrichment/staging/` del control de versiones. La evidencia revisada se promoverá después al directorio de fuentes que corresponda.

## Orden de trabajo propuesto

1. **Kenney:** inspeccionar [Nature Kit](https://kenney.nl/assets/nature-kit), [Food Kit](https://kenney.nl/assets/food-kit) y [Modular Buildings](https://kenney.nl/assets/modular-buildings). Sus fichas indican CC0. Registrar paquete, versión y ruta interna de cada pieza; contar objetos, no copias FBX/OBJ/GLB del mismo objeto. [Condiciones oficiales](https://kenney.nl/support).
2. **OpenGameArt:** buscar piezas que cubran necesidades pendientes y personajes con clips. Revisar créditos, licencias alternativas y componentes por ficha. Crear miniaturas propias: los previews no heredan necesariamente la licencia del asset. [FAQ oficial](https://opengameart.org/content/faq).
3. **Sketchfab:** buscar especímenes y objetos exactos; la descarga por API requiere autenticación de usuario. Falta comprobar acceso autorizado para esta biblioteca. No se reutilizan las credenciales de otras plataformas. [Download API](https://sketchfab.com/developers/download-api), [flujo de descarga](https://sketchfab.com/developers/download-api/downloading-models).
4. **Smithsonian / NASA:** priorizar ciencia y patrimonio documentados. En Smithsonian comprobar la marca CC0 del archivo concreto, no solo los metadatos. En NASA conservar las condiciones y los créditos del recurso, incluidas excepciones de terceros; no asignar CC0 por defecto. [Smithsonian](https://www.si.edu/openaccess/faq), [NASA 3D](https://science.nasa.gov/3d-resources/), [condiciones NASA](https://www.nasa.gov/nasa-brand-center/images-and-media/).
5. **Poly Haven:** seleccionar objetos útiles y presupuestos web pequeños. Assets CC0; generar previews propios. Usar la API oficial con identificador de aplicación y caché; comprobar sus condiciones vigentes antes de automatizar. [Licencia](https://polyhaven.com/license), [condiciones API](https://github.com/Poly-Haven/Public-API/blob/master/ToS.md).
6. **Quaternius:** revisar la licencia específica de la versión antes de adquirir. La página vigente muestra QAL v1.0, de 28 de agosto de 2026, que restringe redistribuir los archivos como assets, incluso modificados. Las nuevas versiones QAL quedan como referencias para esta biblioteca descargable salvo derechos específicos compatibles. No se sustituyen las evidencias CC0 existentes por una licencia global nueva. [QAL oficial](https://quaternius.com/license.html).

## Selección del primer lote

Propuesta inicial: hasta 24 objetos nuevos después de deduplicar, elegidos por carencias reales y utilidad en Code Studio y Sócrates. El piloto puede ser menor si no hay candidatos adecuados. Objetivo provisional para derivados web: hasta 25 MiB por GLB y 200 MiB adicionales en total; revisar tamaño acumulado del sitio antes de ampliar. Estos límites de planificación no modifican los presupuestos de los laboratorios.

`priorities.json` concentra especies e instrumentos guatemaltecos identificables, anatomía, mecanismos y animación. Un loro no resuelve quetzal ni un templo genérico acredita Tikal. Mantener identificaciones científicas, institucionales y culturales verificables, y declarar toda simplificación. No hay asignación curricular aprobada en esta fase.

## Flujo de adquisición y revisión

1. **Descubrir:** guardar URL canónica, ID de origen, autor, paquete/versión y utilidad propuesta. Usar API o descarga oficial; respetar límites y condiciones del servicio. Caché, reanudación y espera ante HTTP 429. Una página no descargable queda como referencia.
2. **Registrar derechos:** capturar licencia y fecha, evidencia de la ficha/archivo y SHA-256. Conservar todas las alternativas y registrar cuál se aplica; usar IDs de licencia reconocidos o `LicenseRef-*` para condiciones propias. Evaluar malla, materiales, texturas, clips y previews por separado. Un permiso desconocido se registra como `null`.
3. **Adquirir originales:** solo cuando la descarga esté permitida, guardar en `enrichment/staging/<plataforma>/<ID>/` sin ejecutar contenidos. Conservar bytes y hashes. Al extraer archivos, rechazar rutas absolutas, `..`, enlaces que salgan del destino y tamaños descomprimidos excesivos. No persistir URLs firmadas con secretos ni tokens.
4. **Deduplicar:** comparar ID canónico y hashes contra `index.json` y entre candidatos; después comparar autor, título, paquete y geometría. Un SHA distinto después de convertir no demuestra un objeto nuevo. Duplicados exactos amplían procedencia, no cantidades. Los 57 modelos de Quaternius y 4 de Kenney del catálogo son puntos de comparación, no duplicados externos ya confirmados.
5. **Preparar derivado web:** conservar originales y producir GLB separado, con operación, herramienta, versión y hashes de entrada/salida. Registrar dimensiones originales, unidades, ejes, pivote, materiales y texturas. No aplicar la normalización a 2 m del laboratorio implícitamente. Los rigs nuevos pasan por el laboratorio existente; no se ejecuta inferencia en esta fase.
6. **Comprobar técnicamente:** GLB válido, dependencias resueltas, carga sin red externa, extensiones soportadas, métricas de malla/textura, skins/joints y nombres/duración de clips reales. La etiqueta «animated» de una plataforma no sustituye la inspección del archivo.
7. **Revisar visualmente y educativamente:** abrir render y visor real; comprobar materiales, escala, cámara, deformaciones, clipping y clips. Registrar revisiones `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN` por separado. Un proceso terminado no equivale a calidad visual.
8. **Promover:** solo candidatos con derechos de la acción concreta y las cuatro revisiones en `PASS`. Exportar en una transacción revisable catálogo, CSV, áreas, fuentes, licencias, créditos, cobertura, miniaturas y manifiesto de integridad. Ejecutar build/check y probar la galería bajo `/3d-assets/` antes del despliegue.

## Licencias e índices

Todas las licencias encontradas pueden representarse en el inventario de candidatos. Su presencia no concede permiso para redistribuir el archivo ni para modificarlo. Separar descarga, redistribución original, redistribución derivada, uso comercial, atribución y compartir igual. No asignar una licencia uniforme al corpus.

CC0 admite copia, modificación y distribución bajo sus condiciones. CC BY-SA exige cumplir compartir igual al distribuir adaptaciones. Para NC evaluar el uso concreto; ND requiere revisar la distribución de cualquier adaptación, incluido rigging o animación. Los cambios exclusivamente técnicos de formato requieren analizar la licencia aplicable. [CC0](https://creativecommons.org/publicdomain/zero/1.0/), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/).

`reference-only` conserva una referencia y sus condiciones sin archivo público; `staging` indica adquisición local en revisión; `eligible-for-promotion` indica elegibilidad revisada y todavía no publicación. El esquema por sí solo no verifica los derechos ni las condiciones entre estos estados.

Para la futura versión del índice usar IDs con espacio de nombres (`proveedor:ID`, y miembro estable para piezas de un paquete). Conservar los IDs Poly Pizza y sus enlaces actuales. Añadir procedencias múltiples y relación original/derivado sin modificar los originales existentes. El visor necesitará filtro de fuente y estados de uso por licencia; el builder y sus textos hoy específicos de Poly Pizza deben adaptarse antes de añadir un proveedor real. Conservar selección, enlaces profundos, atribuciones, funcionamiento local y manifiestos.

El primer lote amplía la galería y sus índices; los modelos originales existentes permanecen intactos. Hay trabajo concurrente de creación y rigging: no incluirlo en un commit de ampliación ni reconstruir su entorno como parte de esta tarea.

## Criterio para iniciar la descarga

Confirmar o recuperar el listado original, elegir el primer lote de `priorities.json`, resolver acceso de la fuente elegida y verificar derechos por archivo. Después implementar su adaptador con adquisición oficial, evidencia y deduplicación. No se ha programado un rastreo recurrente ni una descarga masiva.

La adquisición y conversión utiliza Blender para export/render y Pillow para codificar WebP. El sitio estático y su validación continúan usando únicamente la biblioteca estándar de Python. `tools/promote_external.py` es una promoción offline que exige evidencia de deduplicación y revisión; nunca sobrescribe una carpeta de modelo existente.
