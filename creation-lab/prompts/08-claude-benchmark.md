# Prompt para Claude Code: benchmark Haiku, Sonnet y Opus

Copia el bloque siguiente en Claude Code abierto en la raíz de `3d-assets`.
El encargo prepara y ejecuta un benchmark nuevo; no cambia el flujo de producción
Sol/Luna. No se ha ejecutado Claude como parte de la preparación de este prompt.

```text
Trabaja en este repositorio 3d-assets. Quiero un benchmark reproducible de
creación 3D educativa con Claude Haiku, Sonnet y Opus. El caso es una célula
animal para secundaria, con trece estructuras y etiquetas en español.

Esta petición autoriza usar esas tres familias para este benchmark aislado,
como excepción explícita al default Sol/Luna del repositorio. Conserva ese
default para producción. No simules otra identidad de modelo para pasar un
validador y no atribuyas a Haiku código escrito o reparado por Opus/Sonnet.

1. INSPECCIÓN Y PREPARACIÓN
Lee AGENTS.md, SETUP.md, creation-lab/START-HERE.md,
creation-lab/docs/ITERATIVE-WORKFLOW.md, los skills gg3d-pipeline,
gg3d-benchmark, gg3d-lowpoly, gg3d-visual-qa y gg3d-export-qa, y el brief
creation-lab/benchmarks/animal-cell-20261022/brief.json.
Comprueba git status, herramientas, Blender y CLI --help. Conserva cambios
ajenos, modelos originales, índices, entorno UniRig y servidores existentes.
Usa un directorio y puerto propios. No modifiques el benchmark histórico.

Resuelve los modelos Haiku, Sonnet y Opus realmente disponibles en este entorno
mediante Claude Code/tu proveedor y su documentación oficial. Registra versión
de Claude Code, proveedor, alias solicitado, ID exacto resuelto y esfuerzo real
por agente. No supongas que un alias fija una versión. No uses opusplan ni
fallbacks que mezclen autores: si un runtime cambia de modelo, marca ese intento
como contaminado y consérvalo fuera de la comparación principal. Si no puedes
seleccionar o confirmar una familia, marca esa condición BLOCKED; no la imites
con el modelo de la conversación. Usa el acceso ya configurado; no busques
credenciales en otros archivos ni actives proveedores pagados adicionales.

La CLI iterate.py actual admite solamente Sol/Luna. Para este encargo implementa
un perfil de benchmark explícito y aislado que permita registrar los IDs Claude
confirmados por rol/condición, con pruebas de rechazo de modelos fuera del perfil.
Mantén los defaults Sol/Luna y todos los controles de evidencia. No elimines ni
relajes la validación de modelos globalmente. Reutiliza el worker, la biblioteca
components y el QA existentes; documenta comandos realmente implementados.

2. PROTOCOLO ANTES DE GENERAR
Congela un protocolo versionado en creation-lab/benchmarks/claude-animal-cell/.
Matriz principal: tres familias x tres autorías independientes = nueve réplicas.
Cada réplica comienza en contexto nuevo, escribe su propio generador y tiene
su propia sesión. Reejecutar el mismo script no cuenta como nueva autoría.
Escoge un esfuerzo común realmente soportado cuando sea posible; si no lo hay,
registra diferencias y compara configuraciones completas. No equipares a ciegas
medium/high entre familias o proveedores. No amplíes a más condiciones sin motivo.

Todos reciben el mismo brief, biblioteca de componentes, fuentes educativas,
cámaras, presupuestos, seed y límites. Conserva 0.30 m de dimensión mayor,
45 000 triángulos, 24 materiales, 350 mallas y GLB de hasta 8 MiB del brief.
Mantén Blender/renderer y el código común congelados durante el batch. Los
autores no pueden leer otros generadores, evaluaciones o resultados del piloto.
Pueden utilizar la biblioteca compartida: registra su hash y aclara que el
experimento mide creación asistida por componentes, no generación desde cero.

El coordinador puede ser Opus, pero solo organiza. No escribe ni corrige la
geometría de las condiciones. Cada familia realiza tanto su generación como
sus reparaciones. Registra coordinación y revisión aparte del autor y del coste
de autoría. Los renders Blender se ejecutan secuencialmente en este equipo.

3. FLUJO DE CADA RÉPLICA
Produce primero un blockout: envoltura abierta, núcleo y volúmenes distinguibles
de las trece partes. Renderiza y revisa visibilidad y relaciones antes del detalle.
Después construye las formas detalladas: cisternas aplanadas, ribosomas anclados
al RER, REL tubular, mitocondrias con crestas interiores, núcleo/nucléolo,
centríolos y demás estructuras requeridas. Conserva part_id y anclajes de etiquetas.

Permite hasta dos correcciones totales por sesión, además del primer blockout
y el primer detalle. Incluyen arreglos técnicos y visuales; no hay intentos
estéticos ocultos. El feedback debe identificar vista, defecto y cambio requerido;
no incluir código escrito por otro modelo. Un fallo técnico sin renders puede
repararse desde sus logs. Conserva todas las versiones y revisiones. Si se agota
el presupuesto, deja BLOCKED/FAIL con la causa y continúa las otras réplicas.

Usa el mismo reviewer Opus, versión/esfuerzo fijados y contextos independientes
para todas las condiciones. Entrega al reviewer el brief, imágenes y etiquetas
con IDs ciegos, sin modelo autor ni código. Mantén el mapping fuera de ese
contexto. El reviewer abre realmente las seis vistas y registra sus hashes.
Esto compara autores bajo un mismo sistema de revisión asistida; no es un
benchmark de flujos exclusivamente Haiku/Sonnet/Opus de extremo a extremo.
Declara el posible sesgo del revisor de la misma familia y no atribuyas su
aprobación a un docente externo. Un segundo juicio humano queda NOT_RUN si falta.

4. VALIDACIÓN
Separa técnica, visual y contenido/biología con PASS/FAIL/BLOCKED/NOT_RUN.
Comprueba dimensiones en todos los ejes, presupuesto, geometría no degenerada,
materiales, GLB autocontenido, reapertura .blend y reimportación en proceso limpio.
No relajes tolerancias por un fallo del importador: diagnostica fuente, export
e importación separadamente. Un formato correcto no demuestra utilidad educativa.

Evalúa biología visible (30), legibilidad (25), composición (15), forma/sombreado
(15) y utilidad educativa (15). Tener trece IDs no implica tener trece estructuras
reconocibles. Una pieza oculta se marca como no evaluable, no como correcta.
El contenido del blockout solo aprueba disposición de volúmenes; sus checks no
certifican el detalle todavía ausente. Verifica el visor aparte de los renders.

5. ENTREGABLES Y COMPARACIÓN
Por intento: generador exacto, biblioteca/brief/worker con hashes, recibo del
modelo/rol/contexto, .blend, GLB, parts.json, seis renders, logs, manifest,
diagnóstico y revisión. Guarda outputs grandes en .local con paquete restaurable
e índice de integridad si se distribuyen; no versionar secretos, caches o entornos.

Entrega protocolo, tabla por réplica, agregados por familia, fallos y limitaciones,
visor o enlace local comprobado, y comandos para repetir desde un clon limpio.
Muestra tasa de aceptación inicial/final, correcciones, notas y dispersión, tamaño
y complejidad del asset, tiempo de autoría si está disponible, tiempo Blender
por separado, tokens/coste solo observados y tiempo de coordinación/revisión.
Ausencias de telemetría = NOT_AVAILABLE. Tres réplicas siguen siendo exploratorias.

El piloto Sol/Luna/Astra de 2026 no tuvo bucle visual ni biblioteca común: úsalo
solo como contexto histórico, nunca para declarar que Claude supera a esos modelos.
Una comparación directa exigiría reejecutarlos con este mismo protocolo.

Comprueba tests y referencias de los skills modificados. No publiques en la
galería ni hagas push sin autorización específica para esa entrega. Termina con
los archivos reales, lo ejecutado, lo bloqueado y una recomendación limitada
a la evidencia obtenida. No te detengas en un plan si el entorno permite ejecutar.
```

El uso de agentes con contexto propio y la selección por alias/modelo se apoyan
en la documentación oficial de [subagentes](https://code.claude.com/docs/en/sub-agents)
y [configuración de modelos](https://code.claude.com/docs/en/model-config), consultada
el 22 de octubre de 2026. Verifica de nuevo las capacidades y los IDs al ejecutarlo.
