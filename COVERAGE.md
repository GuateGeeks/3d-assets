# Cobertura y coincidencias pendientes

342 modelos originales en 23 áreas; 134 consultas inspeccionadas.

La biblioteca es una selección inicial para revisión y autoría. La API puede devolver aproximaciones semánticas. Las consultas siguientes no tienen una coincidencia literal completa en el título dentro de la primera página inspeccionada. Esto no prueba que el modelo no exista en todo el catálogo. No renombrar un recurso para presentarlo como una especie, instrumento o sitio que no ha sido verificado.

| Consulta | Recursos descargados |
| --- | --- |
| animated animal | Wolf |
| person | Man |
| human heart | Heart; Heart; Pickup Heart |
| lungs | Chest |
| human skull | skull003; Skull; Skull |
| human brain | Brain In A Jar 💭; Brain; Brain |
| pulley | Hose wheel |
| motor | Motorcycle; Motorcycle; Motorcycle |
| electric motor | Large Electric Generator |
| pottery | Honey |
| ruins | Ruin |
| playground | Play Structure |
| trash bin | Trash Can; Trashcan Small; Trashcan |
| quetzal | Parrot |
| tapir | Collared peccary |
| ceiba | Bamboo |
| cacao | Coffee bean |
| marimba | Xylophone |
| tikal | Mayan Temple |

## Contexto guatemalteco

Un loro no se acredita como quetzal, un xilófono no se acredita como marimba y un templo genérico no se acredita como una reconstrucción de Tikal. Los modelos similares se conservan con su título original y se reclasifican cuando la asociación es incorrecta; `unfulfilledQueries` identifica los objetos solicitados que esos recursos no acreditan. No se consideran necesidades resueltas. Para revisar la respuesta completa, consultar `sources/search/<consulta>.json`.

## Animaciones

`gltf` conserva lo encontrado en cada archivo. `apiAnimated` registra lo declarado por el catálogo. Ver [animados](indices/animation/animated.md), [con esqueleto](indices/animation/rigged.md) e [inconsistencias](indices/review/api-animation-mismatch.json).

## Licencias

La cobertura de licencias de todos los candidatos inspeccionados, incluyendo los no seleccionados, está en [sources/license-coverage.json](sources/license-coverage.json). Cada licencia encontrada está representada en la descarga; no se inventan licencias que no aparecieron en las consultas.
