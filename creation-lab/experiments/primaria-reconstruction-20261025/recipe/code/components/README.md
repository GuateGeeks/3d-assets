# Componentes geométricos

Biblioteca pequeña para componer blockouts con piezas comprobables. No genera
una célula final, valida biología ni aprueba un diseño. Coordenadas XYZ diestras,
Z arriba, unidades en metros; cada posición pertenece al mismo marco explícito.
Importar `components` funciona con Python sin Blender. Solo el adaptador requiere
`bpy`. No hay dependencias externas ni archivos `.blend` compartidos.

```python
from components import CutawayProfile, FlattenedCisterna, sphere
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
