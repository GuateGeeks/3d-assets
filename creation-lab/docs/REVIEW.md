# Revisión independiente del núcleo M1

Astra, esfuerzo xhigh, revisó el código y la evidencia de forma independiente.
La implementación estuvo a cargo de Sol high; los skills y prompts, de Luna
medium. La asignación sigue el plan de modelos, no constituye un benchmark.

Tres hallazgos corregidos y comprobados:

1. Los renders fuente se producían antes de la reapertura. Ahora las cinco
   vistas se generan en el proceso que reabre el `.blend`; se registran su hash
   y las invariantes de geometría, materiales, límites y transformaciones.
2. La firma de posiciones y la paleta no detectaban materiales reasignados ni
   caras invertidas. La firma de superficies considera triángulos orientados y
   material por superficie. Pruebas reales en Blender detectaron ambas
   corrupciones sin modificar los artefactos conservados.
3. El brief aceptaba un ID numérico y fallaba sin control con budgets de tipo
   lista. Ambos casos se rechazan antes de ejecutar Blender.

El revisor verificó los hashes del canario final, el snapshot del worker,
43 comprobaciones sin fallos y los tres procesos de Blender: construcción,
reapertura con cinco renders e importación con un render. No quedaron P1/P2
abiertos en el alcance del núcleo M1.

El coordinador abrió después las seis imágenes finales. La baliza asimétrica
está encuadrada; silueta, marcación frontal, chaflanes y asignación de los dos
materiales se conservan en la exportación. La vista posterior es más oscura por
la iluminación, pero legible. Esta aprobación solo cubre el canario técnico.

Las 12 pruebas incluyen dos con Blender real. El catálogo existente pasó
verificación de 342 modelos, miniaturas, rutas, licencias e inventario del sitio.
La comprobación de integridad de fuentes externas se registra por separado.

[Evidencia estructurada](validation.json) · [Estado actual](STATUS.md)
