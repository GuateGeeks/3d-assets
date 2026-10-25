# Reconstrucción del alumno de primaria desde imágenes

## Autoridad y alcance

La fuente principal es references/GuateGeeks_Primaria_Piezas_R2/GuateGeeks_Primaria_Piezas_R2/imagenes/00-personaje-completo.png, en particular el frente y los tres cuartos. Es una ilustración de diseño, no una captura métrica. Las medidas normalizadas observadas sirven para reconstruir proporciones; no expresan dimensiones físicas del estudiante.

La geometría R3 es una referencia negativa y una fuente de infraestructura reutilizable. Su contrato numérico no prevalece sobre la imagen: perpetuó una cabeza estrecha, otro flequillo, mangas cortas, extremidades delgadas y zapatos pequeños. No se trasladan esas decisiones al nuevo generador.

Este trabajo produce un personaje de estudio editable. No sustituye el catálogo, no integra todavía un rig de producción ni publica cambios en el cotizador. La fidelidad se evalúa antes de producir una simplificación para la cámara del campus.

## Proceso reproducible

1. Conservar originales y hashes. Separar imagen principal, documentos históricos, resultados rechazados e interpretaciones nuevas.
2. Identificar silueta y puntos observables: coronilla, mentón, hombros, borde de manga, chaleco, mano, separación de piernas y calzado.
3. Construir el personaje completo con volúmenes grandes antes de dividir trabajo por piezas. Cabeza, pelo, manga y torso deben juzgarse juntos.
4. Renderizar frente, lateral, espalda, tres cuartos y alambre; exportar, reimportar y renderizar el GLB en un proceso nuevo.
5. Abrir las imágenes y revisar con un contexto independiente. Un conteo correcto no demuestra parecido. Conservar defectos y cada intento, sin sobrescribir evidencia.
6. Corregir proporciones antes de añadir ojos, sonrisa, solapas, tirantes y acabado. El pelo necesita una silueta asimétrica y un flequillo diagonal continuo; aumentar triángulos no corrige un diseño equivocado.
7. Revisar también en material neutro: el uniforme no debe disimular diferencias de forma. En el visor se puede alternar material, arcilla y alambre.
8. Entregar fuente Blender, generador, GLB, brief, imágenes y dictámenes técnico, visual y de contenido por separado. Un resultado de estudio no certifica animación, deformaciones ni rendimiento de todo el campus.

## Vistas generadas de apoyo

support/turnaround-support-v1.png se generó con la herramienta integrada de imágenes a partir de la lámina principal, el 25 de octubre de 2026. Se pidió conservar identidad, postura, flequillo, ropa y proporciones, y mostrar frente, lateral, espalda y tres cuartos. SHA256: bb9f752fe59014d4da997acd936fbf83798b89ca3a3662f840f0ca8d8094167a.

Inspección inicial: conserva bien vestimenta, colores y rasgos grandes, pero ensancha ligeramente la cabeza y su vista lateral continúa siendo oblicua. Por tanto, es apoyo de continuidad visual, no nueva autoridad ni ortografía certificada. No se usa su textura como sustituto de geometría. No se modificó ni sobrescribió el original.

## Decisiones que evitan repetir el fallo

- Congelar relaciones de silueta antes de publicar medidas de piezas y anclajes.
- No considerar las 20 recetas históricas como obligación de diseño; las piezas se derivan del personaje reconstruido.
- No confundir la cantidad de polígonos, un rig conectado o un export válido con aceptación artística.
- Mantener vistas y escala comparables al contrastar versiones. No deformar horizontalmente una imagen para que coincida.
- Marcar la profundidad no observable como una interpretación. La vista frontal no determina por sí sola la espalda o el perfil.
- Conservar iluminación neutra y material mate; los pliegues grandes deben seguir siendo legibles sin ruido de textura.
- Registrar los modelos y esfuerzos solicitados de los agentes. El backend real solo se afirma si el runtime lo expone.

La imagen y el diseño suministrados se conservan para este trabajo del usuario. No se les atribuye una licencia pública no proporcionada ni se promueven automáticamente al catálogo.
