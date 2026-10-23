# Cobertura y coincidencias pendientes

1021 modelos en 23 áreas: 342 de Poly Pizza, 637 de Kenney, 14 de OpenGameArt y 28 de Poly Haven. Las 134 consultas siguientes documentan la búsqueda inicial de Poly Pizza.

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

## Ampliación de otras fuentes

Kenney aporta completos Nature Kit (329 modelos), Food Kit (200) y Modular Buildings (108). OpenGameArt aporta Gear Pack (8), Animated LowPoly Robot (1) y Animated Animales Low Poly (5). Los 651 modelos añadidos tienen ficha individual y los seis ZIP completos están disponibles. No se acreditan nuevas especies guatemaltecas ni anatomía a partir de estos kits. La hormiga del piloto no pasó QA y queda excluida.

La comparación contra los 342 originales encontró una coincidencia geométrica entre las zanahorias de Kenney; se conserva la versión del kit y se agrupan ambas fichas. Miel, robot y lobo también se reúnen con sus posibles equivalentes para comparación. Las familias reúnen variantes semánticas, no aseguran igualdad geométrica. Las 651 incorporaciones preparadas no comparten SHA-256 con una ficha previa; los formatos alternativos del mismo objeto permanecen en el ZIP del kit, sin inflar la cantidad de fichas. La comparación del piloto de 23 modelos se conserva como evidencia histórica.

Los 1,368 archivos de los 342 modelos iniciales se verificaron sin cambios. Los GLB nativos mantienen la geometría y las imágenes fuente; los seis animados incluyen conversión documentada de materiales antiguos y comprobación de dimensiones de reposo. La revisión visual cubre 16 hojas de contacto de los 637 modelos Kenney y la comparación fuente/reimportación de seis animados. No sustituye la revisión docente de escala, precisión científica o uso curricular.

## Poly Haven

Se añadieron 28 referencias detalladas: mechero Bunsen, equipo de química, lupa, dos binoculares, dos microscopios, placa de circuito, multímetro, portátil clásico, dos bombillas, cinta métrica, brújula, silla de ruedas, caja de primeros auxilios, chaleco y aro salvavidas, extintor con rotulación coreana, semillero, regadera, dos palas de jardinería, tornillo de banco, cepillo de carpintería, dos llaves y ukelele.

Los GLB conservan los componentes glTF de 1K, incluyendo materiales, texturas, dimensiones y el rig mecánico del tornillo de banco. Los 993 modelos anteriores permanecen sin modificaciones. Las 28 preparaciones se compararon por SHA-256 y huella geométrica con el catálogo y entre sí: no hubo coincidencias. Las familias documentan afinidad funcional y variantes, sin sustituir fichas ni licencias.

La inspección visual compara vistas fuente, diagnóstico de malla y reimportación limpia. La adecuación docente, las graduaciones de instrumentos y la rotulación regional siguen pendientes. No se atribuyen nuevas especies, patrimonio guatemalteco ni exactitud metrológica a este lote.
