# Reconstrucción fiel de un personaje desde imágenes

Aplicar cuando el usuario ya eligió un personaje y pide reproducirlo. En ese caso, desarrollar variantes de identidad no es el objetivo: conservar la dirección elegida y resolver su volumen.

## Antes de modelar

- Identificar una imagen principal y las vistas que mandan sobre las demás. Separar referencias positivas, modelos rechazados e interpretaciones generadas.
- Una receta de piezas o un JSON histórico no conserva autoridad si el usuario rechaza su parecido. Derivar las proporciones nuevas de la referencia elegida y explicar qué es observación aproximada.
- Registrar hitos normalizados por altura total: coronilla, mentón, hombro, manga, mano, cadera y suela. Las ilustraciones pueden contener perspectiva e inconsistencias: no llamarlas planos calibrados.
- Extraer relaciones de anchura y silueta además de alturas. Aumentar uniformemente un personaje no corrige una cabeza estrecha con torso ancho.
- Conservar entradas, prompt, hashes, fuentes y las limitaciones de las imágenes de apoyo. Una vista generada que todavía sea oblicua no se convierte en perfil ortográfico por su etiqueta.

## Blockout y detalle

Construir primero el personaje entero. Dividirlo en autores por piezas antes de estabilizar las proporciones puede producir un montaje técnicamente válido de otro personaje.

La silueta frontal sola no basta. Abrir lateral y espalda: una cabeza con forma correcta delante puede ser una escalera de prismas detrás. Las grandes masas deben tener volumen cerrado y coherente antes del rostro, costuras, fibra y rig.

Modelar planos deliberados. Un casco continuo de anillos variables puede resolver la corona; una superficie frontal amplia con chaflanes de borde puede resolver la cara sin crear una gran banda oscura en la mandíbula. No sustituir el flequillo asimétrico por mechones pequeños repetidos.

Comprobar apoyos y capas. Tirantes deben seguir el hombro y el chaleco; no formar un marco flotante. Superficies de cadera y pantalón coplanares pueden producir franjas negras aunque el GLB y las normales pasen. Eliminar o separar esas caras con geometría explícita.

## Presentación y gates

Antes del primer run, comprobar el contrato de cámara del worker: la presentación común apunta al origen. Centrar también la altura del asset y sus etiquetas cuando corresponda; no modificar la escala física para encuadrarlo.

Abrir los seis renders del workflow. Agregar frente ortográfico real, material neutro y acercamientos cuando las cámaras comunes no permitan contrastar la imagen. Conservar fuente y hash de la geometría usada por esas presentaciones.

La comparación debe conservar proporción y altura aparente. Recortar con CSS o una cámara no autoriza estirar horizontalmente una referencia para disimular una discrepancia.

Un PASS de blockout significa que masas y distribución están aceptadas. Si se difiere un defecto de superficie al detalle, registrarlo explícitamente como obligatorio y comprobarlo en la entrega. No trasladar al detalle una forma mayor rechazada, no aprobar por presupuesto de intentos agotado y no ocultar fallos anteriores.

Separar export/reimportación, parecido visual, contenido y deformación. El rig se valida después de la forma; no demuestra reconocimiento del personaje.

## Evidencia del caso

[Alumno de primaria, proceso y límites](../../../../creation-lab/experiments/primaria-reconstruction-20261025/WORKFLOW.md). Los intentos y su dictamen permanecen en el experimento; este aprendizaje no declara éxito final ni superioridad medida de un modelo o proveedor.

## Contactos que las vistas generales pueden ocultar

Una cuña del zapato puede dejar suspendido el bajo del pantalón aunque una vista elevada parezca correcta. Añadir frente/perfil ortográficos reales, inspección a tamaño grande y una comprobación de contacto sobre la malla exportada. Muestrear posiciones distintas: el GLB puede duplicar vértices por normales y materiales. Registrar una omisión de revisión sin reescribir el PASS histórico; la aceptación global debe reflejar el defecto hallado posteriormente.