# Componentes geométricos

Biblioteca pequeña para componer blockouts con piezas comprobables. No genera
una célula final, valida biología ni aprueba un diseño. Coordenadas XYZ diestras,
Z arriba, unidades en metros; cada posición pertenece al mismo marco explícito.
Importar `components` funciona con Python sin Blender. Solo el adaptador requiere
`bpy`. No hay dependencias externas ni archivos `.blend` compartidos.

```python
from components import CutawayProfile, FlattenedCisterna, sphere
from components import circle_outline, cylinder, extruded_outline, rounded_box, rounded_rect_outline
from components import material, mesh_object, validate_mesh

profile = CutawayProfile(radii=(.12, .10, .08), cut_fraction=.15,
                         wall_fraction=.08, center=(0, 0, 0))
shell = profile.shell(segments=32, rings=12)
fill = profile.fill(segments=32, rings=12, clearance=.03, inset=.05)
validate_mesh(shell, max_triangles=2000)  # Presupuesto de este componente/brief.
mat = material('Envoltura', (.06, .35, .38), roughness=.5)
obj = mesh_object('Borde continuo', 'envoltura', shell, mat, smooth=False)
```

| API | Contrato |
| --- | --- |
| `sphere(radii, center=..., segments=24, rings=12)` | `MeshData` de elipsoide cerrado; un vértice por polo, triángulos explícitos, winding exterior. |
| `CutawayProfile(...).shell(segments=32, rings=12)` | Envoltura con cavidad abierta y labio anular continuo. El material sólido es manifold cerrado, aunque la cavidad esté abierta. |
| `profile.fill(clearance=.02, inset=.03, segments=32, rings=12)` | Relleno cerrado derivado de la misma malla interior por homotecia hacia un pivote interior. `clearance` = hueco inferior/altura de cavidad; `inset` = hueco superior/radio Z exterior. |
| `FlattenedCisterna(radii, wave, center)` | Elipsoide aplanado deformado suavemente en Z; no representa lumen ni ultraestructura. |
| `sheet.mesh(segments=24, rings=12)` | Malla de la misma ecuación usada por anclajes. |
| `sheet.surface(theta, phi)` | Punto y normal exterior unitaria; theta en `[0,pi]`, phi en radianes. |
| `sheet.anchor(theta, phi, offset=0)` | Centro desplazado según esa normal, por ejemplo en el radio de un ribosoma. |
| `validate_mesh(mesh, closed=True, max_triangles=None)` | Finito, sin degenerados, índices válidos, uso de vértices, manifold, winding y volumen exterior. Devuelve conteos y volumen firmado. |
| `rounded_rect_outline(width, height, radius, segments=6, center=(0, 0))` | Lista `(x, y)` antihoraria, en metros. `radius` de 0 (cuatro esquinas vivas) a `min(width, height)/2`; cada arco de esquina tiene `segments` subdivisiones. Valores no finitos o no positivos lanzan `ValueError`. |
| `circle_outline(radius, segments=24, center=(0, 0))` | Polígono regular antihorario inscrito en el círculo, primer punto en ángulo 0; `segments >= 3`. |
| `extruded_outline(outline, holes=(), thickness=0.001, z0=0.0)` | `MeshData` cerrada, manifold y exterior de un contorno plano extruido de `z0` a `z0 + thickness`. El contorno puede ser cóncavo; un contorno horario se normaliza a antihorario y los agujeros pueden venir en cualquier sentido. Los agujeros deben quedar estrictamente dentro y no tocarse, cruzarse ni anidarse (también se rechazan contornos con menos de 3 puntos, puntos repetidos, área nula o autointersección): `ValueError`. Tapas por ear clipping tras puentear cada agujero al contorno; paredes de dos triángulos, con las de los agujeros hacia el hueco. Comparte vértices entre tapas y paredes (`2 * (N contorno + N agujeros)` vértices, sin vértices sin usar). Los puentes son diagonales internas, no huecos. |
| `refined_plate(outline, holes=(), thickness=0.001, z0=0.0, spacing=None)` | Mismas entradas, validación, paredes y volumen que `extruded_outline` (contornos de agujeros intactos), con tapas re-trianguladas por flips de Lawson (Delaunay restringido: las aristas de borde no cambian). Con `spacing` (metros, finito y positivo) subdivide el contorno exterior a esa longitud, y más cerca de un agujero (cada arista mide como máximo 3 veces su distancia al agujero más cercano), y añade puntos de Steiner en rejilla hexagonal a 0.6 × `spacing` de todo borde. Placa micro:bit 52 × 42 mm con agujeros de 3.4 mm a 0.1 mm del borde y `spacing=0.0026`: 2044 triángulos, ángulo mínimo de tapa 10.5° (ear clipping: 0.002°). Sin `spacing` conserva vértices y número de triángulos. Inserción O(puntos × triángulos): pensada para cientos de puntos. |
| `rounded_box(size, radius, center=(0, 0, 0), segments=3)` | Caja con todas las aristas y esquinas redondeadas por `radius` (`radius < min(size)/2`; 0 da la caja de 12 triángulos). Cubo subdividido con vértices sobre el sólido redondeado, es decir inscrito: el volumen queda por debajo del analítico (aprox. 0.2 % con `segments=3` y 0.6 % con 2 en las pruebas, para radios pequeños; el error crece con radius/size: cerca de 1 % con r/size = 0.3 y cerca de 3 % hacia 0.5 con `segments=3`, menos con más `segments`). Volumen analítico: `(a-2r)(b-2r)(c-2r) + 2r[(a-2r)(b-2r)+(b-2r)(c-2r)+(a-2r)(c-2r)] + pi r^2 [(a-2r)+(b-2r)+(c-2r)] + 4/3 pi r^3`. |
| `cylinder(radius, height, center=(0, 0, 0), segments=24)` | Cilindro cerrado con eje Z centrado en `center`; exactamente `4 * segments` triángulos (abanico en cada tapa desde un vértice central, más `2 * segments` laterales). Los vértices están en el círculo circunscrito. |
| `mesh_object(name, part_id, mesh, mat, ..., max_triangles=None)` | Objeto final `MESH`, sin modificadores; metadatos `part_id` y versión; Principled obligatorio y normales de esquina fijadas. |

