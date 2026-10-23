# Adaptador creation-lab → rigging

22 de octubre de 2026. Implementación y recorrido real aprobados. El alcance
es recibir geometría estática revisada, ejecutar UniRig y devolver un candidato
en su escala original, con apariencia y procedencia verificadas. La calidad de
deformación del rig nuevo todavía requiere revisión.

## Uso

Desde la raíz de `3d-assets`, en WSL:

```bash
python3 lab/lab.py ingest --candidate creation-lab/.local/runs/<handoff>/candidate.json
python3 lab/lab.py rig --candidate lab/.local/runs/<ingest>/creation-prepared.json --stage all
```

`ingest` imprime la ruta `preparedManifest` del segundo comando. En Windows
puede usarse `.\lab\lab.cmd` con los mismos argumentos y rutas WSL. Los
[detalles del contrato](../../creation-lab/docs/INTEGRATION.md) describen las
verificaciones de entrada y la separación del corpus humano/cuadrúpedo.

## Recorrido ejecutado

- Fuente: canario original de tres bloques, autor GuateGeeks, CC0-1.0; no es
  el robot de producción ni una prueba de calidad anatómica.
- Handoff: `creation-lab/.local/runs/20261022T215851655676Z-dc714b4214`.
- Ingest final: `lab/.local/runs/20261022T222159Z-31c05d61`, `success`.
- Rig final: `lab/.local/runs/20261022T222206Z-91fd94f9`, `success`, 342.604 s
  observados para sus diez etapas. Este tiempo incluye verificar checkpoints;
  no es un benchmark de velocidad.
- Salida: [restored.glb](../.local/runs/20261022T222206Z-91fd94f9/restored/restored.glb).
- [Informe de ejecución](../.local/runs/20261022T222206Z-91fd94f9/run.json) y
  [restauración](../.local/runs/20261022T222206Z-91fd94f9/restoration-report.json).

UniRig generó el esqueleto, usó ese mismo archivo para calcular pesos y fusionó
el resultado con la malla preparada. El adaptador aplicó después la inversa
registrada a las raíces del conjunto malla/armature. Las fuentes, la entrega
revisada y los scripts ejecutados están copiados y hashados en runs propios.
La fuente `.blend` 5.2 se conserva sin abrirla en Blender 4.2; el intercambio
entre versiones usa GLB.

| Comprobación | Resultado |
| --- | --- |
| Cadena de QA y procedencia | PASS; tres runs originales hash-bound y copiados |
| Preparación | 7 comprobaciones aprobadas, dimensión mayor normalizada a 2 m |
| Restauración | 9 comprobaciones aprobadas; geometría, UV, normales, materiales y pesos |
| Dimensiones finales XYZ | 0.1800000295 × 0.1900000349 × 0.3000000420 m |
| Diferencia dimensional máxima | 3.73 × 10^-8 m respecto de la fuente |
| Geometría y materiales | 132 triángulos, 288 vértices, 2 materiales |
| Rig | 1 skin, 4 joints, 288/288 vértices con pesos, 0 clips |
| Reimportación en proceso nuevo | PASS en Blender Python 4.2.0 |
| Skinning según matrices glTF | PASS independiente; escala física confirmada sin usar la matriz del nodo de malla |
| Formato Khronos | 0 errores, 1 advertencia de jerarquía |
| Comparación visual en reposo | PASS; ambas imágenes abiertas y comparadas, Blender 5.2.3 LTS / Cycles CPU |
| Suite del laboratorio | 26 tests PASS, incluidos 5 tests reales de Blender CPU |
| Regresión de creation-lab | 10 tests PASS; 2 tests nativos opt-in no repetidos en este corte |
| Trabajo previo preservado | 20 archivos de corpus, galería, informes y entorno con hashes idénticos |
| Catálogo y sitio | Verificación final aprobada para 342 modelos, licencias, miniaturas e inventario publicable |

SHA-256 fuente GLB:
`46d923d856963f03034e7ef3ec9e7af41631dfd22657e661132fc4eb847a3e5e`.
SHA-256 GLB restaurado:
`c37ab87e5b7713b69fda9cd66d08a9cf8da8d9bf177733ad9f29d72347c51444`.

La evidencia adicional está en
`creation-lab/.local/adapter-validation-20261022/`: `fresh-clean-inspection.json`,
`gltf-validation.json`, `visual-review.json`, `preserved-final.json` y
`renders-clean/`. Los primeros probes `fresh-inspection.json` y `renders/`
incluyeron geometría auxiliar que el importador crea para mostrar huesos;
se conservan como diagnóstico. La evidencia final desactiva esa opción con
`disable_bone_shape=True`; el GLB de salida nunca incluyó esa geometría.

## Cobertura y límites

Los tests CPU incluyen un modelo de 0.30 m con dos mallas, jerarquía,
transformaciones no identidad, dos materiales, UV, textura y rig determinista.
Comprueban preparación y restauración sin cambiar el original. Rechazan mallas
sin pesos, UV alteradas, material cambiado, matriz inversa falsa, conexiones
de texturas intercambiadas y cambios flat/smooth de normales. Otros tests
rechazan referencias fuera del ámbito, symlinks, hashes alterados, evidencia
visual ausente y metadatos preparados que contradigan la fuente aprobada.

La revisión independiente cerró los hallazgos de referencias preparadas,
vínculos de geometría y conservación de apariencia. Recalculó hashes,
artefactos, pesos y coordenadas glTF del resultado real.

La advertencia `NODE_SKINNED_MESH_NON_ROOT` proviene de la jerarquía exportada
por UniRig. El cálculo independiente de `jointWorld × inverseBind × POSITION`
confirma la escala de este archivo en reposo. Esto no aprueba animaciones,
deformaciones ni todos los consumidores posibles: normalizar la jerarquía
del derivado final pertenece al trabajo de revisión y empaquetado.

Los candidatos no se añaden automáticamente a la galería, al catálogo ni a
paquetes. La interfaz de revisión existente conserva sus mapas anatómicos
humano/cuadrúpedo. Para un modelo nuevo hay que definir su revisión, comprobar
deformaciones y después crear los clips.
