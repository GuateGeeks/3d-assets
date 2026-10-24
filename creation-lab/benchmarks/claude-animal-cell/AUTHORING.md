# Contrato de autoría · célula animal (benchmark Claude v1)

Este texto es idéntico para todas las réplicas. Eres autor/a de **una** réplica.
Escribes un generador Python para Blender; el coordinador lo ejecuta con el worker
común, renderiza y lo envía a una revisión ciega. No ejecutas Blender.

## Encargo

Modelo 3D educativo de una célula animal para secundaria, con las trece estructuras
y etiquetas en español del [brief](brief.json). Léelo completo: partes, funciones,
`biologicalChecks`, `blockoutChecks`, presupuestos, escala y contrato geométrico.

Restricciones duras (medidas sobre vértices reales tras construir):

- Dimensión mayor 0.30 m con tolerancia relativa 0.02 (0.294–0.306 m). Una esfera
  recortada con anillos discretos puede no alcanzar su radio analítico: calcula la
  composición con los límites reales de tus vértices.
- Hasta 45 000 triángulos, 24 materiales, 350 objetos de malla y GLB de 8 MiB.
- Z arriba, frente -Y, aproximadamente centrado en el origen. La envoltura se abre
  por arriba y hacia el frente para mostrar el interior desde la cámara común
  (0.45, -0.60, 0.55) mirando al origen. Nada de esferas opacas que oculten partes.
- Triángulos no degenerados (doble área ≥ 1e-14 m²), sin modificadores pendientes.

## Contrato del generador

El archivo define `build()` sin argumentos y devuelve:

```python
{"title": "...", "design_notes": ["..."],
 "parts": {"membrana": {"label_position": [x, y, z]}, ...}}  # las 13 IDs, metros Blender
```

- Cada malla final lleva `obj["part_id"]` con una ID del brief; las trece IDs deben
  tener al menos una malla. Solo objetos `MESH` en la escena.
- Materiales Principled (usa `components.material`). Sin luces, cámaras, texto 3D,
  exportación, guardado ni E/S de archivos: el worker lo hace.
- Imports permitidos: `bpy`, `math`, `random`, `mathutils`, `components`. El worker
  llama `random.seed(brief.seed)` antes de `build()`.
- `label_position` debe quedar sobre o junto a la estructura visible que etiqueta.

## Biblioteca compartida

Puedes leer y usar `creation-lab/components/` (README, `geometry.py`, `blender.py`),
`creation-lab/components/demo-brief.json` y `creation-lab/examples/component-demo.py`.
La biblioteca es común a todas las réplicas: el experimento mide creación asistida
por componentes, no generación desde cero. `mesh_object()` crea un objeto por
`MeshData`; para muchas piezas pequeñas (ribosomas, vesículas) combina varias
`MeshData` en una sola malla para respetar el límite de objetos.

Puedes leer, sin modificarlos, el worker `creation-lab/scripts/iteration_worker.py`
y la medición `lab/scripts/creation_geometry.py` para entender las comprobaciones.

## Etapas

1. **Blockout**: envoltura abierta, núcleo y volúmenes distinguibles de las trece
   partes en su disposición. Se revisa visibilidad y relaciones, no el detalle.
2. **Detalle** (solo tras aprobar el blockout): cisternas aplanadas; ribosomas
   anclados al RER (usa los anclajes de superficie de la biblioteca) y algunos libres;
   REL tubular sin ribosomas; mitocondrias con crestas interiores visibles en una
   abierta; núcleo con envoltura parcial y poros sugeridos y nucléolo; dos centríolos
   aproximadamente perpendiculares; Golgi curvo con vesículas; citoesqueleto escaso.
   Conserva `part_id` y anclajes de etiquetas.

Hay **dos correcciones totales** para toda tu sesión (blockout + detalle), además del
primer blockout y del primer detalle. Cada corrección recibe un mensaje con la vista,
el defecto y el cambio requerido, o el log técnico. Escribe cada versión en un archivo
nuevo; no sobrescribas versiones anteriores.

## Reglas del contexto

- Escribe solo dentro de tu carpeta de trabajo (te la indica el coordinador).
- Puedes ejecutar `python3` sin Blender para probar geometría de `components`
  (por ejemplo `validate_mesh`, límites y conteos). **No ejecutes Blender**, no
  renderices ni intentes ver resultados por otra vía: no hay intentos ocultos.
- No leas otros generadores, evaluaciones o resultados: nada bajo
  `creation-lab/benchmarks/animal-cell-20261022/`, `creation-lab/.local/` fuera de tu
  carpeta, otras carpetas `authors/`, `sessions/`, `blind/`, `coordinator/`, ni el
  historial de git. No uses web, skills, MCP ni subagentes (herramienta `Agent`).
- Tras una corrección puedes abrir los renders de tu propia réplica que el
  coordinador copie en tu carpeta `feedback/`.
- Al terminar cada etapa, entrega tu informe con la herramienta `SubagentHandback`:
  ruta del archivo, `sha256sum`, qué construiste, conteos estimados y riesgos.

Las transcripciones del runtime se auditan después: lecturas fuera de este contrato,
subagentes o cambios de modelo marcan la réplica como contaminada.
