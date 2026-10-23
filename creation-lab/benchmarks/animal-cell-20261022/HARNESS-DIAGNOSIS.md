# Diagnóstico compartido de reimportación

La primera corrida B `20261022T224930Z-c5b4b814` permanece intacta. En Blender
5.2.3 LTS, sus 22,224 triángulos, posiciones, winding, UV y materiales coinciden
tras reimportación; cambian normales de sombreado. La geometría contiene 1,216
triángulos de área casi cero (área doble menor que 1e-14 m²), conservados también
por el GLB. El dot mínimo observado entre normales fue 0.8735229.

El diagnóstico de los accessors binarios del GLB confirma que el exportador sí
conservó las normales originales. El cambio aparece al reconstruir la malla en
el importador de Blender. Las diferencias observadas incluyen los polos
coincidentes de las esferas procedurales. El gate completo detecta un cambio
real de shading; no es una discrepancia de orden de triángulos o de nombres.

Se probaron dos estrategias comunes sin modificar el generador:

- Congelar normales de esquina: conserva la fuente, pero la reimportación falla.
- Triangular y conservar normales personalizadas: la reimportación pasa, pero
  cambia el shading original. También se probó la triangulación exacta de
  `loop_triangles`, con el mismo límite de conservación de normales.

Estas transformaciones no se adoptaron. El harness no elimina degenerados, no
repara geometría y conserva la comparación estricta de superficies, winding,
materiales, UV y normales. El fallo inicial puede alimentar la única reparación
técnica autorizada; la composición visual se evalúa por separado.

Ampliación posterior: A también falla sólo en normales pese a tener cero
triángulos degenerados (mínimo dot 0.9999794066, unos 0.37 grados). Los degenerados
de B son un defecto geométrico demostrado, pero no la causa única del problema
de importación. En A también se confirmó que el GLB conserva las normales crudas
correctas. Las pruebas NORMALS/smooth y adaptación desde accessors no encontraron
una solución que pase el gate completo. `HARNESS-NOTES.md` conserva los resultados
y hashes adicionales; el harness permaneció congelado durante esas pruebas.

El worker registra ahora `source-quality.json` y, ante un fallo de reimportación,
diagnósticos que aíslan normales del resto de la superficie. Esas comparaciones
parciales son exclusivamente diagnósticas y nunca aprueban el gate técnico.
El runner pasa `--python-exit-code 1` a todos los procesos Blender para que una
excepción Python no termine como ejecución exitosa.

Evidencia local, fuera de la corrida inmutable:

- `creation-lab/.local/benchmarks/animal-cell-20261022/diagnosis-initial-B.json`
- `creation-lab/.local/benchmarks/animal-cell-20261022/raw-normal-comparison-B.json`
- `creation-lab/.local/benchmarks/animal-cell-20261022/normal-freeze-probe/result.json`
- `creation-lab/.local/benchmarks/animal-cell-20261022/triangulated-normal-freeze-probe/result.json`
- `creation-lab/.local/benchmarks/animal-cell-20261022/exact-triangulated-normal-probe/result.json`

`diagnose.py`, `raw_normals_probe.py` y `normals_probe.py` son utilidades de
diagnóstico explícitas. No forman parte de la preparación de las seis condiciones.
