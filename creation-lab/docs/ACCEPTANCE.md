# Criterios de aceptación

`PASS`: comprobado con evidencia. `FAIL`: incumplimiento observado.
`BLOCKED`: falta un requisito o dependencia. `NOT_RUN`: no ejecutado.
Los estados técnico, visual y de contenido se registran por separado. Para
creaciones nuevas sigue [el flujo iterativo](ITERATIVE-WORKFLOW.md), con blockout
revisado antes del detalle y dos correcciones totales por sesión por defecto.

## Núcleo M1

- Un brief válido define ID, dimensiones en metros, orientación, presupuesto
  y procedencia. Los valores inválidos se rechazan antes de invocar Blender.
- Cada ejecución usa un directorio nuevo, con logs y hashes. Una segunda
  ejecución conserva intacta la anterior; un fallo conserva su evidencia.
- Blender genera una escena canario y guarda una fuente editable `.blend`.
- Otro proceso limpio reabre el `.blend`. Renderiza frente, lateral, espalda,
  tres cuartos y wireframe. Cada imagen se abre para revisión real.
- Exporta GLB y lo reimporta en otro proceso limpio. Comprueba dimensiones
  con tolerancia explícita, ejes, geometría finita, materiales y presupuestos.
- El conteo corresponde a geometría evaluada/exportada, no solo a la malla
  anterior a modificadores. GLB no depende de archivos externos.
- Un hash confirma integridad; no demuestra calidad artística. El informe
  visual identifica imágenes revisadas y los problemas observados.
- El handoff es candidato y conserva fuentes, licencia y transformaciones.
  No modifica originales, corpus, catálogo ni una inferencia en curso.

## Dirección artística y producción

El primer concepto y blockout del asset de producción requieren revisión del
usuario antes del detalle, tal como define el workflow solicitado. El canario
técnico no equivale a esa aprobación. Imágenes generadas sirven de referencia,
no como planos métricos; las dimensiones del brief son la autoridad.

Robot low-poly: altura 0.30 m; cuerpo compacto, pantalla frontal, dos ruedas
y brazos simples; sin logo inventado; ≤6000 triángulos exportados LOD0,
≤2 materiales, texturas ≤2048 px. Piezas significativas editables.

Robot detallado: master independiente del derivado optimizado; conserva diseño
y proporciones aprobados. El derivado tiene ≤40000 triángulos y ≤4 materiales,
texturas ≤2048 px; UV y bake cuando hagan falta. Verificar clay, wireframe,
vistas generales y closeups. Usa las dos correcciones totales de la sesión;
otro presupuesto debe fijarse explícitamente antes de comenzar.

La prueba orgánica evalúa anatomía estilizada, articulaciones y continuidad
por separado. Una prueba hard-surface satisfactoria no demuestra esa capacidad.

## Puente interactivo de herramientas Blender

Solo un controlador de la escena. Blender Lab MCP es el preferido; consulta
la auditoría antes de instalar. Prueba de salida: descubrir herramientas reales,
consultar escena desechable, capturar evidencia visual, hacer una modificación
pequeña y comprobar el resultado. Una entrada TOML no cuenta como conexión.

## Benchmark

Dos briefs low-poly, dos hard-surface detallados, uno orgánico y una escena.
Repeticiones y semillas fijadas; mismas referencias, presupuestos y herramientas
en comparación entre modelos. Evaluación de sistemas completos se informa
separada. Registrar calidad visual ciega, cumplimiento, editabilidad, exportación,
tiempo observado, intervención humana y gasto observable. Conservar fallos.
Sin acceso o presupuesto para un competidor, registrar `NOT_RUN`.


Para aceptación de objetos/escenas interactivas y jobs de proveedores, consulta los [gates de Studio](../../studio/docs/ACCEPTANCE.md). La conexión MCP descrita arriba prueba una herramienta, no la interacción de un asset.
