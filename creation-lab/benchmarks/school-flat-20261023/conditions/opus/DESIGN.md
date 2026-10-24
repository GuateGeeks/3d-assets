# Comparación · Escuela Flat/Minimal · condición solo-Opus

Pedido del usuario (23 oct 2026): conservar el diorama de la condición orquestada
(`../claude-school-20261023`, congelada con `SNAPSHOT.json`) y recrearlo por completo con
Opus 5.5 para comparar. n = 1 autoría por rol y condición: compara estos artefactos, no
demuestra superioridad general.

## Igual en ambas condiciones
- Brief (`spec/brief.json`, mismo sha256), kit inicial (paleta v1 extraída del generador blockout-v1
  de la línea base), contrato de módulos, `check_module.py`, `assemble.py` (solo cambia la nota de diseño),
  `build_web.py`, runner `iterate.py`/worker común, Blender 5.2.3 LTS, render común.
- Encargos de los 6 autores: mismo texto, cambiando solo rutas y el alias de modelo.
- Esfuerzo de autores `medium`; revisores Opus 5.5 `medium` en contexto nuevo; coordinador Opus 5.5 `high`
  (el mismo contexto de coordinación).
- Presupuesto: dos correcciones por sesión, además del primer blockout y el primer detalle.

## Diferencias conocidas (sesgos a declarar)
- Aclaraciones de contrato que en la línea base llegaron durante la ejecución están desde el inicio:
  `hinge` solo apertura (ya en CONTRACT.md) y duración común por clip (ANIM-BRIEF.md). Son aclaraciones,
  no feedback visual, pero reducen una ronda de mensajes del autor de animación.
- El coordinador ya conoce los defectos de la línea base (vuelta en U del bus, etiquetas). Regla:
  solo se reenvían defectos observados en las revisiones y pruebas de ESTA condición; no se anticipan
  arreglos de la línea base. Las indicaciones de etapa de detalle se derivan de las revisiones de esta condición.
- En la línea base el coordinador cambió la paleta del kit tras el blockout v1 por un defecto de contraste;
  aquí solo se cambia si una revisión de esta condición lo pide.
