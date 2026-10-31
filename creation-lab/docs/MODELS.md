# Modelos y esfuerzo

El workflow activo usa Sol/Luna por defecto (el modo `claude` existe solo por
elección explícita; ver más abajo). La asignación es una propuesta
operativa para iterar; aún no es un resultado de benchmark completo. Los pilotos
históricos conservan sus autores, modelos, esfuerzos y calificaciones originales.
El protocolo detallado vive en [ITERATIVE-WORKFLOW.md](ITERATIVE-WORKFLOW.md).

| Trabajo | Modelo solicitado | Esfuerzo |
| --- | --- | --- |
| Brief, composición, arquitectura y coordinación | `gpt-6.1-sol` | `medium` |
| Implementación general e integración | `gpt-6.1-sol` | `medium` |
| Tarea delimitada, componente, variante y documentación acotada | `gpt-6-luna` | `medium` |
| Revisión independiente con imágenes abiertas | `gpt-6.1-sol` | `medium` |
| Diagnóstico difícil justificado por un fallo observado | `gpt-6.1-sol` | `high` |

La revisión usa un autor/contexto distinto del que produjo la geometría y recibe
brief, criterios e imágenes reales con hashes. Registra modelo y esfuerzo
solicitados y efectivos declarados de coordinador, autores, correctores y revisor, además de
herramientas y cambios de contexto. El registro de sesión es una declaración del
coordinador, no una atestación del backend. Una identidad de rol no demuestra que se
seleccionó ese modelo: si la herramienta no expone o confirma el dato, decláralo.
Si Sol o Luna no están disponibles, registra `BLOCKED` y la causa; no sustituyas
modelo/esfuerzo en silencio. La escalada `high` debe justificar el diagnóstico y
mantener trazabilidad; no se usa por defecto para toda tarea.

[model-profiles.json](../config/model-profiles.json) expresa preferencias de
planificación. No cambia el modelo global de Codex, no inicia agentes ni impone
un modelo en herramientas remotas. [codex.example.toml](../config/codex.example.toml)
es un ejemplo local revisable. No instala configuración global ni prueba acceso.

La generación de imágenes es opcional y queda desactivada por defecto, sin modelo
de imagen preferido activo. Para conceptos pueden usarse referencias manuales
con procedencia. Un proveedor de imagen requiere capacidad real, acceso y la
autorización de gasto aplicable; no se atribuye selección de modelo a una
herramienta que no la expone. El login de Codex no es una clave de API y los
perfiles no contienen secretos.

El historial de preparación incluyó Astra `high`/`xhigh`, Sol `high`, Luna
`medium` y preferencias de imagen `gpt-image-2.5-flare`/`gpt-image-2.5-sunburst`.
Son antecedentes, no defaults activos ni evidencia de acceso o calidad.

La comparación futura contempla solo Sol, Sol+Luna y solo Luna con el mismo
brief, biblioteca de componentes, herramientas, presupuestos y dos rondas máximas
de corrección totales por sesión, compartidas entre etapas y aparte de la primera
ejecución blockout y la primera detail. Se recomiendan al menos tres autorías independientes por condición
para un piloto; no equivalen al benchmark completo de seis briefs. Volver a ejecutar
un script existente no crea una autoría nueva. Separa los gates técnico, visual y
de contenido, conserva fallos y no infieras costo/tokens sin telemetría disponible.

El modo `claude` (`iterate.py init --mode claude`) es una elección explícita que no
cambia el default Sol/Luna ni constituye un benchmark. Solo admite IDs exactos:

| Rol | IDs admitidos en `claude` |
| --- | --- |
| Coordinación | `claude-sonnet-5-5`, `claude-opus-5-5` |
| Autoría | `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-haiku-5-5` |
| Revisión (contexto nuevo e independiente) | `claude-opus-5-5`, `claude-sonnet-5-5` |

Los esfuerzos son los de siempre. Los IDs Claude siguen rechazados en `sol`,
`mixed` y `luna`; los IDs Sol/Luna y los alias (`sonnet`, `opus`, ...) se rechazan
en `claude`. No se afirma superioridad medida; registra modelo y esfuerzo
solicitados y reales por rol, sin inventar IDs de agente, uso ni coste.

El modo operativo mixto usa Sol para coordinación/revisión y permite autores
Sol o Luna; los modos puros usan solo Sol o solo Luna también para su revisión
interna, siempre en otro contexto. Una evaluación externa común del benchmark
se registra aparte para no confundir su revisor con un autor de la condición.
La etapa blockout evalúa layout/visibilidad y los `blockoutChecks` explícitos del
brief; el detalle evalúa `contentChecks`/`biologicalChecks` completos. Un PASS de
blockout habilita detallar, sin aprobar contenido fino ni relajar el gate final.
