# Harness animal-cell: diagnóstico del primer fallo B

22 de octubre de 2026. Blender nativo 5.2.3 LTS. El primer run B
`creation-lab/.local/benchmarks/animal-cell-20261022/B/20261022T224930Z-c5b4b814`
se conserva sin cambios. No se ejecutaron las seis condiciones durante esta
depuración ni se editaron generadores o `lab/scripts/creation_geometry.py`.

## Resultado

La comparación completa detecta un cambio real en **normales de sombreado
durante la importación de Blender**. Triangulación, winding, posiciones, UV y
materiales coinciden. Los accessors POSITION/NORMAL binarios del GLB pasan la
comparación completa contra la fuente; las normales reimportadas no la pasan.
El mínimo dot observado entre normales fue 0.8735229, aproximadamente 29 grados.

La fuente y el GLB tienen 22,224 triángulos, incluidos 1,216 de área casi cero
(área doble menor que 1e-14 m²). Los 1,216 contienen una arista colapsada a
menos de 1e-10 m. Son 49 objetos de ocho partes. No fueron eliminados ni soldados.

Congelar normales sin triangular conserva la fuente, pero falla la reimportación.
Triangular y fijar normales hace pasar la reimportación, pero cambia el shading
original, incluso usando exactamente `loop_triangles`. Esas transformaciones se
descartaron. La comparación completa conserva sus tolerancias y todos sus gates.

## Reparación técnica B, acotada para el autor

El helper `sphere()` de `conditions/B/generator.py`, líneas 45–55 de la primera
versión, crea `seg` vértices coincidentes en cada polo (`j=0` y `j=rings`) y luego
crea quads con arista colapsada en ambos extremos. Cada esfera aporta `2*seg`
triángulos degenerados. Es un defecto geométrico confirmado, pero no una causa
única demostrada del cambio de normales: A también falla sin ningún triángulo
degenerado. La reparación sugerida es usar un solo vértice por polo,
anillos interiores y abanicos triangulares orientados en los polos. Conservar
centros, escalas, segmentación interior, materiales, `part_id`, nombres y labels;
no usar esta reparación para cambiar composición o estética.

| Parte | Objetos afectados | Triángulos degenerados |
| --- | ---: | ---: |
| citoplasma | 1 | 72 |
| nucleo | 8 | 220 |
| nucleolo | 1 | 40 |
| ribosomas | 21 | 348 |
| vesiculas | 8 | 204 |
| mitocondrias | 3 | 144 |
| lisosomas | 6 | 156 |
| centrosoma | 1 | 32 |

Objetos concretos: `citoplasma__volumen`; `nucleo__cuerpo`,
`nucleo__lumen_visible`, `nucleo__poro_00..05`; `nucleolo__sin_membrana`;
`ribosomas__libre_00..05`, `ribosomas__rer_00_00..02_04`;
`vesiculas__golgi_00..02`, `vesiculas__libre_00..04`;
`mitocondrias__cuerpo_00..02`; `lisosomas__enzima_00..02`,
`lisosomas__vesicula_00..02`; `centrosoma__matriz`.
El inventario JSON enlazado abajo conserva los 49 nombres individuales.

## Cambios del harness y congelación

- Runner: `--python-exit-code 1` en las tres etapas Blender.
- Worker: `source-quality.json` registra degenerados sin repararlos. Ante fallo,
  `reimport-result.json.diagnostics` aísla las normales del resto de la superficie.
  La comparación parcial es diagnóstica y nunca aprueba el gate.
- No se adoptó ninguna transformación geométrica ni relajación de tolerancias.
- Runner/worker congelados para el batch coordinado por root. Cada run registra
  su snapshot/hash propio; la corrida B original usa el snapshot anterior.

Hashes al congelar:

| Archivo | SHA-256 |
| --- | --- |
| `run.py` | `00304c3e9eb28f9e3c88994da524a8a886999cd3c2065a660ef06e31e0f88596` |
| `worker.py` | `159a934abbf51bd222d60db26ecb9d6399bc2a8d6067d5e3de382b3ad08ab559` |
| `B/20261022T224930Z-c5b4b814/generator.py`, primera versión congelada | `c159a78e81410409401e1cac90ae1e3352f7c8050b9f6a11709f7263e6bd67cd` |

