# Célula animal · benchmark piloto

Seis propuestas originales para secundaria, con trece partes y explicaciones en
español. Cada autor generó código procedural de Blender a partir del mismo
[brief](brief.json) y [contrato](AUTHORING.md). Los archivos editables, GLB,
renders y recibos están en `creation-lab/.local/benchmarks/animal-cell-20261022/`.

## Explorar y usar

Desde la raíz de `3d-assets`, con Python 3.10 o posterior:

```powershell
python creation-lab/benchmarks/animal-cell-20261022/serve.py --port 4393
```

Abrir <http://127.0.0.1:4393>. El visor permite comparar propuestas, girar el
modelo, seleccionar las partes y descargar el GLB o el archivo de Blender.
Las etiquetas son interactivas; `parts.json` conserva las posiciones, nombres,
funciones y correspondencia con los objetos editables. El GLB también conserva
`part_id` en los extras de cada objeto.

La maqueta mide aproximadamente 30 cm. Los colores, cantidades y proporciones
son convenciones didácticas; no representan una micrografía ni una escala
microscópica exacta. Es una selección de estructuras de una célula animal
generalizada en interfase. Algunas células especializadas difieren de este
esquema y no se representa todo el inventario celular.

## Diseño de la comparación

| Variante | Modelo autor | Esfuerzo solicitado |
| --- | --- | --- |
| A | gpt-6.1-sol | high |
| B | gpt-6-luna | medium |
| C | gpt-6-astra | high |
| D | gpt-6.1-sol | medium |
| E | gpt-6-luna | high |
| F | gpt-6-astra | medium |

El [protocolo](protocol.json) fija semilla, presupuesto de geometría, cámara,
iluminación, Blender 5.2.3 LTS y render CPU. Los autores trabajaron en contextos
independientes; las asignaciones constan en [el recibo](authoring-receipt.json).
Hay una sola propuesta por condición: esto permite comparar estos seis
artefactos, no demostrar superioridad estadística de un modelo ni completar
el benchmark M7 de seis briefs distintos.

El tiempo registrado corresponde al proceso local de construir, reabrir,
renderizar y reimportar, con sus verificaciones. No mide latencia pura del
modelo. No se dispone de telemetría de tokens ni de costos. No se ejecutaron
proveedores externos de texto a 3D ni APIs de imágenes.

Una condición puede fallar visualmente aunque contenga trece identificadores
y pase las comprobaciones técnicas. Los defectos y las primeras ejecuciones
se conservan; el protocolo permite como máximo una reparación técnica por autor.

## Reproducir una condición

```powershell
python creation-lab/benchmarks/animal-cell-20261022/run.py A --blender 'D:\SteamLibrary\steamapps\common\Blender\blender.exe'
```

Cada ejecución crea una carpeta nueva con código, versiones, comandos, tiempos
y hashes. `COMPLETE` contiene el hash del manifiesto. Los artefactos existentes
no se sobrescriben. La comprobación adicional de formato usa la dependencia
Khronos ya instalada en el laboratorio:

```powershell
node creation-lab/benchmarks/animal-cell-20261022/validate.cjs
```

## Relación con 3d-assets

El benchmark vive en `creation-lab`, usa la comprobación de geometría y
materiales del adaptador del laboratorio y conserva escala, ejes y procedencia
en sus recibos. Cada propuesta tiene objetos separados por estructura.
No necesita un esqueleto ni una inferencia de UniRig para su uso educativo.
Estos experimentos no se insertan automáticamente en el catálogo publicable.

## Fuentes educativas

Las funciones del brief son paráfrasis de fuentes abiertas consultadas:
[OpenStax: células eucariotas](https://openstax.org/books/biology-2e/pages/4-3-eukaryotic-cells),
[sistema de endomembranas](https://openstax.org/books/biology-2e/pages/4-4-the-endomembrane-system-and-proteins),
[citoesqueleto](https://openstax.org/books/biology-2e/pages/4-5-the-cytoskeleton),
[MedlinePlus: la célula](https://www.medlineplus.gov/genetics/understanding/basics/cell/)
y [NHGRI: mitocondrias](https://www.genome.gov/genetics-glossary/Mitochondria).

La zona pálida representa citosol; el citoplasma comprende citosol y orgánulos
fuera del núcleo. El núcleo contiene la mayor parte del ADN, no todo. El
nucléolo no tiene una membrana propia y las mitocondrias transforman energía
química para producir ATP. Estas distinciones deben conservarse al adaptar
las etiquetas para clase.

Geometría procedural original, sin modelos ni imágenes externos. La declaración
de procedencia y licencia CC0-1.0 se conserva en el brief y cada run.
