# Contrato de módulos · Escuela Flat/Minimal

Prueba aislada pedida por el usuario: diorama de una escuela, estilo **Flat Shaded /
Minimalist 3D**, animado e interactivo en la web. El coordinador (Opus) reparte
módulos por modelo, ensambla un solo generador y ejecuta Blender. **Ningún autor
ejecuta Blender** (una sola carga de Blender a la vez la gestiona el coordinador).

Lee `brief.json` (partes, estilo, checks) y `kit.py` (primitivas, paleta, `obj()`).

## Qué entregas

Un archivo `module_<nombre>.py` en tu carpeta de autor con **una sola función**
pública `module_<nombre>()` sin argumentos, más funciones auxiliares con prefijo
`_<nombre>_` (evita choques de nombres al concatenar). Reglas:

- **Sin imports.** El archivo se concatena después de `kit.py`; usa directamente
  `math`, `random`, `GROUND`, `box`, `box_on`, `cylinder`, `cone`, `frustum`,
  `pyramid`, `gable`, `blob`, `transform`, `merge`, `obj`, `PALETTE`.
- Crea cada objeto final con `obj(nombre, part_id, malla, color, anim=None)`.
  `color` es una clave de `PALETTE`. Solo tus `part_id` asignados.
- Devuelve `{part_id: {"label_position": [x, y, z]}}` para cada parte asignada:
  un punto **sobre** la parte, visible desde arriba/frente, donde va su etiqueta.
- Sin E/S, red, luces, cámaras ni texto 3D. Determinista: si usas `random`,
  crea `rng = random.Random(<entero fijo>)`.
- **Facetado minimalista:** pocas caras (cilindros 6–10 segmentos, `blob` 6–8 ×
  4–6), siluetas limpias, sin microdetalles. Une con `merge()` las piezas que
  comparten color, parte y movimiento, para pocos objetos.
- Las mallas deben ser sólidos cerrados (las primitivas del kit lo son). Piezas
  delgadas: grosor mínimo 0.0008 m. Lo que va sobre el terreno empieza en
  `GROUND` (puede hundirse ≤0.001 para no flotar). Superficies coplanares de
  distinto color: separa ≥0.0006 m en altura o profundidad para evitar z-fighting.
- Respeta tu región del plano (abajo). Nada fuera de X[-0.20,0.20], Y[-0.15,0.15].

Comprueba sin Blender desde la raíz de `3d-assets`:

```sh
python3 creation-lab/.local/claude-school-20261023/spec/check_module.py RUTA/module_<nombre>.py
```

Debe terminar con `"ok": true`. Informa ruta, sha256 y el resumen del check.

## Plano (metros; Z arriba; frente -Y)

| Elemento | Región / medidas |
| --- | --- |
| Base | X[-0.20,0.20] Y[-0.15,0.15]; tierra Z[-0.056,-0.044], pasto Z[-0.044,-0.040] |
| Calle | Y[-0.147,-0.105]; asfalto encima del pasto; carril del bus y≈-0.126 |
| Banqueta | Y[-0.105,-0.093] a todo lo ancho |
| Camino a la puerta | X[-0.014,0.014], Y[-0.093,-0.010] |
| Edificio | huella X[-0.10,0.10] Y[0.00,0.075]; 2 pisos hasta Z=0.030; techo a dos aguas hasta ≈0.058 |
| Torre del reloj | huella X[-0.022,0.022] Y[-0.010,0.030]; hasta Z≈0.085; techo piramidal hasta ≈0.115; reloj al frente (y≈-0.010) centro Z≈0.065 |
| Puerta | en la torre, frente y≈-0.010, X[-0.010,0.010], Z GROUND→GROUND+0.030; bisagra en x=-0.010 |
| Asta y bandera | asta en (-0.045,-0.060), alto ≈0.11 sobre GROUND |
| Columpios | X[-0.185,-0.085] Y[-0.085,-0.025] |
| Cancha | X[0.040,0.190] Y[-0.088,-0.012] |
| Árboles | puntos sugeridos (x,y): (-0.175,0.120) (-0.120,0.125) (0.120,0.125) (0.175,0.115) (-0.170,0.040) (0.170,0.040) (-0.060,0.125) (0.060,0.125) |
| Estudiantes | figuras de ≈0.020 de alto; en camino, banqueta y patio (no dentro de cancha/columpios) |
| Nubes | Z[0.095,0.135], X[-0.17,0.17], Y[-0.05,0.10] |

## Animación (metadatos en `obj(..., anim=...)`)

Los módulos **no crean animaciones**: describen el movimiento y el paso de
animación lo construye después. `anim` es:

```python
{'clip': 'bandera', 'kind': 'sway', 'pivot': [x, y, z], 'axis': 'Z',
 'params': {'amplitude_deg': 18, 'period': 2.4, 'phase': 0.0}}
```

`pivot` en coordenadas de mundo; el objeto gira/se traslada respecto a él.
`params` admite números, texto o **listas planas** de números. `period` en segundos.

| kind | Movimiento | params |
| --- | --- | --- |
| `hinge` | gira de 0 (cerrada) a `angle_deg` (abierta) alrededor de `axis` en `period`; no es bucle: el visor la reproduce una vez y alterna el sentido (enmienda del coordinador, 23 oct) | `angle_deg`, `period` |
| `spin` | rotación continua alrededor de `axis` | `period` (s/vuelta), `direction` (+1/-1) |
| `sway` | oscilación senoidal alrededor de `axis` | `amplitude_deg`, `period`, `phase` (0–1) |
| `swing` | péndulo alrededor de `axis` | `amplitude_deg`, `period`, `phase` |
| `bounce` | rebote vertical \|sin\| | `height`, `period`, `phase` |
| `drift` | vaivén de traslación a lo largo de `axis` | `distance`, `period`, `phase` |
| `path` | recorrido lineal por puntos de mundo del pivote, en bucle; gira para mirar hacia donde avanza (frente local = -Y del modelo salvo `forward`) | `points` (x,y,z planos), `period`, `forward` ('+X','-X','+Y','-Y') |
| `walk` | como `path` con balanceo vertical | `points`, `period`, `bob`, `forward` |

Clips y partes (`brief.animations.clips`): `puerta` (hinge, por clic), `reloj`
(manecillas), `bandera`, `balon` (balón de la cancha), `columpios`, `arboles`,
`autobus`, `estudiantes`, `nubes`. Todos los objetos de un clip que deben moverse
juntos (p. ej. carrocería, ventanas y ruedas del bus) llevan el **mismo** `clip`,
`kind`, `pivot` y `params`. Los bucles deben cerrar sin saltos.
