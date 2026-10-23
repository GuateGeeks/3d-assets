# Diagnóstico e instalación de UniRig

Fecha: 22 de octubre de 2026. Estado: **instalación e inferencia del ejemplo oficial verificadas** en la RTX 3060 Ti de 8 GB. El laboratorio se implementa íntegramente en `3d-assets`.

## Resultado del primer corte

Se implementaron `doctor`, `setup`, `verify` y `smoke`, el lanzador Windows/WSL, el entorno aislado, la resolución de dependencias fijada, caché de checkpoints, comprobaciones CUDA y registro de ejecuciones. El instalador se repitió desde el lock en 2,75 segundos, conservando las versiones y el checkout oficial.

- Python 3.11.14; PyTorch 2.5.1+cu124; runtime CUDA 12.4; Blender Python 4.2.0.
- Commit de UniRig: `6793c6640ff01c8fb389f3993434124bb43d2933`.
- Revisión de checkpoints: `36842e2b5947e9e60f89275b83208c8e74071c63`; ambos SHA-256 coinciden con los objetos publicados.
- Pruebas de versiones, CUDA, Blender e imports: **8/8**.
- Pruebas sin GPU del laboratorio: **6/6**.
- Prueba negativa: esqueleto sin pesos rechazado con código 1.
- Biblioteca original: **342 modelos y miniaturas**, integridad y rutas verificadas.

## Prueba real de instalación

Ejecución: `20261022T211744Z-7452a5c2`. Resultado: `success`. Semilla: 42. Backend de voxelización: `open3d`.

La generación de esqueleto usa la malla oficial de jirafa. El skinning usa el esqueleto revisado que proporciona upstream; después se fusiona con la malla original. Esta prueba verifica la instalación de ambas etapas y la exportación; no representa una revisión anatómica ni una corrección automática del esqueleto generado.

El recorrido completo tardó **106.329 segundos** con pesos descargados, incluyendo preparación, cargas, conversiones y validación. Es una muestra de instalación, no una mediana del corpus ni tiempo puro de GPU.

| Etapa | Segundos | Pico GPU muestreado en MiB |
| --- | ---: | ---: |
| prepare-smoke | 5.439 | 1689 |
| extract-skeleton | 4.281 | 1690 |
| generate-skeleton | 33.854 | 7318 |
| validate-skeleton | 0.844 | 1615 |
| extract-skin | 4.294 | 1615 |
| generate-skin | 45.927 | 7392 |
| validate-skin | 0.899 | 1676 |
| merge | 9.901 | 1692 |
| validate-glb | 0.839 | 1692 |

Las cifras GPU corresponden al dispositivo completo e incluyen otras aplicaciones. Se muestrean aproximadamente una vez por segundo. El manifiesto también conserva el pico RSS muestreado del proceso principal; no suma workers ni equivale a memoria total del sistema.

## Archivo generado

[GLB de la jirafa](../.local/runs/20261022T211744Z-7452a5c2/workspace/output/model_rigged.glb) · 6682320 bytes · SHA-256 `dbf03ff3ed8d16451580185a8080b299e46af3c1ee5863949bea962d30ea9179`.

Blender vuelve a abrir el archivo y encuentra 2 mallas, 30 huesos y 14885 vértices con pesos. No se encontraron vértices deformables sin asignación ni sumas de pesos fuera de tolerancia. El archivo contiene **0 clips**: la animación forma parte de las fases siguientes.

La [comprobación independiente de Khronos](gltf-validation.json), versión `2.0.0-dev.3.10`, encontró **0 errores y 1 advertencia**. La advertencia señala un nodo con malla skinned que no es raíz; debe revisarse su comportamiento de transformaciones al preparar un paquete final. Hay además tres avisos informativos de coordenadas UV sin uso. La revisión visual permanece pendiente.

Khronos se ejecutó como herramienta independiente de esta sesión. El comando `smoke` automatiza la inspección con Blender; no requiere Node para funcionar.

## Incidencias resueltas y evidencia

Los intentos fallidos conservan sus manifiestos y logs bajo `.local/runs/`. El registro de [incidencias de instalación](installation-issues.json) explica los metadatos de bpy, la descarga Git LFS y las adaptaciones de ejecución. El [manual](../README.md) documenta los comandos y el alcance de cada comprobación.

La prueba que usa `pyrender` falló al inicializar EGL. El perfil de este host usa Open3D, la alternativa admitida por UniRig. Se conservan la configuración efectiva y hashes de sus YAML por ejecución, sin modificar el checkout upstream.

El worker de inspección evita el fallo nativo de finalización de bpy después de cerrar datos y escribir su resultado. Se comprobó tanto una salida válida como el rechazo de un esqueleto sin pesos; el cierre explícito conserva el código real de validación.

## Siguiente corte

Preparar el corpus del proyecto, ejecutar UniRig sobre modelos propios, ampliar la galería para comparar variantes, revisar deformaciones y crear clips. Los derivados revisados y paquetes aún están pendientes. SkinTokens tendrá su evaluación separada. La implementación en Code Studio o Sócrates comenzará después de cerrar el flujo completo de `3d-assets`.
