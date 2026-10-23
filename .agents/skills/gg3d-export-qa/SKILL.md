---
name: gg3d-export-qa
description: Verifica exports de creation-lab, estructura GLB, reimportación limpia, límites y evidencia de handoff; el QA de deformaciones de rigs pertenece a gg3d-rigging.
---

# QA de exportación

El protocolo de seis imágenes y estados de esta skill corresponde a creación. Para candidatos UniRig y deformaciones consulta [gg3d-rigging](../gg3d-rigging/SKILL.md); no sustituyas la revisión anatómica por estos controles de export.

Sigue [criterios](../../../creation-lab/docs/ACCEPTANCE.md) y [contrato de integración](../../../creation-lab/docs/INTEGRATION.md). Valida el GLB desde disco y reimpórtalo en un proceso limpio de Blender o `bpy` 4.2 disponible. Confirma apertura, dimensiones, orientación, mallas, materiales, texturas, transformaciones y límites del brief. Reporta cualquier pérdida sin reparar la evidencia en silencio.

Usa `validate RUN` y `report RUN` cuando existan. Mantén el resultado técnico separado de la revisión visual. Una corrección crea nueva evidencia; la validación no modifica fuentes ni exports.

Abre también `reimport-three-quarter.png` y compárala con la vista fuente correspondiente. Para la revisión visual se requieren sus hashes junto con los de las cinco vistas fuente. El candidato de handoff requiere export y reimportación comprobados, hashes y resultados técnicos y visuales explícitos. `handoff RUN` crea un manifiesto candidato; no lo publica ni lo convierte en asset del catálogo.

Al reimportar glTF riggeado en bpy, usa `disable_bone_shape=True` cuando esté disponible o excluye explícitamente auxiliares de visualización de huesos. La Icosphere del importador no es geometría del export; contrasta el GLB desde disco antes de afirmar que cambió el asset. Las separaciones de vértices por normales/materiales tampoco demuestran agujeros: conserva la medición bruta y la evaluación soldada de diagnóstico sin modificar la fuente.

No abras una fuente `.blend` 5.2 en bpy 4.2 para transferirla: conserva la fuente y usa GLB entre versiones. Para rigs, escalar solo el nodo de malla no prueba escala física del skin. El [adaptador](../../../creation-lab/docs/INTEGRATION.md) registra normalización/inversa, restaura toda la jerarquía y comprueba geometría, UV, materiales, texturas, normales y pesos; una divergencia debe quedar como fallo, no como una restauración exitosa de dimensiones solamente.
