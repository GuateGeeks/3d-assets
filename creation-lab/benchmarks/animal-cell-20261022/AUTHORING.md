# Contrato común de generación

Lee `brief.json`. Entrega un generador original de célula animal didáctica que
cumpla ese brief. Es un benchmark experimental autorizado, no el primer asset
de producción del robot: no hay aprobación de concepto pendiente. El público
secundaria y etiquetas españolas ya fueron confirmados.

Escribe únicamente el `generator.py` de la condición asignada. Define `build()`
sin argumentos y devuelve un diccionario con `title` (título breve),
`design_notes` (decisiones en español), y `parts`: un mapa de los 13 IDs exactos
del brief, cada uno con `label_position: [x,y,z]` en coordenadas de mundo Blender,
metros. Ese punto debe señalar una superficie visible representativa.

`build()` se llama en Blender nativo5.2.3LTS sobre una escena vacía. Puedes
importar bpy, math, random y mathutils. Semilla20261022. Toda geometría final
debe ser MESH: convierte curvas. Cada objeto de malla debe tener
`obj["part_id"]` con uno de los 13IDs exactos. Nombres editables como
`mitocondrias__cresta_01`; muchas mallas por parte son válidas. No unir toda la
célula en una malla. No dejar modificadores sin aplicar.

Las etiquetas las añade el visor común. NO crear texto3D, rótulos, cámaras,
luces, fondos, suelo, animaciones o armatures. No guardar, renderizar, exportar
ni cerrar Blender. El runner compartido hace esas tareas. Usa Principled con
BaseColor/Roughness/Metallic y también diffuse_color. No texturas ni recursos
externos, complementos, red o llamadas a otros modelos. Evita transparencias
superpuestas y booleans caros: muestra cortes geométricos reales.

Busca una maqueta de buena factura: formas diferenciadas, membranas finas,
cortes abiertos, separación espacial y paleta coherente. Las 13partes deben
ser reconocibles, no sólo existir en metadata. Puedes exagerar tamaños para
legibilidad sin relaciones falsas. Crestas y nucléolo visibles. Apertura hacia
la cámara del brief, máximo45000triángulos,24materiales,350mallas,8MiBGLB.

No leas ni copies otras condiciones/resultados/evaluaciones. No delegues.
No ejecutes Blender: el coordinador ejecuta el mismo runner para todas.
Puedes comprobar sintaxis sin ejecutar el archivo. Entrega la primera versión.
Máximo una reparación técnica por condición, en intento nuevo; conservar
fallos. Sin rondas estéticas ocultas. No se estiman costes o tokens no expuestos.
