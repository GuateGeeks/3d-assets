---
name: gg3d-lowpoly
description: Crea assets 3D low-poly compactos y legibles para el robot GuateGeeks y usos educativos.
---

# Assets low-poly

Para composición, componentes y correcciones lee el
[workflow iterativo Sol/Luna](../../../creation-lab/docs/ITERATIVE-WORKFLOW.md).
Es la referencia única de roles, dos rondas por defecto y gates separados;
los perfiles propuestos aún no demuestran superioridad medida.


Aplica [criterios de aceptación](../../../creation-lab/docs/ACCEPTANCE.md). Para el robot original conserva altura de 0.30 m, cuerpo compacto, pantalla frontal, dos ruedas, brazos simples y ningún logotipo inventado. El LOD0 exportado admite como máximo 6000 triángulos, dos materiales y texturas de 2048 px.

Esas cifras corresponden al robot. Para otro asset o benchmark, usa el presupuesto
explícito de su brief; registra la escala de la maqueta y sus convenciones sin
atribuirle precisión física o científica que no se haya solicitado y verificado.

Prioriza silueta y formas funcionales frente al ruido superficial. Conserva editables las piezas significativas y documenta escala, frente, pivotes, normales y materiales. Verifica los conteos en la geometría evaluada y en el export, después de modificadores; no uses estimaciones de la malla base.

Mide también los límites de los vértices reales: una esfera recortada con anillos
discretos puede no contener su ecuador y no alcanzar el radio analítico. Calcula
la composición a partir de esos límites cuando la dimensión del brief sea estricta;
no cambies la tolerancia para aceptar la diferencia.

Mantén este entregable separado del master detallado. Usa la ruta M1 de la CLI para exportar, reimportar en proceso limpio y conservar evidencia. Los conteos correctos no implican aprobación visual.