`wall_fraction` reduce proporcionalmente los tres radios interiores; no es grosor
normal constante. El corte debe cruzar ambos perfiles, lejos de sus polos.
La envoltura y el relleno **deben usar los mismos segments/rings**: la contracción
preserva contención en el poliedro convexo real, incluso a baja resolución. Dos
teselaciones independientes de una misma ecuación no ofrecen esa garantía.
No deformar después las piezas por separado si se necesita conservarla.

En anclajes, usar `theta=pi*j/rings`, `phi=tau*i/segments` toca un vértice de la
malla real. Otros ángulos muestrean la superficie analítica; no garantizan
contacto con el plano facetado. Si se transforma después el objeto, transformar
también anclajes y normales en ese mismo marco. El radio del anclaje y la
curvatura pueden exigir separación adicional; comprobarlo en renders.

Las formas de placa (`shapes.py`) son Python puro y devuelven `MeshData` que
pasa `validate_mesh`. Ejemplo: una placa de 52 x 42 mm con esquinas de 3 mm y
cinco agujeros: `extruded_outline(rounded_rect_outline(.052, .042, .003),
[circle_outline(.003, 24, (x, -.0165)) for x in (-.0225, -.01125, 0, .01125, .0225)],
thickness=.0016)` da 608 triángulos (con astillas de ear clipping; `refined_plate` con
las mismas entradas da tapas bien formadas). Un agujero de radio .0035 en x = ±.0225
sería tangente al borde de 0.026 y se rechaza. Límites: el volumen es el del
polígono extruido (un círculo de 24 lados pierde ~1.1 % de su área); el ear
clipping es O(n^3) y está pensado para cientos de puntos, no para miles; no hay
chaflanes, redondeo por arista ni agujeros que toquen el contorno.

No se incluye tubo todavía: esta biblioteca cubre los fallos repetidos de polos,
borde/relleno y apoyo de anclajes. No prueba ausencia de cualquier
autointersección de una deformación arbitraria ni asigna presupuestos del robot
a otros assets. Los límites de `demo-brief.json` son solo de esta demostración.

## Ejecución y comprobación

Desde la raíz del repositorio, con Python 3.10+:

```powershell
python -m unittest discover -s creation-lab/tests -p test_components.py -v
$env:CREATION_TEST_BLENDER = '/ruta/absoluta/a/blender'
python -m unittest discover -s creation-lab/tests -p test_components.py -v
```

El probe Blender construye en memoria, verifica los 19 objetos, cinco IDs,
materiales, triangulación y normales; no guarda ni renderiza. La prueba pura
verifica cierre, winding, semiespacios de contención del relleno a varias
resoluciones/cortes, normales y anclajes compartidos, errores y presupuestos.
`PASS` técnico de esos tests no equivale a inspección visual.

La demo implementa el contrato común `build()` y no hace E/S. Usar el runner
para conservar un run nuevo, fuente independiente, GLB, renders y medición real
de geometría/dimensiones en reapertura/reimportación; reemplazar los IDs por
los contextos reales de ejecución. Consultar `iterate.py --help` para el CLI:

```powershell
python creation-lab/iterate.py init --brief creation-lab/components/demo-brief.json --output creation-lab/.local/iterations/component-demo-UNIQUE --mode mixed --actor-id CONTEXTO_SOL_REAL --model gpt-6.1-sol --effort medium
python creation-lab/iterate.py run --session creation-lab/.local/iterations/component-demo-UNIQUE --generator creation-lab/examples/component-demo.py --stage blockout --blender '/ruta/absoluta/a/blender' --actor-id CONTEXTO_AUTOR_REAL --model gpt-6.1-sol --effort medium
```

El runner conserva snapshot de `components/` dentro de `run/code/`, para que un
cambio futuro de la biblioteca no altere la receta histórica. Cada agente es
dueño de su escena; intercambia el generador y el recibo, nunca el mismo `.blend`
editable. Abrir las imágenes antes de completar la revisión. La demo no otorga
automáticamente `PASS` visual, aprobación de blockout ni permiso para detalle.

La referencia A/D del benchmark informa decisiones de polos y normales. Se
conservan intactos sus autores, fuentes y recibos históricos; este ejemplo no
hereda su aprobación visual o biológica.
