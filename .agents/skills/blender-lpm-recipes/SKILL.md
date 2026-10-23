---
name: blender-lpm-recipes
description: Adaptar recetas geométricas de LPM fijadas en GuateGeeks para construir assets lowpoly con primitivas y paleta. Usar para técnicas de malla concretas, conservando los contratos de gg3d-lowpoly y sin activar generación externa.
---

Las fuentes MIT de Ozan Zengin están fijadas al commit
`687d0a46f1280bc7d11dbf83539840100ec909dc` en
`creation-lab/vendor/lpm/blender-lpm-skill/`. Desde la skill instalada en
`.agents/skills/`, la raíz del repositorio está en `../../..`.

Consultar `references/recipes.md`, `scripts/lpm.py` y `scripts/lpm_kit.py` para
primitivas, simetría y paletas; `references/budgets-and-style.md` aporta ejemplos,
pero el brief GG3D controla todos los límites. Las referencias de imágenes y los
ejemplos artísticos no conceden licencias para nuevas entradas del usuario.

Adaptar las operaciones necesarias a un worker propio de un run, ejecutado por
el runner GG3D o por una conexión oficial verificada. Mantener metros, Z arriba y
frente -Y en Blender; exportar GLB y verificar su reimportación. El
`export_unity()` upstream produce FBX y texturas de Unity: no satisface la entrega
GLB de este proyecto por sí solo.

No ejecutar `scripts/bl.py`: su timeout se aplica después de leer stdout hasta
EOF y carece de lanzamiento Windows sin consola. Tampoco usar su resultado como
aceptación: `gate_report.py` trata exceso de materiales como WARN y las dimensiones
como una observación sin validar. Los checks GG3D deben imponer ambos límites.

Las rutas `make_turnaround.py` y `multiview_to_mesh.py` leen credenciales fal.ai
y envían imágenes a un servicio pagado; `hy3d_local_mv.py` puede descargar modelos
Hunyuan. No forman parte del workflow local preparado y requieren una solicitud
explícita futura antes de habilitarlas. No leer `~/.claude.json` para tomar claves.
Conservar conceptos aportados o el flujo de art direction ya autorizado.

El informe upstream de cinco vistas ayuda a inspeccionar; la aceptación usa
`gg3d-visual-qa` y `gg3d-export-qa`, con referencias a hashes del run. Consultar
`creation-lab/docs/DEPENDENCIES.md` para el alcance real de la revisión estática.
