# Comprobar un visor de modelos

Aplicar a entregas interactivas con `model-viewer`, no a una revisión que solo
solicite renders. El [visor del piloto](../../../../creation-lab/benchmarks/animal-cell-20261022/README.md)
tiene comprobaciones HTTP y de interacción separadas.

Comprueba en el navegador real que el GLB se ve y termina la carga, que los
selectores cambian la condición, que las etiquetas muestran la explicación y
anclaje correspondientes, y que girar/restablecer/ocultar etiquetas funciona.
Prueba actualizar resultados con el mismo modelo cargado: puede no producir un
nuevo evento `load`. En `model-viewer`, asignar la propiedad `src` no garantiza
que el atributo DOM `src` refleje el valor; conservar la URL activa y el estado
de carga evita un indicador permanente al refrescar.

Comprueba el encuadre en el ancho real de entrega. Una cámara fija que funciona
en un render puede recortar el modelo en un panel estrecho. Guarda una captura
del resultado y registra el viewport probado; no declares una prueba de móvil
o escritorio ancho si solo se usó el panel lateral.

Inspecciona errores de consola posteriores a la carga actual. El bundle local
puede inicializar WebAssembly incluso si el GLB no usa compresión. Si la CSP lo
bloquea, limita la excepción necesaria a `wasm-unsafe-eval` en `script-src`;
no habilites `unsafe-eval` de JavaScript ni abras permisos globales por defecto.
Valida la corrección tras recargar, distinguiendo los errores históricos.

Las pruebas HTTP de rutas, descargas y metadatos no demuestran que WebGL renderice.
Las pruebas visuales tampoco verifican por sí solas que cada descarga conserva
sus bytes. Mantén ambos recibos, con versiones/hashes cuando correspondan. Para
un servidor local, usa el inventario explícito de assets y conserva su ámbito
local; no sirvas todo el repositorio para resolver un 404.
