# Resultados · escuela Flat/Minimal, orquestada vs solo-Opus

23–24 de octubre de 2026. **Ambas condiciones terminan aprobadas** en técnica, visual y
contenido, con animación y visor web verificados. La orquestada (Haiku/Sonnet como autores)
costó menos; la solo-Opus llegó con menos iteraciones. Es n = 1 autoría por rol y condición:
compara estos dos artefactos, no demuestra superioridad general de un modelo.

## Comparación

| | Orquestada | Solo-Opus |
| --- | --- | --- |
| Blockout v1 | técnica PASS · visual **FAIL** (nube tocando la torre; wireframe sin aristas) · contenido PASS | técnica PASS · visual PASS · contenido PASS |
| Correcciones usadas (máx. 2) | 1 (blockout v2) | 0 |
| Detalle | PASS / PASS / PASS, 9/9 contentChecks | PASS / PASS / PASS, 9/9 contentChecks |
| Geometría final | 90 objetos · 7.078 triángulos · 19 materiales | 91 objetos · 7.492 triángulos · 19 materiales |
| Animación (9 clips) | PASS: 64 checks + 31 de verificación | PASS: 23 + 8 (tras corregir un falso FAIL del exportador) |
| Revisión final animación / interacción / estilo | PASS / PASS / PASS con reservas | PASS / PASS / PASS con reservas |
| Rondas de ajuste del visor tras probar con datos reales | 2 | 2 |
| Tokens entrada / salida ≥ | 36,1 M / 176,7 k | 34,2 M / 149,7 k |
| Costo estimado (equivalente de API) | **≈ $13,1** | **≈ $15,2** |

Desglose del costo estimado:

| | Orquestada | Solo-Opus |
| --- | ---: | ---: |
| Autores | $1,79 | $7,13 |
| · tres módulos simples (entorno, patio, vida) | $0,03 c/u (Haiku) | $0,61–0,81 c/u |
| · edificio / animación / visor | $0,34 / $0,50 / $0,86 (Sonnet) | $0,90 / $1,15 / $2,88 |
| Revisores | $1,47 (4 revisiones) | $1,16 (3 revisiones) |
| Coordinador | $9,85 | $6,95 |

Tarifas de lista del skill `claude-api` (caché del 6 de octubre de 2026, no verificadas en vivo):
Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0,10/$0,50 por millón, con escrituras de caché
según su TTL real y lecturas de caché a la tarifa de cada modelo. La salida es cota inferior: los
transcripts guardan el uso del inicio del stream y el razonamiento oculto no se cuenta. Es costo
equivalente de API, no la factura de una suscripción. Scripts: `receipts.py`, `cost_estimate.py`.

Modelos reales verificados en cada transcript: todos los roles respondieron con el modelo pedido.

## Pendientes comunes

- El bus (0.07 m) gira en U sobre una calle de 0.042 m y pisa la banqueta: el recorrido lo fija el contrato.
- La tarjeta de la puerta sigue diciendo "Tócala para abrirla" con la puerta abierta.
- Sin prueba de clic directo sobre el canvas ni en navegadores o dispositivos reales.
- El render "wireframe" del runner común no muestra aristas a esta escala (grosor fijo `.00018*factor`).

## Aprendizajes que cambian decisiones

1. **El modelo del autor importa menos que el costo de coordinar.** Con contrato, kit de primitivas
   cerradas y un verificador puro, Haiku entregó módulos acotados que pasaron al primer intento por
   ~3 centavos, frente a $0,6–0,8 con Opus. El coordinador fue el 75 % del costo en la orquestada
   y el 46 % en solo-Opus: reducir rondas, depuración y mensajes pesa tanto como elegir el autor.
2. **Contrato primero, autores en paralelo.** Plano con regiones, paleta cerrada, primitivas
   validadas y `check_module.py` permitieron cuatro autores simultáneos sin Blender: todos los runs
   de ambas condiciones pasaron la parte técnica a la primera.
3. **Escena estática y animación separadas.** El worker común exige escena estática; los módulos
   describen el movimiento en propiedades `anim_*` y un paso aparte re-pivota, crea acciones y las
   mete en pistas NLA con el nombre del clip. Blender 5.2.3 fusiona las pistas homónimas de varios
   objetos en una animación glTF por clip. Los clips con periodos mixtos necesitan una duración común;
   un clip de interacción (puerta) va solo de cerrado a abierto y el visor invierte el sentido.
4. **Revisar trayectorias contra la geometría.** Ningún check midió el volumen barrido del bus; el
   defecto pasó todas las revisiones de imágenes fijas. Un clip con traslación necesita un check de
   límites por fotograma o fotogramas densos de la parte crítica.
5. **Una revisión por gate es ruidosa.** Dos revisores Opus independientes juzgaron distinto una nube
   casi idéntica sobre la torre; esa diferencia explica la única corrección que separa a las condiciones.
   En comparaciones, usar doble revisión o ejemplos de calibración, y reportar el desacuerdo.
6. **Dar hechos, no prescripciones geométricas.** Una instrucción del coordinador (girar la bandera
   −35°) contradijo la cámara y costó media corrección. Entregar la dirección de cámara y dejar que
   el autor calcule fue más fiable.
7. **Probar el visor con datos reales e interacción.** Sombras de nubes, etiquetas fijas sobre partes
   móviles y etiquetas encima de la UI solo aparecieron con el GLB real. Un script CDP (Chromium
   headless + WebSocket de Node 22) que pulsa chips, puerta y noche y recoge errores de consola
   detectó los cambios de estado; conviene incluir estos requisitos en el encargo web desde el inicio.
8. **Los transcripts subestiman la salida.** El uso registrado por mensaje suele ser el del inicio
   del stream; para recibos, tomar el máximo por mensaje y estimar la salida visible como cota inferior.
9. **Comparaciones secuenciales con el mismo coordinador se contaminan.** La segunda condición recibió
   aclaraciones de contrato que la primera obtuvo a mitad de camino, y el coordinador ya conocía los
   defectos. Para una comparación limpia, contexto de coordinación separado y mensajes congelados.

## Evidencia

- Orquestada: runs `001-bfd67d4b45f3` (blockout v1), `002-9af6cf0bfa2f` (blockout v2), `003-4f40280a1fc5` (detalle).
- Solo-Opus: runs `001-a1341a7ff806` (blockout), `002-da798cb30fbb` (detalle).
- Revisiones ingeridas por `iterate.py`, revisión final y resultados de animación en `conditions/<c>/evidence/`.
- Entregables con hashes en `fixtures/index.json`. Las páginas publicadas como Artifact privado son copias
  construidas con `build_web.py`; no forman parte de la evidencia versionada.
- Dependencia: el modo `benchmark` de `creation-lab/iterate.py` usado en ambas sesiones pertenece al trabajo
  del benchmark Claude de célula animal; a la fecha de este informe estaba sin integrar en `main`.
