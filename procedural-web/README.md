# Puente Blender para personajes procedurales web

Retoca en Blender los personajes del cotizador (alumnos de primaria Meshy, campus Three.js con
rig rígido de 12 huesos) y sus poses y animaciones, y devuelve el resultado a los módulos de
datos del cotizador. El cotizador sigue siendo la fuente que se publica: este puente solo
traduce en ambos sentidos y deja recibo de cada paso.

| Paso | Comando | Resultado |
|---|---|---|
| Diagnóstico | `python3 procedural-web/pw.py doctor` | Blender, `bpy`, Node y los modelos del cotizador encontrados. |
| Exportar | `python3 procedural-web/pw.py export --model nino` | `.local/runs/<fecha>-export-nino/nino.blend` y su recibo. |
| Retocar | Abrir el `.blend` en Blender | Geometría, colores, pivotes y acciones. |
| Revisar | `python3 procedural-web/pw.py import --model nino --blend <archivo>` | Lista de cambios, sin escribir nada. |
| Aplicar | La misma orden con `--apply` | Módulo del modelo y clips del cotizador actualizados. |
| Adoptar | `python3 procedural-web/pw.py adopt --model nina --blend <personaje.blend> [--apply]` | Un personaje riggeado propio (una malla, esqueleto tipo Mixamo) pasa a ser el modelo, conservando sus triángulos. |

Modelos: `nino` y `nina` (los que existan en `asesor/lab/paper/meshy/primaria-meshy*-data.js`).

## Configuración

Copia `config.example.json` a `procedural-web/.local/config.json` (ignorado por Git) o usa
opciones (`--cotizador`, `--blender`, `--bpy`, `--node`) o variables (`GG_COTIZADOR`,
`GG_BLENDER`, `GG_BPY`, `GG_NODE`). Las rutas son de cada equipo; no se versionan.

- `blender`: el ejecutable con el que se edita. Desde WSL vale un `blender.exe` de Windows: el
  puente le pasa rutas de Windows (`wslpath -w`). Exporta e importa con la **misma versión** con
  la que se edita: un `.blend` guardado por una versión nueva puede no abrir en una anterior.
- `bpy`: un Python con el módulo `bpy` (por ejemplo el entorno de UniRig del laboratorio). Sirve
  para pruebas sin interfaz: `--engine bpy`.
- `node`: el cotizador muestrea sus poses con Node (`node/sample_poses.mjs`).

## Qué contiene el .blend

- **Ejes y escala.** Three.js (Y arriba, +Z frente) → Blender (Z arriba, −Y frente): `(x, y, z) → (x, −z, y)`. Unidades de escena: H = 0.78 en primaria.
- **Armature `GG.<modelo>`.** Los 12 huesos del proyecto (`root`, `hips`, `torso`, `head`, `armL/R`, `foreL/R`, `legL/R`, `shinL/R`):
  - cada hueso nace en su pivote y apunta hacia arriba con roll 0, así que sus ejes locales son los de three.js;
  - el modo de rotación es `ZXY`, que equivale al `YXZ` de three.js;
  - las propiedades `gg_*` guardan el modelo, H, los puntos de referencia y la procedencia.
- **Colecciones `bag` y `plain`.** Son las variantes de pie (con mochila) y sentada; `plain` empieza oculta. Cada pieza es un objeto (`bag.head`, `plain.torso`, ...) con:
  - un solo grupo de vértices, con el nombre de su hueso y peso 1;
  - un modificador de armature.
- **Materiales `gg.<clase>`.** Son las clases de color: `skin`, `hair`, `vest`, `shirt`, `pants`, `shoe`, `bag` y `dark`. El campus recolorea cada clase según el alumno (piel, cabello, chaleco, mochila, zapatos), así que el material elige la clase, no el tono final.
- **Acciones `clip.<pose>`.**
  - Hay una por pose de `poses.json`, muestreada de `POSES` del cotizador.
  - Las claves son lineales y empiezan en el fotograma 1; un clip estático tiene un solo fotograma.
  - Las poses periódicas cubren un ciclo a 24 fps.
  - `talk`, `vr` y `grab` no son periódicas: cubren 62.8 s a 12 fps.
  - `hips` solo lleva la elevación (`location.y`).
  - Los metadatos van en `action["gg_clip"]`.

## Reglas al retocar

- **Nombres.** No renombres huesos, objetos, colecciones ni materiales: son el contrato con el cotizador.
- **Una pieza, un hueso.** Si una pieza debe seguir a otro hueso, cambia su grupo de vértices.
  - Puedes duplicar un objeto para añadir una pieza: `bag.<id-nuevo>`, con `gg_part` y `gg_variant` actualizados.
