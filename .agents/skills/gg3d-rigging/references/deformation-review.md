# Revisar deformaciones antes de crear clips

La galería compara fuente/control/candidato sin reemplazar una inspección anatómica. Consulta el [informe del corpus](../../../../lab/reports/CORPUS-REVIEW.md), [mapa](../../../../lab/review-poses.json), [hallazgos](../../../../lab/review-findings.json) y [script de generación](../../../../lab/scripts/build_review.py).

## Comparación válida

- El humano de prueba es Man en T de reposo; el cuadrúpedo es Wolf con patas separadas. El Dog del catálogo está sentado y se dejó como caso difícil posterior. No generalices esa exclusión a todos los perros o assets sentados.
- Verifica que las mallas de control y candidato correspondan a la misma preparación, escala y orientación. Los originales conservan sus rigs/clips; las copias del diagnóstico no llevan animaciones.
- Inspecciona nombres, padres y pivotes del candidato antes de mapear. `bone_24` no significa rodilla para otro run. `review-poses.json` se liga al SHA del GLB; `review-findings.json` también al mapa. Si cambian, reinspecciona antes de actualizar hashes: no cambies el hash solo para eludir el rechazo.
- Las rotaciones se expresan en ejes globales, convertidas al espacio de la armature. Algunos rigs originales tienen pies/controles IK independientes: deben acompañar el mismo pivote de rodilla/codo para evitar un falso estiramiento. La prueba actual usa FK directa con seguidores explícitos; no resuelve IK ni retargetea clips.
- La superposición omite controles sin influencia y no dibuja como articulaciones reales las colas terminales que inventa el importador glTF. El número total de huesos no equivale al número de articulaciones deformantes útiles.

## Qué observar y medir

Abre realmente la malla opaca y el esqueleto. Compara frente, perfil y ángulos adicionales: simetría, axilas, codos, rodillas, cuello, raíz de cola, volumen, penetraciones, contactos con suelo y arrastre de zonas vecinas. Conserva capturas y hashes; distingue observación de inferencia numérica. No conviertas una silueta razonable en aprobación completa del rig.

La razón de estiramiento compara longitudes de la misma arista entre reposo y pose, excluyendo aristas de hasta 2 mm en el modelo normalizado. Se registran P95, máximo y mínimo. Los extremos localizan zonas para revisar; no prueban volumen/contacto ni permiten ordenar globalmente motores. Este umbral corresponde a la normalización de 2 m, no a cualquier escala física.

Los GLB de poses son instantáneas horneadas: cinco poses por asset, dos rigs, versiones opaca/esqueleto; no son clips. En el corte documentado hay 40 instantáneas y cuatro GLB adicionales, 44 en total. Comprueba el inventario actual en lugar de asumir siempre ese número.

Cada `review` crea un run y directorios nuevos. Conserva `runId`, `reviewRunId`, `mappingSha256`, hashes de fuente/candidato y la instantánea del mapa. Los manifiestos latest son punteros. Una revisión parcial de un asset no vuelve equivalentes las revisiones de los otros.

## Galería y límites

Usa [la galería existente](../../../../gallery.html), su [diseño](../../../../gallery/DESIGN.md), `gallery/lab.js` y `tools/serve_gallery.py --lab`. Conserva tipografía y controles establecidos. La comparación usa cámaras vinculadas; revisa encuadre completo en móvil y el botón Restablecer vista. Un acercamiento voluntario no es un defecto geométrico.

La interfaz guarda notas en el navegador por asset/run de inferencia/revisión y exporta JSON con hashes. No hay endpoint de aprobación; exportar notas no modifica el estado del laboratorio. El dictamen se incorpora a la evidencia por separado.

Sirve únicamente GLB del inventario y verifica SHA. Mantén bloqueados cachés, pesos, rutas privadas y aliases; aplica el mismo límite a GET/HEAD. No sustituyas el servidor por un servidor genérico sobre toda la raíz ni publiques los experimentos porque se vean en localhost. La galería pública y el catálogo permanecen separados del inventario privado de revisión.

`NODE_SKINNED_MESH_NON_ROOT` quedó en los candidatos crudos de UniRig; no equivale a error de formato ni a compatibilidad garantizada. Conserva la advertencia y normaliza/verifica la jerarquía del futuro derivado aprobado. La CSP del visor permite `wasm-unsafe-eval` para su WebAssembly; no amplíes a eval de JavaScript para silenciar un error. Usa archivos UTF-8 explícitos cuando el servidor corra en Windows.
