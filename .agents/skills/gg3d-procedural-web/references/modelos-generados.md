# Modelos generados o riggeados → personaje web de rig rígido

Aprendido al llevar al campus del cotizador los alumnos de primaria de Meshy y un modelo propio
riggeado en Blender (25 de octubre de 2026). Destino: Three.js, color por cara, 12 huesos, una
influencia por vértice. Presupuesto por alumno con sombra: 320 triángulos; el campus mayor, 40 000
con la pasada de sombras. Herramientas: `tools/meshy-import.mjs` del cotizador y
`procedural-web/pw.py adopt` de este repositorio.

## Primero, mirar qué llegó

Abre el GLB o el `.blend` y anota cuatro cosas antes de elegir método. Cada una cambia la ruta:

- **Triángulos y topología.**
  - Un remallado denso de una forma simple (el niño de Meshy: 369 000 triángulos, una sola malla cerrada).
  - Piezas cerradas sueltas (la niña de Meshy: 3 951 en 42 piezas).
  - Una malla riggeada de autor (940 triángulos con esqueleto Mixamo).
- **Rasgos.** Ojos y sonrisa pueden estar solo pintados en la textura, dentro de caras grandes, o venir como placas planas delante de la cara.
- **Rig.** Puede no traer ninguno o traer pesos suaves de muchos huesos.
- **Paleta.** El mismo uniforme puede venir en otro tono: chaleco violeta brillante o azul violáceo oscuro.

Mide un barrido error → triángulos con meshoptimizer. Un modelo de papel bien facetado cabe
entero cerca del presupuesto: el niño quedaba fiel en 298 triángulos. Eso dice si el problema es
la cantidad de triángulos o la topología.

## Malla única densa: simplificación global con costuras

- **Una sola simplificación de toda la malla, guiada por error.** Por partes, cada borde se encoge por su lado y aparecen grietas.
- **Cortes por articulación.** Antes, se corta la malla densa con **planos completos** en cada articulación y se separan los vértices por hueso. El simplificador conserva esos cortes como costuras: sin grietas en reposo y cada cara de un solo hueso.
  - Un corte limitado a una región deja juntas en T: bordes abiertos que gastan presupuesto y rompen la forma.
- **Caras sin costura.** Si una cara cruza la rodilla, las piernas se desarman al sentarse.
- **Ruido de clase de color.** No pongas costuras en los cambios de color: el ruido de la textura llena el modelo de islas que el simplificador no puede reducir.
- **Clase por voto.** Cada cara simplificada vota su clase entre las caras densas que tiene debajo.
- **Juntas.**
  - Tapa los extremos de cada segmento: un muslo abierto se ve hueco al doblar la rodilla.
  - La sisa va escalonada (más adentro sobre la axila) para que el casquillo de la manga siga al brazo.

## Piezas cerradas: una pieza, un hueso

- **Huesos.** Cada pieza va al hueso que le toca por su centroide y su clase. La falda se parte en x = 0 para que cada mitad siga a su muslo.
- **Descartes.**
  - Las placas planas de la cara (vuelven como calcomanías).
  - Las cáscaras duplicadas: el mismo color y cajas que coinciden en más del 80 %.
  - Las puntas sueltas de tirantes.
- **Simplificación.** Una simplificación global deja manos y piernas como astillas. Simplifica cada pieza con **un mismo error absoluto**, buscado para caber en el objetivo:
  - menos error en la cabeza (×0.6), el torso y la falda (×0.7);
  - un mínimo por pieza (las coletas, 10, para que no queden como láminas);
  - los extremos de las piezas grandes bloqueados, para no perder alto ni anchos (la cúpula del cabello se encogía 4 %).

## Malla riggeada de autor: conservar sus polígonos

- **No reduzcas sin preguntar.** Si pasa del límite, informa el total y su efecto en el campus medido en GPU. El nuevo límite queda en una constante propia.
- **Pesos suaves → una influencia.** Cada vértice sigue a su hueso de más peso (mapa de huesos, por ejemplo Mixamo → 12). Los triángulos entre dos huesos **se estiran** en la articulación con un triángulo cuyos vértices siguen huesos distintos. No hay grietas, no se añaden caras y el shader rígido sigue igual.
- **La tela sigue al torso.** El chaleco y la mochila siguen al torso: al levantar el brazo se estira la manga, no el chaleco.
- **Pivote de cadera.** El de Mixamo (`Hips`) está más alto que los muslos. Si la escena sienta por el pivote de la cadera, ponlo a la altura de los muslos; ese hueso solo se traslada.
- **Zapatos.** Los zapatos largos piden suela en mecedora (puntera y talón suben) y su propia altura de rodillas (`kneelLift`).
- **Original intacto.** Copia el `.blend` del autor al run y nunca lo abras en su sitio. Si su Blender muestra cambios sin guardar, avisa de que se leyó la versión del disco.

## Color, rasgos y capas (los tres métodos)

- **Color.** Clasifica cada cara por la textura (centroide y tres puntos interiores) con **varios prototipos por clase**, más reglas de posición:
  - zapatos abajo;
  - en la cabeza solo piel, cabello y tinta;
  - bajo el mentón, cabello solo como coleta;
  - sobre la cintura no hay falda.
  
  El campus recolorea por alumno, así que la clase importa más que el tono.
- **Rasgos pintados.** Rasteriza las caras de la cara en UV, quédate con los píxeles de tinta (azul marino oscuro, nunca el violeta del cabello) y llévalos a 3D por baricéntricas. Quedan tres manchas: dos ojos y la sonrisa.
- **Calcomanías.** Ojos (hexágono de 4 triángulos) y sonrisa (3) a 0.0075 H **a lo largo de la normal** de la faceta bajo cada vértice, no en z. Si caen fuera del contorno, toma el plano de la faceta frontal más cercana.
- **Capas cercanas.** Las capas de distinto color a menos de 0.006 H (≈ 0.0045 de escena) parpadean: la cara menor se aleja por su normal. Incluye la misma tela espalda con espalda (una solapa) y devuelve al piso cualquier suela empujada bajo y = 0.

## Rig y validación

- **Pivotes.** Mídelos en el modelo, con una cuadrícula de 0.05 H.
- **UniRig como segunda opinión.** Coincidió en rodilla y cuello, y puso la cadera más abajo y el codo en el borde de la manga (adoptados). Su hombro es una clavícula interna pensada para pesos suaves: con piezas rígidas el pivote va en la punta del hombro.
- **Convención de ejes.** Comprueba posiciones de articulaciones en tres poses entre la escena y Blender, con una tolerancia de 1e-4.
- **Altura** de la persona: la del nivel (0.78 en primaria).
- **Proporciones del modelo** (cabeza 0.30 o 0.32 H): se informan, no se fuerzan.

## Procedencia y sincronía

- **Módulo generado.** El módulo guarda el SHA256 de su fuente. La prueba de sincronía regenera desde el GLB cuando está presente.
- **Módulo editado.** Un módulo adoptado o retocado en Blender lleva `SOURCE.edited` y pasa a ser la fuente:
  - el importador no lo pisa sin `--force`;
  - la prueba valida la procedencia en vez del GLB.
- **Archivos pesados.** Los GLB y `.blend` grandes se quedan fuera de Git, con sus hashes en el README de referencias.