- **Presupuesto.** Cada alumno con su sombra cabe en **320 triángulos**, es decir, unos 313 de geometría. Los polígonos se triangulan al importar. Comprueba después con `npm run check:people` en el cotizador.
- **Capas y calcomanías.**
  - Las capas superpuestas de distinto color van a ≥ 0.006 H a lo largo de su normal.
  - Ojos y sonrisa (`eyeL`, `eyeR`, `smile`, material `gg.dark`) flotan a 0.0075 H de la cara.
- **Pivotes.** Mover un hueso en modo edición mueve el pivote. La cadera, la rodilla, el codo, el hombro y el cuello del cotizador salen del rig importado; el resto de puntos de referencia se mide de nuevo.
- **Animaciones.**
  - Edita las claves de las acciones `clip.*`. La duración en fotogramas de una pose periódica puede cambiar: el fps se conserva.
  - Un clip que vuelve a coincidir con la función original deja de importarse.
  - Las poses estáticas se ven en el fotograma 1.
  - Una pose sentada se ve con la cadera a la altura de pie: el cotizador la asienta en la silla.

## Adoptar un personaje riggeado

`adopt` toma un `.blend` con una malla riggeada y su armature (por ejemplo un modelo de Meshy
riggeado con Mixamo, con textura) y lo convierte en el módulo del modelo **sin reducir sus
triángulos**:

- **Copia:** el archivo se copia al run; el original nunca se abre en su sitio.
- **Huesos:** `mixamo-map.json` reduce los huesos a los 12 del campus. Cada vértice sigue al de más peso; los triángulos entre dos huesos se estiran en la articulación (`vertexBones`). Chaleco y mochila siguen al torso.
- **Colores:** cada cara toma su color de la textura y se clasifica por prototipos (`PROTO`), con reglas de posición: zapatos abajo, coletas junto a la cabeza.
- **Cara:** ojos y sonrisa pintados vuelven como calcomanías.
- **Ajustes de geometría:** se separan las capas a menos de 0.006 H, la suela se curva en mecedora y la cadera queda a la altura de los muslos.
- **Procedencia:** el módulo guarda el SHA256 del `.blend` (`SOURCE.edited`). Después se retoca con `export` e `import` como cualquier otro.

Revisa el informe sin `--apply`: triángulos por pieza, clases de color y vértices de costura. Si
el modelo pasa del límite por alumno, decide el límite con la persona responsable; `adopt` no
reduce nada.

## Qué escribe `import --apply` en el cotizador

- **Modelo:** `asesor/lab/paper/meshy/primaria-meshy*-data.js`, solo si cambió. `SOURCE.edited` registra la herramienta, el `.blend`, su SHA256, la fecha y la versión de Blender. Desde entonces el módulo es la fuente: `tools/meshy-import.mjs` no lo regenera desde el GLB sin `--force`, y la prueba de sincronía valida la procedencia en vez del GLB.
- **Clips:** `asesor/lab/paper/pose-clips-data.js`, con los clips que difieren de las funciones de pose. El campus los usa en lugar de la función para los argumentos con que se muestrearon: el tiempo, y el desfase `k` sumado al tiempo. Con otros argumentos sigue usando la función.

Después, en el cotizador: `npm run build`, `npm run build:inspector`, `npm test`,
`npm run check:people -- <carpeta-nueva>` y `npm run check:paper -- <carpeta-nueva>`. Revisa las
imágenes del inspector o del campus antes de dar por bueno un retoque.

## Pruebas

```bash
python3 -m unittest discover -s procedural-web/tests -v
GG_TEST_BPY=<python con bpy> GG_COTIZADOR=<cotizador> GG_NODE=<node> python3 -m unittest discover -s procedural-web/tests -v
```

La segunda forma exporta e importa ambos modelos sin cambios y debe dar identidad. También
compara las articulaciones de tres poses en three.js con las del armature en Blender, con una
tolerancia de 0.0001.

## Integración y evidencia conservada

Desde el corte del 26 de octubre de 2026, este puente forma parte de `3d-assets`;
no requiere trabajar en la carpeta hermana `3d-assets-blender`. El código, las
pruebas y el ejemplo de configuración se versionan. La configuración y los runs
están en `.local/`, ignorados por Git y excluidos de la publicación.

En el equipo de integración se conservaron los originales del área Blender y se
copiaron sus 202 archivos locales al repositorio principal, verificando SHA-256.
Los recibos retienen rutas y hashes históricos: no se reescriben como si los runs
se hubieran ejecutado aquí. Los runs de validación nuevos quedan separados.
Un clon nuevo debe configurar sus rutas y producir evidencia propia; consultar
[SETUP](../SETUP.md#puente-blender-para-el-cotizador) y el
[informe de integración](../docs/integration-20261026.json).
