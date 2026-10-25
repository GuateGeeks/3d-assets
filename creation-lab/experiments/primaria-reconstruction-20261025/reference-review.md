# Revisión independiente de referencia

Contexto revisor: /root/student_likeness_review. Sol medium solicitado; runtime sin recibo verificable del modelo/esfuerzo real. No autoría de geometría. Se abrieron mediante view_image R2 00-personaje-completo.png y R3 refinado-frente/perfil/espalda.png. R2 SHA256: d19cdd56cd9aca99d99e1501975ae75fa8e214854ccd75ae238113a83930df2a.

La lámina R2 manda sobre R3. Frente y tres cuartos fijan parecido. Perfil y espalda solo resuelven profundidad donde sean compatibles; no son ortografía calibrada. Las medidas son estimaciones de ilustración en perspectiva: alto total H=1; z=0 en suela y z=1 en coronilla. Frente: y coronilla≈212, suela≈870, H≈658 px. Tolerancia orientativa: posiciones ±0.02H, anchos ±10%; evaluar también lectura global.

| Rasgo | Estimación visual |
|---|---|
| Cabeza/pelo | Anchura máxima≈0.34H; mentón z≈0.69; cabeza ancha y cara corta/llena. |
| Flequillo | Gran masa diagonal baja hacia izquierda de imagen. Límite de cara sube hacia derecha. Un pico dominante y grandes masas laterales; evitar dientes simétricos. |
| Cara | Ojos pequeños oscuros verticales a z≈0.78; separación≈0.10H. Sonrisa curva pequeña centrada z≈0.73; sin nariz prominente. |
| Cuello | Corto z≈0.65–0.69; cuello blanco de dos grandes puntas y abertura V delante del chaleco. |
| Torso | Hombro z≈0.67; bajo chaleco z≈0.41; ancho chaleco≈0.23H; ancho hombros con mangas≈0.40H. Chaleco morado saturado ligeramente abierto abajo. |
| Manga/manos | Manga holgada blanca hasta codo z≈0.49; antebrazo piel. Brazos abiertos hacia abajo. Puños poligonales grandes, altura≈0.09H. |
| Pantalón | Azul oscuro; cintura z≈0.41, bajos≈0.08. Dos perneras anchas casi rectas≈0.12H cada una, hueco entre bajos≈0.04H. |
| Zapatos | Morado oscuro; alto≈0.09H; ancho cada uno≈0.16H; gran puntera prismática; ancho conjunto≈0.36H. |
| Mochila | Turquesa vivo; cuerpo ancho≈0.21H y alto≈0.24H, z≈0.39–0.63. Sale claramente en perfil/3/4. Tirantes anchos≈0.03H apoyados sobre hombro y bajando al lateral del chaleco. |

La referencia muestra mangas hasta codo y antebrazos descubiertos. Coordinación confirmó esa lectura frente a la expresión inicial mangas largas. Las manos son puños angulares sin dedos realistas. La estética exige planos amplios quebrados, bordes definidos y sutiles variaciones triangulares: no ruido de triangulación que borre masas. Pelo berenjena oscuro, chaleco violeta, pantalón índigo, zapatos berenjena, blanco y turquesa deben distinguirse claramente.

## R3: defectos que no deben heredarse

- Frente: zapatos/manos diminutos, piernas visualmente largas y estrechas, ausencia de base pesada juvenil.
- Frente: flequillo dentado casi simétrico y casco uniforme; falta diagonal dominante y anchura expresiva R2.
- Frente: mangas tubulares cortas rígidas y brazos muy delgados/verticales. R2 tiene manga caída holgada y manos grandes.
- Perfil: torso plano, pie pequeño, tirantes finos como cable flotante; no cinta ancha apoyada. Pelo no reproduce barrido.
- Espalda: pantalón largo/angosto, zapatos mínimos, corte de pelo recto y mochila pequeña/alta frente a R2.

## Gates siguientes

Blockout PASS requiere cabeza ancha, relación torso/pernera, manos/zapatos grandes, mangas holgadas, piernas separadas y mochila/tirantes volumétricos. Color correcto con proporciones R3 sigue FAIL. Ojos, sonrisa y triangulación fina no son requisito de blockout.

Detalle requiere flequillo diagonal reconocible, ojos/sonrisa proporcionados, cuello legible, pelo coherente, manos/calzado angulares y mochila con cintas anchas apoyadas. Abrir seis renders reales: front, side, back, three-quarter, wireframe y reimport-three-quarter. Separar técnico, visual y contenido. Renders no recibidos: visual NOT_RUN y contenido NOT_RUN. Sin aprobación anticipada.

## Apoyo generado

Se abrió support/turnaround-support-v1.png. Conserva bien los colores, silueta y flequillo de R2; cabeza ligeramente ampliada y cuerpo visualmente más compacto. Es apoyo de construcción, no nueva autoridad ni medida calibrada. Su segundo personaje sigue en vista oblicua y no demuestra una ortografía lateral. No usarlo para justificar desviaciones frente a R2.
