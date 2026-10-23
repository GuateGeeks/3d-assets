---
name: blender-codex-recipes
description: Consultar las recetas Codex de Rivello fijadas en GuateGeeks para resolver una tarea concreta de Blender, incluyendo blockout, modelado, materiales, iluminación, UV, render o exportación. La orquestación y aceptación de assets pertenecen a gg3d-pipeline.
---

Este adaptador usa las recetas técnicas de Samuel Asher Rivello, commit
`54b4f26b7c0e530b7158244f397b34e6c16d7b76`, conservadas bajo licencia MIT.
Resuelve la raíz del repositorio desde esta carpeta (`../../..` cuando está instalada
en `.agents/skills/`) y lee solo la receta necesaria en
`creation-lab/vendor/rivello/<nombre>/SKILL.md`:

- `blender-create-greybox` y `blender-create-model`: masas, silueta, proporciones y contactos.
- `blender-materials`, `blender-light-camera`, `blender-uv-bake`: superficies, encuadre y mapas.
- `blender-render`, `blender-game-export`, `blender-review-optimize`: salidas e inspección técnica.
- `blender-setup`: diagnóstico de una conexión oficial existente; no configura ni instala por sí solo.

Las recetas son referencias técnicas. El brief de GuateGeeks define escala,
presupuestos, materiales, ejes y destino; no heredar la paleta fija de ocho colores
del greybox ni el contrato `documentation/models/` del repositorio de origen.
La referencia upstream a `blender-create-visual-target-2d` se resuelve mediante el
trabajo de conceptos de `gg3d-art-direction`; esa skill upstream no está instalada.

El núcleo headless de `creation-lab/create.py` es una ruta independiente y autorizada.
La disponibilidad de MCP no condiciona un run headless. Para trabajo MCP, primero
consultar `creation-lab/docs/DEPENDENCIES.md`, comprobar conexión actual y el PID
de Blender previsto, y conservar los registros del run. Una prueba desechable
anterior no demuestra que el editor del usuario esté conectado ahora.

Los scripts upstream permanecen sin modificar. `audit_scene.py` cuenta slots y
no sustituye la comprobación GG3D de materiales realmente usados;
`verify_outputs.py` verifica estructura PNG, sin dictamen visual ni confinamiento
de rutas arbitrarias. Usarlos solo con objetos/manifiestos propios de un run.
Los helpers setup leen configuración de cliente; ejecutarlos únicamente cuando
la tarea requiera ese diagnóstico, sin volcar secretos ni reconfigurar el cliente.

La entrega usa las puertas de `gg3d-pipeline`, `gg3d-visual-qa` y `gg3d-export-qa`.
Los estados upstream no se convierten automáticamente en PASS de GuateGeeks.
La licencia y los hashes están en `creation-lab/sources.lock.json`.
