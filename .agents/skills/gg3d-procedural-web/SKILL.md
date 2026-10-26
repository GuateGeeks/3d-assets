---
name: gg3d-procedural-web
description: Crea y verifica modelos 3D procedurales para la web (Three.js, color por vértice, sombreado plano, rig rígido), como el campus y los personajes papercraft del cotizador; incluye piezas fieles a láminas de referencia, composición de escenas, presupuestos y medición en GPU.
---

# Modelos procedurales para la web

Ruta distinta de Blender/GLB: la geometría se genera en JavaScript al cargar la
página, sin texturas ni UV, con color por vértice, sombreado plano y un rig de
una influencia por vértice. Caso de referencia: el campus papercraft del
cotizador (repositorio `GuateGeeks/cotizador`, `docs/papercraft/GESTION-VISUAL.md`).
Para assets Blender/GLB sigue [gg3d-pipeline](../gg3d-pipeline/SKILL.md).

## Contrato antes de modelar

- Fija presupuestos del frame completo, no por malla: triángulos **incluida la
  pasada de sombras**, draw calls y materiales. Decide qué capas proyectan sombra
  (solo arquitectura) y cuáles usan sombra de contacto.
- Cuenta los auxiliares en el límite de la pieza (la sombra de contacto de un
  personaje). Si el paquete de referencia ya ocupa el límite, redistribuye caras
  siempre ocultas antes de añadir; un cambio de límite lo aprueba la persona
  responsable y queda en una sola constante.
- Un hueso por panel rígido, nombres de hueso **únicos** (las etapas de ensamblaje
  se enlazan por nombre) y separación normal mínima entre capas superpuestas. Un
  modelo de piel suave que debe conservar sus polígonos usa costuras estiradas: cada
  vértice sigue a un hueso y los triángulos entre dos se estiran (sigue siendo una
  influencia por vértice).
- El presupuesto del campus depende de la composición: si la variante pesada sale
  por semilla (niño o niña), mide el estado mayor en GPU y registra el margen.

## Piezas fieles a láminas

Con paquetes de referencia por piezas, sigue la
[guía de piezas y pliegues](references/piezas-y-pliegues.md): verificación del
paquete como datos, recetas JSON importadas con prueba de sincronía, overrides por
id sin tocar el original, mapa de pliegues por vista y comparación con escala común.

## Modelos generados o riggeados

Para llevar un GLB de Meshy (malla densa o piezas cerradas) o un personaje riggeado de autor
al rig rígido, sigue la [guía de modelos generados](references/modelos-generados.md): mira
primero la topología, simplifica con costuras en planos completos o pieza por pieza, conserva
los polígonos de un modelo de autor con costuras estiradas, y saca los rasgos pintados de la
textura como calcomanías.

## Composición y escena

Diorama: exagera la escala de los equipos (1.8–3.6×) para que se lean desde la
cámara general; colócalos donde la cámara los ve; mide su área visible en
píxeles y comprueba con una prueba automática que nada atraviesa mesas, muros ni
personas. Detalles y la técnica de interior translúcido sin materiales nuevos en
la [guía de escena](references/escena-y-qa.md).

## Retoque en Blender

Para retocar a mano geometría, colores, pivotes o clips de animación de esos personajes, usa
[gg3d-blender-web](../gg3d-blender-web/SKILL.md): exporta a `.blend` y devuelve el retoque al
cotizador con procedencia.

## Verificación

Abre las imágenes antes de dictaminar y separa técnica, visual y contenido.
Mide rendimiento en GPU real: Chromium headless cae a SwiftShader sin avisar
(ver la guía de escena). Una carpeta nueva por corrida; revisión independiente
en contexto nuevo para cerrar un corte.
