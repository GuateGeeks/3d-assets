# Reconstrucción del alumno de primaria R2

Autoridad: `references/GuateGeeks_Primaria_Piezas_R2/GuateGeeks_Primaria_Piezas_R2/imagenes/00-personaje-completo.png`. El ZIP R3 se conserva como comparación fallida, nunca como autoridad de proporciones. La imagen actual manda sobre contratos JSON históricos. Modelo de estudio; sin integración a campus, catálogo o producción.

Brief congelado por iterate.py: 1 m de altura convencional, 5000 triángulos, 8 materiales, 45 mallas, GLB 2 MiB. No es escala física comprobada del papercraft. Dos correcciones totales entre blockout y detalle, aparte de las primeras ejecuciones. La referencia y la reconstrucción están autorizadas; el detalle requiere revisión independiente del blockout real.

## Contenido versionado

Versión ligera (2026-10-25): se versionan docs, scripts, receta, revisiones, la entrega
(`delivery/`), el comparador (`inspector/`) y las láminas de apoyo (`support/`). Quedan
locales, listados en `.gitignore`, los paquetes de referencia del usuario (`references/`,
redistribución no verificada), la sesión completa (`session/`), los renders
(`presentation-v1/`, `presentation-v2/`, `completion-run/`), `environment-runs/` y el
paquete `GuateGeeks_Primaria_R4.zip`. Sus hashes siguen en los manifiestos versionados.

## Entorno comprobado

Blender nativo `D:/SteamLibrary/steamapps/common/Blender/blender.exe`: 5.2.3 LTS, hash e13b728c6880. Python nativo disponible en `D:/SteamLibrary/steamapps/common/Blender/5.2/python/bin/python.exe`: 3.13.13. El alias `python` de Windows Store no funciona, `py` no está instalado, WSL está denegado dentro del sandbox.

Desde la raíz de `3d-assets`, PowerShell admite rutas UNC directamente con este Python. No requiere unidad mapeada ni cambios globales:

```powershell
$py3d = 'D:/SteamLibrary/steamapps/common/Blender/5.2/python/bin/python.exe'
$exp3d = 'creation-lab/experiments/primaria-reconstruction-20261025'
& $py3d creation-lab/iterate.py --help
& $py3d creation-lab/create.py doctor --blender 'D:/SteamLibrary/steamapps/common/Blender/blender.exe' --runs-root "$exp3d/environment-runs"
& $py3d creation-lab/iterate.py status --session "$exp3d/session"
```

El primer doctor devolvió acceso denegado 0xC0000022 al iniciar Blender. Un reintento autorizado fuera del sandbox pasó el probe real. Conservar ambos en `environment-runs`. Los renders reales usan Cycles CPU; una sola carga pesada simultánea. No usar launcher WSL con Blender Windows.

## Autoría y revisión

Propietario de generadores y .blend de autor: contexto `/root/student_pipeline`. Coordinación `/root`; revisión en contexto independiente. Modelo solicitado gpt-6.1-sol, esfuerzo medium. Identificador backend/esfuerzo real no expuestos al agente: `runtime-evidence.json` los conserva como null, sin afirmar atestación. Los parámetros CLI son declaraciones del coordinador, no recibos del backend.

`generator-blockout-v1.py` implementa `build()` sin E/S, cámaras ni render. El worker común conserva fuente, renderiza seis imágenes, reabre el .blend, exporta/reimporta GLB y verifica técnica. Abrir las seis imágenes antes de registrar review, y comparar con R2. Técnica, visual, contenido y procedencia son gates separados.

No publicar ni commitear. Derechos: reconstrucción interna autorizada por usuario; redistribución no verificada independientemente.

## Estado inicial Git y primer blockout

Git por UNC requiere `git -c safe.directory=//wsl.localhost/Ubuntu/home/adawolfs/projects/makecode/3d-assets -C 3d-assets status --short` para este host; no se cambió configuración global. El estado previo mostraba cambios ajenos en skills benchmark, benchmark célula A/D/reviews/results, ITERATIVE-WORKFLOW, STATUS, iterate.py y tests, además de carpetas benchmark Claude y experiments. Se conservaron íntegros. Git emitió aviso `.git/sequencer/todo: Function not implemented` bajo UNC; no se tocó estado de secuenciador.

Run `001-e4adb71fe836`: técnica PASS, 724 triángulos, 7 materiales, 29 mallas, GLB 66068 bytes. Reapertura y reimportación PASS con triángulos orientados, UV, materiales y límites conservados. Presentación visual FAIL pendiente de registro independiente: los vértices z0..1 dejaron la cabeza fuera del encuadre común que apunta al origen. Se conserva el intento. `generator-blockout-v2.py` centra geometría y labels en z[-.5,.5]; consume primera corrección al ejecutarse. No cambia la escala ni las proporciones.

## Runs conservados y revisión independiente

- `001-e4adb71fe836`: blockout inicial, técnica PASS; revisión independiente FAIL visual/contenido por recorte de cámara.
- `002-a580406555e8`: corrección 1, centrado de geometría; técnica PASS; revisión independiente FAIL por volúmenes extruidos de cabeza/pelo y tirantes rígidos.
- `003-b86b551b74f2`: corrección 2, casco cerrado volumétrico, mejillas y tirantes por secciones; técnica PASS y revisión independiente PASS solo para scope blockout. Defectos de superficie y detalle explícitos en review.
- `004-05247a80c4f0`: primera ejecución detail, técnica PASS; 1738 triángulos, 8 materiales, 30 mallas. Pantalón sin frente coplanar, cabeza frontal plana con mejillas facetadas, pelo posterior recogido, ojos ovalados y sonrisa curva, colores profundos y zapatos en cuña. Revisión final independiente pendiente al escribir este apartado.

Dos correcciones consumidas; no quedan reparaciones de sesión. No se modificaron runs cerrados. Fuente final y export están en `session/runs/004-05247a80c4f0/source.blend` y `asset.glb`. La revisión final se conserva en archivo externo `review-detail-v1.json` y se sella mediante el CLI cuando el revisor la completa. Las presentaciones adicionales deben escribirse fuera del run, sin guardar cambios en la fuente.

## Hallazgo suplementario posterior: contacto pantalón / zapatos FAIL

Root detectó en la presentación frontal ortográfica que los bajos flotan sobre la cuña de los zapatos. Confirmado por coordenadas del generador: en y=-0.052m, la superficie superior del zapato queda en z=0.06712426m mientras el bajo del pantalón está en z=0.082..0.089m. Hay una separación real de 0.01487574..0.02187574m, además de la sombra. Fue introducida por la cuña del primer detalle y no se detectó en la revisión de alcance estrecho.

`session/reviews/004-05247a80c4f0.json` conserva el PASS de aquella revisión sin reescribirlo. El dictamen posterior está en `supplemental-contact-failure.json`: FAIL para contacto/fidelidad global. La entrega NO está aprobada como reconstrucción fiel completa. No se modificó el asset ni se ocultó el defecto. Presupuesto de correcciones agotado; coordinación determina procedimiento posterior. El manifiesto distingue técnica PASS y aquel PASS estrecho de aceptación global FAIL.
