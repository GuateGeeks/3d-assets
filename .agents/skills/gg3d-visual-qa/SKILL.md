---
name: gg3d-visual-qa
description: Evalúa apariencia, silueta, proporciones, materiales y renders de assets de creation-lab contra su brief aprobado; para pesos y deformaciones de rigs usar gg3d-rigging.
---

# Revisión visual

Para composición, componentes y correcciones lee el
[workflow iterativo Sol/Luna](../../../creation-lab/docs/ITERATIVE-WORKFLOW.md).
Es la referencia única de roles, dos rondas por defecto y gates separados;
los perfiles propuestos aún no demuestran superioridad medida.


Este protocolo es el QA visual de creación. Para comparar control/UniRig, poses estáticas, articulaciones y pesos usa [gg3d-rigging](../gg3d-rigging/SKILL.md). Un PASS de apariencia en reposo no aprueba deformación, clips ni anatomía de un rig recibido. Conserva separados esos dictámenes.

Compara el asset con el brief y la dirección aprobada; consulta los [criterios](../../../creation-lab/docs/ACCEPTANCE.md). Abre las cinco vistas fuente: `front`, `side`, `back`, `three-quarter` y `wireframe`, más `reimport-three-quarter.png` (seis imágenes en total). La última permite comparar el resultado reimportado. Comprueba escala, silueta, rasgos, lectura de materiales, intersecciones, sombreado y presentación. Un viewport o boceto no cuenta como render final.

Usa un revisor/contexto distinto del autor y registra modelo y esfuerzo solicitados y reales de todos los roles según el workflow. Registra los estados visual y de contenido aparte del técnico con `PASS`, `FAIL`, `BLOCKED` o `NOT_RUN`, una razón breve y el SHA256 de cada imagen revisada. Identifica cada defecto y la vista que lo demuestra. No apruebes renders ausentes ni conceptos pendientes.

Para modelos educativos, distingue apariencia de exactitud del contenido:
comprueba que las partes exigidas sean visibles, identificables y estén en la
relación espacial correcta. Los nombres de objetos y etiquetas no prueban eso.
Declara las convenciones de color/escala y limita el dictamen a lo observable.
Si una estructura está oculta, registra la imposibilidad de evaluarla; no infieras
un PASS por el código que supuestamente la construye.

Cuando la entrega incluya un visor interactivo, comprueba también su carga,
selección y cámara según [QA del visor](references/viewer-checks.md). Esa prueba
de interfaz se registra por separado de la revisión de renders.

El `wireframe` del runner común usa un grosor de arista fijo que en maquetas de 0.3–0.4 m casi no se ve; juzga el facetado en las demás vistas y no lo cuentes como defecto del autor mientras el runner no cambie. En assets animados revisa además fotogramas de los tramos críticos de cada trayectoria (giros, extremos), no solo los primeros segundos.

Cuando esté disponible, usa `review` con `--opened-images` y un argumento `--evidence VIEW=SHA256` por cada una de las seis imágenes.
