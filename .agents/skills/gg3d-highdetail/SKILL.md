---
name: gg3d-highdetail
description: Produce un master 3D detallado y editable junto con un derivado optimizado que conserva el diseño aprobado.
---

# Assets detallados

Para composición, componentes y correcciones lee el
[workflow iterativo Sol/Luna](../../../creation-lab/docs/ITERATIVE-WORKFLOW.md).
Es la referencia única de roles, dos rondas por defecto y gates separados;
los perfiles propuestos aún no demuestran superioridad medida.


Sigue [aceptación](../../../creation-lab/docs/ACCEPTANCE.md). Separa el master editable de alta resolución del derivado optimizado. Para el robot, el derivado no supera 40000 triángulos, cuatro materiales ni texturas de 2048 px. Mide el GLB exportado.

Añade detalle donde mejore forma, respuesta de materiales o uso cercano, sin alterar el concepto ni el blockout aprobados. Conserva comprensibles la topología, nombres de objetos, transformaciones y espacios de materiales. Al reducir geometría, protege silueta y piezas necesarias. Crea UV y hornea mapas cuando aporten valor.

Reabre fuente y export en un proceso limpio. Compara el resultado con las vistas aprobadas y registra pérdidas, materiales no compatibles y límites incumplidos. No pidas nuevas aprobaciones para pasos técnicos ya autorizados.