El hash de primera versión viene del snapshot del run, nunca de
`conditions/B/generator.py`, que recibió una reparación en paralelo.

## Diagnóstico adicional A y configuración del importador

El run `A/20261022T225937Z-f8eb57e5` contiene 36,980 triángulos y **cero**
triángulos degenerados. También conserva posiciones, winding, UV y materiales.
Su mínimo dot entre normales fuente/importadas es 0.9999794066, aproximadamente
0.37 grados, frente al umbral común `dot >= 1 - 1e-5` (aproximadamente 0.256
grados). Este fallo permanece visible y no se relajó el umbral.

El importador instalado usa `import_shading=NORMALS` por defecto.
`set_poly_smoothing()` infiere `sharp_face`; después aplica
`normals_split_custom_set_from_vertices()`. Blender almacena `custom_normal`
como `INT16_2D` en dominio CORNER. Es un límite de representación a investigar;
el tipo de almacenamiento por sí solo no prueba toda la causa.

Pruebas en A, sin modificar fuente, GLB ni harness:

- NORMALS normal: FAIL completo.
- `polygon.use_smooth=True` después de importar: FAIL completo.
- Smooth antes de aplicar las normales personalizadas del importador: FAIL.
- Adaptador desde POSITION/NORMAL del GLB con vértices independientes por
  triángulo y normales de esquina: FAIL completo. No usa datos del QA esperado
  como entrada de adaptación y no cambia el GLB. No se adoptó.

La comprobación de accessors confirma también en A
`authoredVsRawExport=PASS` y `rawExportVsImported=FAIL`: el GLB conserva las
normales correctas. No se encontró una configuración que mantenga todas ellas
dentro del umbral. El fallo técnico se documenta como incompatibilidad de
representación/importación Blender bajo este gate estricto, separado de la
calidad artística del generador. El coordinador decidió usar una reparación
técnica del autor A, limitada a triangulación/normales, en un intento nuevo.

Runner y worker permanecieron congelados durante estas pruebas adicionales.

## Evidencia

Los siguientes paths son relativos a
`creation-lab/.local/benchmarks/animal-cell-20261022/`:

| Archivo | SHA-256 |
| --- | --- |
| `B/20261022T224930Z-c5b4b814/manifest.json` | `0fb4120a66a2a171f979e3fd465a3c8103e8380872dfcfcaae9ae92b19987fc3` |
| `diagnosis-initial-B.json` | `351b371505574f4140772cc6326bd63be3eaf7ce4cbd88bb58ce86ae152566e3` |
| `raw-normal-comparison-B.json` | `b6658038711d413564039743279d0e8f19cc5dd60502fdbc019bee46c0b18c7b` |
| `normal-freeze-probe/result.json` | `fb5ef585a4508ef2e6fd066a0fd9f3e62bcfa1a21dd2dbbdbe5d4b8a5bc17242` |
| `triangulated-normal-freeze-probe/result.json` | `c864309344baab1ea1ef4664e1092f84d4c38b8acfa07125b1b9ee32d5bfbe6b` |
| `exact-triangulated-normal-probe/result.json` | `c864309344baab1ea1ef4664e1092f84d4c38b8acfa07125b1b9ee32d5bfbe6b` |
| `degenerate-object-inventory-B.json` | `c9af06a61697266cc71d9e72b29bb3852eb1cc0f95daa482f1270a4a6c600034` |
| `diagnosis-initial-A.json` | `f149e5dcd70187359cacf262363dc2747551be85a6f37dcf198e3d9f48723dc5` |
| `raw-normal-comparison-A.json` | `3bf29dea5713e18ec5c154acf132dfbf27c52de1a950cf707c9afa54223e96a8` |
| `import-api-options-A.json` | `723d84d3b9d12d881b20ce19fa4c10346fa1cfa2002b18630b454ed58bd35c4e` |
| `raw-normal-adapter-A.json` | `98d8cb1a5ab71411a7543b03245a6256d30b73a0da3cec0ebda2592e9160fd4e` |

Fuente `.blend` original:
`c59318d808f1078e924bb96d6daefde5b28eecf192e8f67c11e06d3d849d8d2d`.
Las utilidades `diagnose.py`, `raw_normals_probe.py`, `normals_probe.py` y
`object_quality_probe.py` leen esa evidencia y escriben resultados separados.
Los probes no forman parte del runner de las condiciones.
