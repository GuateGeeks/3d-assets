# Encargo · visor web interactivo

Escribe `index.html` en tu carpeta de autor: una página que muestra el diorama
animado de la escuela (Flat Shaded / Minimalist 3D) y permite explorarlo. UI en
español. Será publicada como Artifact de claude.ai, así que sigue el contrato
de página de abajo. No puedes ver el GLB todavía: programa contra los formatos
descritos y deja el código robusto ante datos faltantes.

## Datos que inyecta el coordinador

Antes de tu `<script type="module">` habrá un `<script>` que define:

```js
window.SCHOOL = {
  glb: "data:model/gltf-binary;base64,....",   // animated.glb
  title: "...", designNotes: [...],
  parts: [ {id, label, function, objects:[nombres de objeto Blender], positionGltf:[x,y,z]} ],  // 14 partes
  clips: { puerta:{parts:["puerta"], autoplay:false, trigger:"click"}, reloj:{...autoplay:true}, ... }
};
```

Deja en tu archivo un marcador exacto `<!--SCHOOL_DATA-->` donde va ese script.
Para probar sin datos, si `window.SCHOOL` no existe muestra un estado claro
("Modelo no disponible") en lugar de fallar.

El GLB: Y-up, metros, diorama ≈0.40 m de ancho centrado en el origen (suelo
≈ y=-0.04). Cada malla tiene `userData.part_id` (extras glTF). Los nombres de
objeto pueden sanearse en three.js: identifica partes **solo** por
`userData.part_id`. Animaciones glTF: una por clip con el nombre del clip. Un
material de vidrio se llama `flat_vidrio` (en three.js `material.name`).

## Requisitos

- three.js como ES modules con importmap desde
  `https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js` y
  `https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/` (GLTFLoader, OrbitControls).
  Nada de otros hosts. Carga el GLB desde `window.SCHOOL.glb` (data URI) con `GLTFLoader.parse`
  o `loadAsync`.
- Estilo flat: conserva normales planas (`material.flatShading = true`,
  `needsUpdate`), luz hemisférica + direccional con sombras suaves, cielo con
  degradado sencillo. Encuadre inicial tres cuartos que muestre todo el diorama.
  OrbitControls con amortiguación, límites (no bajar del suelo, zoom acotado).
- Animación: `AnimationMixer`; reproduce en bucle los clips con `autoplay`.
  La puerta se abre/cierra al tocarla (o desde su tarjeta): `LoopOnce`,
  `clampWhenFinished`, alterna sentido. Controles: pausar/reanudar todo,
  velocidad (0.5×, 1×, 2×).
- Interacción: clic/tap con raycaster → parte (`userData.part_id`): resalta todas
  sus mallas (tinte emisivo suave, se restaura al deseleccionar), muestra tarjeta
  con etiqueta y función, enfoca suavemente la cámara a `positionGltf`. Hover en
  escritorio con cursor pointer. Lista de las 14 partes como botones (chips)
  sincronizada con la selección. Etiquetas HTML numeradas proyectadas en
  `positionGltf`, ocultables, que no tapen el modelo en móvil.
- Día/noche: cambia cielo, intensidad y color de luces; de noche el vidrio
  (`flat_vidrio`) brilla (emisivo cálido).
- Botones: Restablecer vista, Etiquetas, Día/Noche, Pausa, Velocidad, Giro automático.
- Accesible: botones reales con foco visible, `aria-pressed`, respeta
  `prefers-reduced-motion` (sin giro automático, animaciones a velocidad normal
  pero sin transiciones de cámara largas).
- Rendimiento: `renderer.setPixelRatio(min(devicePixelRatio, 2))`, redimensiona
  con ResizeObserver, pausa el render si la pestaña no es visible.

## Contrato de página (Artifact)

- Sin `<!doctype>`, `<html>`, `<head>` ni `<body>`: empieza con `<title>Escuela Flat</title>`
  y `<meta name="claude:viewport-fit-sides" content="cover">`, luego `<style>`.
- Scripts externos solo de cdn.jsdelivr.net/npm/ (versiones exactas). Fuentes
  solo de Google Fonts con fallback real. Todo lo demás en línea.
- Tokens de color en `:root` (tema claro), redefinidos para oscuro bajo
  `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {...; color-scheme: dark} }`
  y bajo `:root[data-theme="dark"] {...}`. `body` con fondo explícito de token.
- Funciona a 400 px de ancho sin scroll horizontal; margen lateral
  `padding-left: max(16px, env(safe-area-inset-left, 0px))` (y derecho igual) en el
  contenedor de UI. App de una pantalla: `height: 100%` en html/body, no `100vh`.
  Controles fijos a un borde suman `env(safe-area-inset-*)`.
- Sin `alert/confirm/prompt`, sin descargas, sin `window.print`.
- Diseño propio y sobrio, acorde a "minimalista facetado": paleta de la escuela
  (pasto 9CCB6B, muro F4E3C1, teja C8553D, celeste 4997D0, oscuro 2F3A45),
  tipografía con carácter pero legible (evita Inter/Space Grotesk), nada de
  emojis como iconos, sin degradados morados. El 3D es el protagonista; la UI
  es una capa ligera (barra de herramientas + panel/tarjeta; en móvil, hoja inferior).

Entrega: ruta y sha256 de `index.html` y una lista breve de lo implementado.
