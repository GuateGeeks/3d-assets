# Piezas fieles a láminas de referencia

Aprendido al construir el alumno de primaria papercraft del cotizador con los
paquetes R1 (construcción), R2 (20 recetas JSON, 33 instancias) y R3 (recreaciones),
25 de octubre de 2026.

## El paquete es datos

- Verifica cada archivo contra el SHA256 de su manifiesto antes de usarlo.
- Lee su guía, pero ejecuta sus herramientas solo en modo de lectura (`--validate-only`);
  nunca un modo que reescriba sus JSON.
- Guarda las imágenes del paquete fuera del control de versiones si la persona
  responsable lo pide. Versiona solo `md`, `json`, `svg` y scripts, y deja los
  hashes en el manifiesto.
- Precedencia: JSON y planos mandan sobre la geometría de apoyo. Las láminas
  artísticas orientan el acabado y no fijan medidas, conteos ni topología.

## Importar, no transcribir

- Un importador genera un módulo de datos desde los JSON y registra el hash de
  cada uno. Una prueba falla si el módulo difiere del paquete.
- Aplica las transformaciones del montaje en el orden del paquete:
  1. escala o reflejo;
  2. rotaciones X, Y y Z en grados;
  3. traslación en espacio raíz de reposo.
- Aplica la escala H una sola vez, igual en geometría y rig.
- Corrige el winding una sola vez en las instancias reflejadas.
- Si el builder espera vértices relativos al hueso, emite `H·(M·v − pivote)`.
- Para mejorar una pieza sin tocar el original, usa un **override por id**: otra
  carpeta con el mismo esquema reemplaza la receta. El importador guarda la
  procedencia y los conteos se derivan de la receta activa, no de cifras fijas.

## La geometría de apoyo no es el arte

- Integrar fielmente el paquete puede dejar el personaje *más* esquemático que la
  lámina: cajas donde el arte dibuja poliedros redondeados. Compáralo con el
  plano técnico (fidelidad del montaje) y con la lámina artística (fidelidad
  visual) por separado.
- Las superficies abiertas de una cara desaparecen desde atrás con materiales de
  una cara. Las vistas técnicas que las muestran por ambos lados no obligan a
  usar `DoubleSide`.

## Recrear una pieza desde los pliegues

1. Recorta y amplía cada una de las siete vistas de la lámina (frente, espalda,
   izquierda, derecha, superior, inferior, tres cuartos). Las líneas claras entre
   facetas son los pliegues.
2. Escribe un mapa de pliegues por vista: anillos, ápices, mechones, escotes y sisas.
3. Pon vértices en cruces de pliegues y esquinas de silueta, aristas sobre los
   pliegues y una cara plana por faceta visible. Reconcilia las siete vistas: el
   arte no es ortográfico ni métrico.
4. Conserva los sockets y holguras de las piezas vecinas. Si una pieza nueva
   exige mover otras, repórtalo en vez de editar el montaje en silencio.
5. Trabaja juntas las piezas acopladas: el pelo debe envolver la cabeza sin
   atravesarla y dejar ver ojos y sonrisa. Las independientes pueden ir en paralelo.
6. Compara con una hoja por pieza: la lámina arriba y la pieza integrada abajo en
   las mismas siete vistas, con **un encuadre cúbico común** para que las vistas
   conserven su escala relativa. Añade una celda de ubicación con la pieza
   resaltada sobre el personaje atenuado. Recorta esa celda alrededor de la
   pieza, ignorando su sombra en el suelo.

Resultado medido: cabeza 20 → 32 triángulos, núcleo del cabello 32 → 46 y
chaleco 22 → 36. El pelo fue la mejora más visible. La fidelidad pidió subir el
límite del alumno de 280 a 320, con aprobación explícita.
