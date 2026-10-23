---
name: gg3d-pipeline
description: Coordina el flujo de creación 3D de GuateGeeks, desde el brief hasta un candidato de handoff con evidencia revisada.
---

# Flujo de creación 3D

Para composición, componentes y correcciones lee el
[workflow iterativo Sol/Luna](../../../creation-lab/docs/ITERATIVE-WORKFLOW.md).
Es la referencia única de roles, dos rondas por defecto y gates separados;
los perfiles propuestos aún no demuestran superioridad medida.


Este flujo produce geometría y evidencia en `creation-lab/`. Para preparar o inferir rigs, revisar pesos/deformaciones o continuar `lab/`, usa [gg3d-rigging](../gg3d-rigging/SKILL.md) y el [estado de rigging](../../../lab/STATUS.md). La entrega revisada se recibe con `ingest` y `rig --candidate`; la aceptación de la fuente no aprueba el rig.

Usa [criterios de aceptación](../../../creation-lab/docs/ACCEPTANCE.md), [plan de hitos](../../../creation-lab/docs/IMPLEMENTATION-PLAN.md), [integración](../../../creation-lab/docs/INTEGRATION.md) y [modelos recomendados](../../../creation-lab/docs/MODELS.md) como contrato. La interfaz Python define qué está implementado; inicia con `python creation-lab/create.py doctor` y usa solo los subcomandos disponibles.

La ruta M1 crea runs reproducibles e inmutables bajo `creation-lab/.local/runs`, con `.blend`, cinco renders reales, GLB y reimportación limpia. Continúa con `validate`, `report`, revisión visual con hashes y `handoff` candidato. Nunca sobrescribas evidencia previa.

Mantén separados los gates técnico, visual y de contenido, además del requisito de procedencia: `PASS`, `FAIL`, `BLOCKED` o `NOT_RUN`. No presentes la M1 como prueba de capacidad para M2–M7. No generes imágenes pagadas automáticamente ni alteres UniRig. En producción, espera aprobación explícita del usuario solo para el primer concepto y blockout antes de añadir detalle; ejecuta los pasos técnicos ya autorizados sin pedir confirmaciones repetidas.

Para preparar un clon nuevo, seguir [SETUP.md](../../../SETUP.md). El runtime
MCP opcional se restaura con su lock de Windows CPython 3.12 x64; la configuración
activa de cada equipo es local. Verificar las fuentes antes de usar recetas.

Los recibos históricos describen el equipo donde se ejecutaron, no rutas de
instalación obligatorias. Resuelve ejecutables mediante las opciones/diagnóstico
del CLI y comprueba las dependencias del modo elegido; no copies una ruta Steam,
UNC o un Python privado como requisito de otro host. Distingue código, resultados
versionados, artefactos que deben restaurarse y entornos/checkpoints locales.

Antes de un relevo o publicación, verifica desde un clon sin `.local` que las
instrucciones encuentran sus dependencias y artefactos. Conserva resultados
históricos y nuevas verificaciones por separado. El éxito del benchmark no
demuestra que `_site` represente el catálogo actual: comprueba fuentes y sitio
generado por separado. Si otro trabajo construye `_site`, no lo reconstruyas
ni detengas su proceso para cerrar una comprobación ajena; registra el alcance
pendiente. Usa un directorio/puerto propio para la comprobación independiente.
