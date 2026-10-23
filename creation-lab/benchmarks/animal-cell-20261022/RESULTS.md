# Resultados · célula animal para secundaria

22 de octubre de 2026. Se crearon seis alternativas reales con tres modelos
autores y dos niveles de razonamiento. **D es la opción recomendada de este
piloto (87/100); A es la segunda (85/100)**. Ambas superan las comprobaciones
técnicas y la revisión visual y biológica de los rasgos representados.

El [visor local](http://127.0.0.1:4393) permite girar cada modelo, seleccionar sus
trece estructuras y consultar sus funciones en español. Cada alternativa tiene
GLB, fuente editable `.blend`, metadatos de partes y seis renders finales.
Los comandos de inicio y reproducción están en [README](README.md).

## Comparación final

| ID | Modelo / esfuerzo | Puntos | Técnica | Visual | Biología | Reparaciones |
| --- | --- | ---: | --- | --- | --- | ---: |
| A | gpt-6.1-sol / high | 85 | PASS | PASS | PASS | 1 |
| B | gpt-6-luna / medium | 19 | PASS | FAIL | BLOCKED | 1 |
| C | gpt-6-astra / high | 82 | PASS | PASS | FAIL | 0 |
| D | gpt-6.1-sol / medium | **87** | PASS | PASS | PASS | 1 |
| E | gpt-6-luna / high | 44 | FAIL | FAIL | FAIL | 1 |
| F | gpt-6-astra / medium | 82 | PASS | PASS | FAIL | 0 |

La puntuación no sustituye los gates. C y F obtienen una lectura visual
relativamente buena, pero la franja pálida exterior se interpreta como citosol
fuera de la membrana o como una base sin identificar. B tiene trece IDs y un
archivo correcto, pero su envoltura opaca oculta los orgánulos. E presenta
intersecciones, cortes escalonados y relaciones de estructuras poco claras.
Las razones por vista están en [las revisiones](reviews.json).

D ofrece núcleo abierto con nucléolo y cromatina esquemática, RER y REL
distinguibles, Golgi, dos mitocondrias con crestas internas, centríolos y
filamentos. A tiene una disposición más despejada. En ambas quedan mejoras
menores de contraste; los detalles se leen mejor desde la vista elevada.

Los PASS biológicos se limitan a los rasgos visibles de la maqueta. No validan
anatomía oculta, precisión ultraestructural ni la representación de todas las
células animales. Los colores, cantidades y proporciones son convencionales.

## Datos técnicos medidos

| ID | Triángulos | Materiales | Objetos de malla | GLB, bytes | Proceso final, s |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 36,980 | 21 | 193 | 788,468 | 115.375 |
| B | 21,008 | 15 | 92 | 391,928 | 95.000 |
| C | 33,468 | 21 | 202 | 806,236 | 156.578 |
| D | 44,586 | 18 | 189 | 762,996 | 129.844 |
| E | 37,256 | 13 | 90 | 812,612 | 177.406 |
| F | 34,996 | 19 | 183 | 852,740 | 155.250 |

Todas cumplen el presupuesto de 45,000 triángulos, 24 materiales, 350 objetos
y 8 MiB. Su dimensión mayor es aproximadamente 0.30 m. Los diez GLB, contando
primeras versiones y reparaciones, tienen **cero errores y cero advertencias**
en Khronos glTF Validator. Eso valida el formato; no demuestra conservación
durante importación ni calidad educativa.

E conserva superficies, materiales, UV y normales, pero falla el gate de
límites: la dimensión Y pasa de 0.263999999 m a 0.261499956 m al reimportar,
una diferencia de 2.500043 mm. El eje mayor sigue midiendo 0.30 m. Se mantiene
FAIL y no se altera la tolerancia para aprobarlo.

## Procedimiento y alcance

Se usaron contextos independientes y el mismo brief, semilla 20261022,
Blender 5.2.3 LTS, Cycles CPU, dos hilos, 24 muestras y renders de 768 px.
Cada run conserva el código ejecutado, versiones, comandos, hashes y tiempos.
La reapertura del `.blend` y la importación del GLB ocurren en procesos nuevos.
Se cotejan triángulos orientados, posiciones, normales, UV, materiales, límites
y los identificadores de las trece estructuras con el verificador del adaptador.

Un agente revisor independiente, en contexto nuevo y sin conocer el mapping
de autores, abrió las seis vistas finales de cada condición. Calificó biología
(30), legibilidad (25), composición (15), forma/sombreado (15) y utilidad
educativa (15). Su evaluación de utilidad cubre geometría y etiquetas; el
visor se comprobó por separado. Es una revisión asistida, no una evaluación
externa realizada por docentes.

Hubo **diez ejecuciones**: seis iniciales y una reparación técnica en A, B, D
y E. C y F pasaron técnicamente al primer intento. Los otros cuatro fallaron
inicialmente en normales o topología; A/B/D pasan después de reparar. E resolvió
la reimportación y las normales, pero conserva el fallo de límites indicado.
No hubo correcciones estéticas del coordinador. Véase [registro de reparaciones](repairs.json).

Las primeras versiones y revisiones permanecen en sus runs y en
`reviews-blind/history/`. El primer E no obtuvo puntuación visual completa
porque faltaba el render de reimportación. Sus cinco imágenes existentes no
se presentaron como una revisión de seis vistas.

Es un **piloto de un solo brief, n=1 por condición**, no el M7 completo ni una
prueba de superioridad general entre modelos. El tiempo de la tabla incluye
construir, medir, guardar, reabrir, renderizar y reimportar en un host compartido;
no es latencia de inferencia. Algunos intentos iniciales coincidieron con
diagnósticos breves. No se dispone de tokens ni costos, y no se ejecutaron
proveedores externos de texto a 3D ni APIs de imágenes.

## Evidencia e integración

- [Resultados y hashes](results.json), con historial de los diez runs.
- [Revisiones y hashes de las imágenes](reviews.json).
- [Validación Khronos](format-validation.json).
- [Diagnóstico de fuente, GLB e importador](HARNESS-NOTES.md).
- [Pruebas HTTP del visor](viewer-http-validation.json).
- [Pruebas interactivas del visor](viewer-ui-validation.json).
- [Comprobación de coexistencia con el catálogo](integration-validation.json).
- [Procedencia de los autores](authoring-receipt.json) y [fuentes educativas](README.md#fuentes-educativas).

Los artefactos están en `creation-lab/.local/benchmarks/animal-cell-20261022/`.
Se mantienen como experimentos locales fuera del catálogo publicable. Los
`part_id` viajan en extras del GLB; `parts.json` conserva las etiquetas, funciones,
objetos y anclajes en coordenadas Blender y glTF. No se ejecuta autorigging:
este modelo educativo necesita partes separadas, no un esqueleto.

El benchmark usa el módulo de QA del adaptador de rigging, sin modificarlo,
y el visor usa el bundle local de model-viewer de la galería. No modifica los
modelos originales, los índices, los entornos de inferencia ni la salida `_site`
que está preparando el otro trabajo de `3d-assets`.
