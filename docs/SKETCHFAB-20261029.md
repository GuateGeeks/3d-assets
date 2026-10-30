# Revisión de Sketchfab · 29 de octubre de 2026

El catálogo pasa de 1045 a **1152 modelos**, con **115 de Sketchfab** (107 nuevos). Las 23 áreas reciben referencias complementarias; la asociación curricular, identificación cultural, escala y precisión científica siguen pendientes de revisión docente.

Se revisó la primera página de 24 resultados de los 134 términos existentes, más tres consultas de contexto. El inventario conserva 3150 candidatos únicos, incluidos los complementos directos. **No se agotaron las páginas adicionales ni se descargó todo Sketchfab.**

## Evidencia

- [Búsquedas, candidatos y decisiones](../sources/external/institutions/sketchfab-20261029/discovery.json).
- [Comparación contra los 1045 modelos de partida](../sources/external/institutions/sketchfab-20261029/deduplication.json): cero copias SHA-256 o coincidencias de huella entre los 107 aprobados y la base, y entre pares. Las no coincidencias no descartan variantes semánticas.
- [Revisión visual](../sources/external/institutions/sketchfab-20261029/visual-review.json): 112 originales abiertos y reimportados en Blender 5.2.3 LTS, CPU, seis vistas por modelo y 14 hojas de contacto inspeccionadas. Cinco candidatos retenidos por legibilidad o encuadre.
- [Créditos de todos los renders](../sources/external/institutions/sketchfab-20261029/review-attributions.json), incluidos los retenidos.
- [Agrupación semántica](../sources/external/institutions/sketchfab-20261029/grouping-plan.json): conserva familias previas, integra microscopios y añade 54 referencias antes no agrupadas. Cada miembro mantiene su licencia.

Los GLB oficiales se conservan byte por byte. Las miniaturas son renders propios. Los modelos con líneas auxiliares usan una firma de triángulos y segmentos; las huellas históricas de modelos triangulados no cambian. Los archivos originales de los 1045 modelos previos permanecen intactos.

## Nuevas referencias por área

| Área | Nuevos GLB asociados |
| --- | ---: |
| Personajes, narrativa y animación | 3 |
| Animales y biodiversidad | 12 |
| Bosques y plantas | 8 |
| Agua y ecosistemas acuáticos | 6 |
| Tierra, relieve y geografía | 4 |
| Espacio y astronomía | 3 |
| Laboratorio e investigación | 5 |
| Cuerpo humano y salud | 4 |
| Alimentos, agricultura y nutrición | 9 |
| Geometría, tiempo y medición | 4 |
| Física, máquinas y energía | 5 |
| Robótica y electrónica STEAM | 5 |
| Computación y redes | 5 |
| Escuela, lectura y vocabulario | 5 |
| Comunidad, servicios y ciudadanía | 6 |
| Transporte y movilidad | 3 |
| Historia y patrimonio | 6 |
| Arte y música | 5 |
| Deporte y recreación | 5 |
| Oficios, herramientas y productividad | 6 |
| Ambiente y sostenibilidad | 6 |
| Escenarios y juegos para Code Studio | 4 |
| Contexto guatemalteco y mesoamericano | 12 |

Un GLB puede figurar en varias áreas. Algunos GLB de autor contienen conjuntos de objetos; la ficha los presenta como tales, sin confundirlos con copias binarias.

## Controles

`python tools/reindex.py`, `python tools/audit_catalog.py`, `python tools/build_site.py`, `python tools/check_site.py`, siete pruebas de políticas/huellas y seis de selección de galería. Los controles de laboratorios y fuentes conservadas también se verifican en CI. La comprobación final del sitio público se realiza después del despliegue.

La galería corrige la selección inicial al abrir un filtro de fuente: el visor selecciona un resultado del filtro, respeta su orden y muestra un estado sin carga cuando no hay resultados.
