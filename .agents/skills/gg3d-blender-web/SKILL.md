---
name: gg3d-blender-web
description: Exporta a Blender los personajes procedurales del cotizador (alumnos Meshy de primaria, rig rígido de 12 huesos) con sus poses y animaciones, y devuelve el retoque a los módulos de datos del cotizador con procedencia. Usar para retocar geometría, colores, pivotes o clips de animación del campus desde Blender.
---

# Personajes del campus en Blender

Puente en [`procedural-web/`](../../../procedural-web/README.md) entre el cotizador (Three.js,
color por cara, rig rígido) y Blender. Para cómo se generan y verifican esos modelos lee
[gg3d-procedural-web](../gg3d-procedural-web/SKILL.md); este skill cubre el retoque manual.

## Ciclo

1. **Diagnóstico.** `python3 procedural-web/pw.py doctor`. Resuelve Blender, `bpy`, Node y el cotizador desde opciones, variables o `procedural-web/.local/config.json`; nunca copies rutas de otro equipo.
2. **Exportar.** `pw.py export --model nino|nina` deja un run nuevo con el `.blend`, `model.json`, `clips.json` y el recibo. Abre el `.blend` con el Blender configurado; desde WSL el comando imprime la ruta de Windows.
3. **Retocar.** Respeta el contrato del README:
   - nombres de huesos, objetos, colecciones y materiales `gg.<clase>`;
   - un grupo de vértices por pieza;
   - 320 triángulos por alumno con sombra;
   - capas a ≥ 0.006 H y calcomanías a 0.0075 H;
   - rotaciones en modo `ZXY`.
4. **Revisar.** `pw.py import --model … --blend …` sin `--apply` lista piezas, pivotes y clips cambiados.
5. **Aplicar.** `--apply` escribe el módulo del modelo, con `SOURCE.edited` y el SHA256 del `.blend`, y `pose-clips-data.js`. Después, en el cotizador:
   - reconstruye los bundles;
   - corre `npm test`, `check:people` y `check:paper`;
   - abre las capturas antes de dictaminar.

Para un personaje propio ya riggeado (una malla, esqueleto tipo Mixamo), `pw.py adopt` lo convierte
en el modelo sin reducir triángulos: cada vértice sigue a su hueso de más peso, y los triángulos
entre huesos se estiran. Informa el total y su efecto en el presupuesto antes de aplicar; subir un
límite lo decide la persona responsable, con la medición del campus en GPU.

Usa para exportar e importar la **misma versión** de Blender con la que se edita: un `.blend` de
5.x puede no abrir en 4.2. El `bpy` 4.2 del entorno de UniRig sirve para pruebas automáticas
(`--engine bpy`), no para leer archivos guardados por una versión más nueva.

## Animaciones

Las poses del cotizador son funciones. El puente las muestrea como acciones:
- las periódicas, un ciclo a 24 fps;
- `talk`, `vr` y `grab`, 62.8 s a 12 fps.

Al importar se conservan solo los clips que difieren de la función original.

El campus usa un clip en lugar de la función solo para los argumentos con que se muestreó. El
tiempo y el desfase `k` cuentan como tiempo; con otros argumentos sigue mandando la función. Una
pose sentada se edita con la cadera de pie: el cotizador la baja a la silla.

## Lecciones de Blender

- **bpy como módulo.** `bmesh` se importa después de `bpy`. `bpy` 4.2 no lee archivos guardados por 5.x.
- **Blender de Windows desde WSL.** Recibe rutas de Windows (`wslpath -w`) y escribe bien en `\\wsl.localhost\…`. Para abrir la interfaz, lánzalo desacoplado (`setsid nohup … &`).
- **Acciones.** En 4.4+ son por capas y ranuras. Lee los clips evaluando cada fotograma (`frame_set` y `matrix_basis`), no recorriendo las curvas. `keyframe_insert` funciona igual en ambas versiones, y la interpolación lineal se fija en preferencias antes de insertar.
- **Rotaciones.** El orden `YXZ` de three.js (R = Ry·Rx·Rz) es el modo `ZXY` de Blender. Con huesos hacia arriba y roll 0, los ejes locales coinciden.
- **Clips.** Importa solo los que difieren de las funciones originales: una ida y vuelta sin cambios debe dar identidad.

## Verificación

- `python3 -m unittest discover -s procedural-web/tests` prueba el formato de los módulos.
- Con `GG_TEST_BPY` y `GG_COTIZADOR` también hace la ida y vuelta, que debe ser identidad sin ediciones, y compara las articulaciones de three.js contra las de Blender.
- Un run de importación conserva `read.json` y el recibo. No sobrescribas runs anteriores.

Separa el resultado técnico (importación y pruebas) del visual (imágenes abiertas).
