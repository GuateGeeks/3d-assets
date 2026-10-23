# Modelos y esfuerzo

Se conserva la distribución propuesta en la investigación del usuario. Los
identificadores de texto están disponibles en las herramientas de agentes de
esta sesión. Las preferencias no equivalen a resultados de benchmark.

| Trabajo | Modelo | Esfuerzo |
| --- | --- | --- |
| Diagnóstico M0 | `gpt-6-astra` | `high` |
| Arquitectura M1 | `gpt-6-astra` | `xhigh` |
| Implementación y pruebas | `gpt-6.1-sol` | `high` |
| Geometría o integración difícil | `gpt-6-astra` | `xhigh` |
| Revisión independiente | `gpt-6-astra` | `xhigh` |
| Documentación acotada | `gpt-6-luna` | `medium` |

La [guía oficial de selección](https://developers.openai.com/api/docs/guides/model-selection)
recomienda probar modelo y esfuerzo contra la calidad, latencia y coste reales.
No activar `max` para todo el laboratorio.

La investigación propone `gpt-image-2.5-flare` para exploración y
`gpt-image-2.5-sunburst` para refinamiento. Son preferencias conservadas en el
perfil; no se ha comprobado acceso de API ni ejecutado una generación de imagen.
El backend de imágenes se selecciona entre herramientas realmente disponibles;
no se afirma que una herramienta permita elegir esos modelos si no lo expone.

Para M2, el modo manual acepta referencias con su procedencia. El modo proveedor
requiere implementación, credenciales y autorización de gasto aplicables. El login
de Codex no se trata como una clave de API. No se almacenan secretos en perfiles.

El archivo [model-profiles.json](../config/model-profiles.json) es configuración
de planificación del workflow; no cambia el modelo global de Codex ni inicia
agentes por sí solo. En esta preparación se usaron agentes Astra `xhigh`,
Sol `high` y Luna `medium` para las tareas indicadas.
