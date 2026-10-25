# Escena, composición y QA en el navegador

Aprendido en el campus papercraft del cotizador (Three.js r186, un solo canvas,
render bajo demanda), 24–25 de octubre de 2026.

## Composición de un diorama

- **Escala de diorama.** Los equipos del mismo tamaño que los muebles no se ven desde la cámara general.
  - Exagéralos 1.8–3.6× en un hueso hijo `.size`, para que la animación mueva la montura sin escala.
  - Ponlos sobre tapetes de color que contrasten.
- **Mide la visibilidad.** Usa el área visible en píxeles de cada equipo, con un z-buffer por software que reproduzca las cámaras.
  - Mínimos usados: ≥ 250 px² en la vista general (1440 × 1000) y ≥ 2 500 px² en el aula enfocada.
- **Coloca para la cámara.** Pon la actividad hacia el lado abierto y visible, nunca bajo una losa ni detrás de personas.
- **Prueba de interpenetración.** Comprueba apoyo y cruces (laptops sobre la cubierta y de frente a su usuario; nada contra mesas, sillas, muros ni personas) en todos los estados compuestos. En el campus bajó de 519 fallas a 0.
- **Ocupación.** Dibuja solo sillas ocupadas: libera triángulos y evita aulas que parecen vacías.
- **Composición estable.**
  - Los elementos que se agregan con el crecimiento no deben moverse de un estado al siguiente.
  - Si una pieza cambia de anclaje, que sea una excepción explícita en las pruebas.
  - Evita una explanada vacía en la base: ajústala a lo construido más un margen.

## Interior translúcido sin materiales nuevos

Para ver dentro de un aula enfocada:

1. **Bloqueadores.**
   - Lo que queda encima del aula: techo, pisos superiores y su losa.
   - La pared que mira a la cámara.
   - Lo que queda entre la cámara y el aula, según la orientación de la cámara.
2. **Índice compartido.** Reordénalo como `[opaco | translúcido | oculto]`.
   - La malla original dibuja el primer rango.
   - Un gemelo `SkinnedMesh` con los mismos atributos, el mismo esqueleto y el material de vidrio existente dibuja el segundo.
   - No se crean materiales ni búferes.
3. **Edificios completos delante:** ocúltalos. Varias capas translúcidas apiladas forman un velo que no deja ver.
4. **Desechar el gemelo:** borra antes sus atributos e índice. Si no, liberarías los búferes de la malla original.
5. **Comprobaciones:** el conteo de geometrías no debe crecer en ciclos de enfocar y volver. Una captura para PDF debe quitar el efecto.

## Errores que encontraron las pruebas

- **Nombres de hueso repetidos.** Docente y estudiante compartían nombre. El estudiante nunca recibía su etapa de ensamblaje y aparecía en el primer paso. Añade una prueba de unicidad.
- **Coplanares.** Agrupar por normal redondeada da falsos negativos. Agrupa por desplazamiento del plano y reporta el hueso dueño de cada cara.
- **Línea base.** Los parámetros de render por pieza deben compararse en condiciones idénticas: semilla, pose, cámara, escala, luz y material. Muestra aparte cualquier cambio de luz o material.

## Rendimiento y entorno

- **SwiftShader.** Chromium headless cae a SwiftShader sin avisar y la escena adaptativa baja a calidad `eco`, sin sombras. Esa cifra no sirve para el presupuesto.
- **GPU en WSL.**
  - Exporta `GALLIUM_DRIVER=d3d12 LD_LIBRARY_PATH=/usr/lib/wsl/lib`.
  - Lanza Chromium con `--ignore-gpu-blocklist --enable-gpu --use-angle=gl`.
  - Confirma en `WEBGL_debug_renderer_info` que el renderer sea la GPU (por ejemplo «D3D12 (NVIDIA …)»).
  - Registra el rango de triángulos durante la actividad, las draw calls, los materiales y los fps.
- **Playwright.** Las variables declaradas con `let` en la página son globales léxicas: usa `typeof mascot !== 'undefined'`, no `window.mascot`.
- **Servidores locales.** Solo en `127.0.0.1`, un puerto por trabajo, y se detienen al terminar.
- **Shell.** Si `node`/`npm` son funciones de nvm en la shell del agente, fallan en silencio: usa la ruta absoluta del binario.

## Orquestación

- **Worktrees.** Usa un git worktree por trabajo paralelo, con propiedad de archivos y un contrato de API explícitos.
  - Ejemplo: composición posee la construcción de la escena y amplía `meta.actors`.
  - Animación consume esos actores y no edita esos archivos.
- **Campos nuevos.** Se documentan en un archivo compartido y se avisan al otro agente.
- **Al juntar ramas.** Regenera bundles, módulos de datos y contratos; no resuelvas conflictos a mano en archivos generados.
- **Despliegue.**
  - Pruebas completas: Node, mallas, personajes, actividades, navegador en cuatro condiciones y GPU.
  - PR con CI verde, merge.
  - Comprobar que el bundle publicado es idéntico al local y hacer una prueba de humo en producción.
