---
name: gg3d-visual-qa
description: Evalúa apariencia, silueta, proporciones, materiales y renders de assets de creation-lab contra su brief aprobado; para pesos y deformaciones de rigs usar gg3d-rigging.
---

# Revisión visual

Este protocolo es el QA visual de creación. Para comparar control/UniRig, poses estáticas, articulaciones y pesos usa [gg3d-rigging](../gg3d-rigging/SKILL.md). Un PASS de apariencia en reposo no aprueba deformación, clips ni anatomía de un rig recibido. Conserva separados esos dictámenes.

Compara el asset con el brief y la dirección aprobada; consulta los [criterios](../../../creation-lab/docs/ACCEPTANCE.md). Abre las cinco vistas fuente: `front`, `side`, `back`, `three-quarter` y `wireframe`, más `reimport-three-quarter.png` (seis imágenes en total). La última permite comparar el resultado reimportado. Comprueba escala, silueta, rasgos, lectura de materiales, intersecciones, sombreado y presentación. Un viewport o boceto no cuenta como render final.

Registra el estado visual aparte del técnico con `PASS`, `FAIL`, `BLOCKED` o `NOT_RUN`, una razón breve y el SHA256 de cada imagen revisada. Identifica cada defecto y la vista que lo demuestra. No apruebes renders ausentes ni conceptos pendientes.

Cuando esté disponible, usa `review` con `--opened-images` y un argumento `--evidence VIEW=SHA256` por cada una de las seis imágenes.
