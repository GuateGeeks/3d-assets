# Alumno de primaria GuateGeeks · reconstrucción R4

Resultado: modelo de estudio estático, editable y reproducible desde la referencia completa R2. El diseño conserva cabeza ancha, flequillo diagonal, mangas amplias, manos visibles, pantalón azul, calzado voluminoso y mochila turquesa. La comparación de forma precedió al rostro y al acabado.

## Abrir el resultado

- Modelo: delivery/model.glb.
- Fuente editable: delivery/model.blend.
- Piezas y generador: delivery/parts.json y delivery/generator.py.
- Comparador: inspector/index.html. Requiere HTTP local; incluye Three.js y funciona sin CDN.
- Vistas finales: presentation-v2/; revisión independiente: completion-review.json.
- Imágenes de apoyo: support/; prompts y límites: PROMPTS.md.
- Proceso reusable: WORKFLOW.md y reference-review.md.

Para abrir el comparador desde esta carpeta (Python real instalado):

```sh
python -m http.server 8096 --bind 127.0.0.1
```

Abrir http://127.0.0.1:8096/inspector/ . El visor permite frente, perfil, espalda, tres cuartos, órbita, arcilla y alambre; la referencia frontal conserva sus proporciones y altura aparente.

## Reconstrucción

El paquete incluye la receta y el worker congelados; Blender aporta bpy. No es necesario ejecutar npm ni instalar paquetes Python para reconstruir el modelo.

```sh
python reproduce.py --blender "/ruta/a/blender" --output "/carpeta/nueva/reconstruccion"
```

Se usa completion-recipe por defecto. El comando crea, guarda, reabre, exporta, reimporta y renderiza seis imágenes. Nunca sobrescribe una carpeta de evidencia. Se ejecutó realmente con Blender 5.2.3 LTS (build e13b728c6880), Python 3.13.13 y Cycles CPU; build, reopen y reimport resultaron PASS. Otras versiones deben producir su propia comprobación.

Para repetir el contacto sobre otra reconstrucción:

```sh
blender --background --factory-startup --python verify_contacts.py -- --source "/carpeta/nueva/reconstruccion/source.blend" --glb "/carpeta/nueva/reconstruccion/asset.glb" --output "/carpeta/nueva/contacto.json"
```

Para presentar la geometría con cámaras ortográficas y material neutro:

```sh
blender --background --factory-startup --python render-presentation.py -- --source "/carpeta/nueva/reconstruccion/source.blend" --output "/otra/carpeta/nueva/vistas"
```

## Verificación y límites

La entrega contiene 1.738 triángulos, 30 mallas, 8 materiales y un GLB de 95.948 bytes. Altura convencional de 1 m, centrada en el origen: no representa la talla real de un niño. Blender usa +Z arriba y −Y delante; GLB usa +Y arriba y +Z delante.

Técnica, revisión visual y contenido: PASS dentro del brief de reconstrucción low-poly. Contacto de pantalón y zapatos: PASS en 12 muestras por archivo, tanto Blender como GLB; no prueba todos los puntos de las superficies. Se revisaron seis vistas y ortografías adicionales, con hashes. No se certifican animaciones, deformaciones ni rendimiento de una escena completa.

La reproducción conserva simplificaciones: cabello y cara tienen menos planos que la ilustración, no se añadió microtextura de fibra, y queda un pequeño asomo de piel junto a la zona posterior del cabello. Las imágenes de apoyo tampoco son ortografías métricas. El parecido no se presenta como copia exacta.

## Historia conservada

Los cuatro intentos de la sesión original y sus informes siguen intactos en el workspace. El candidato004 pasó una revisión estrecha pero una inspección posterior descubrió un hueco real en el calzado; su aceptación global se registró FAIL. La entrega procede de completion-run, un quinto intento de cierre documentado en completion-protocol.json. No se amplió ningún presupuesto geométrico ni se ocultó el fallo. Esta excepción local no modifica el protocolo predeterminado del proyecto y no constituye un benchmark.

El primer comprobador de contacto falló en GLB por muestrear vértices duplicados por normales en vez de posiciones diferentes. completion-contacts-v2.json conserva la comprobación corregida sin modificar ninguna malla.

Las referencias fueron aportadas para este trabajo. Se conserva su procedencia y no se atribuye una licencia pública nueva al personaje.
