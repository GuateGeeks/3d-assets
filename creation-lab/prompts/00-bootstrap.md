# 00 · Bootstrap del laboratorio

Lee el [workflow iterativo](../docs/ITERATIVE-WORKFLOW.md): Sol `medium`
coordina y define la composición, Luna `medium` resuelve tareas delimitadas y componentes, y
Sol `medium` revisa imágenes en un contexto distinto del autor; Sol `high` queda
para diagnóstico difícil. Registra modelo/esfuerzo solicitados y reales de todos
los roles, sin sustitución silenciosa. Reutiliza componentes fiables antes del
detalle. Dos correcciones totales por sesión se comparten entre etapas, aparte
de la primera ejecución blockout y la primera detail; conserva todos los fallos.
Esta asignación es una propuesta operativa, no una superioridad medida.

Prepara el entorno local del laboratorio 3D y deja un diagnóstico reproducible. Lee [aceptación](../docs/ACCEPTANCE.md), [plan de hitos](../docs/IMPLEMENTATION-PLAN.md), [integración](../docs/INTEGRATION.md) y [modelos recomendados](../docs/MODELS.md). Consulta también el estado vigente y la CLI para distinguir lo implementado de lo futuro; los informes históricos no verifican este host.

Ejecuta `python creation-lab/create.py doctor --blender EXE` con el ejecutable realmente disponible para verificar la instalación nativa; registra versión observada, ruta resuelta y hash. No copies rutas de otro host. También puedes probar `--bpy-python PYTHON` solo si existe un entorno `bpy` 4.2 ya instalado. Trabaja en CPU, sin descargar software o assets, sin llamadas API y sin alterar UniRig.

Inspecciona las fuentes fijadas y licencias del registro local si existen. Comprueba si Blender Lab MCP está realmente conectado y enumera las herramientas expuestas. Solo si está conectado, prueba en una escena desechable consultar estado, capturar evidencia visual y realizar una modificación pequeña verificable. Una configuración de ejemplo no demuestra conexión. Registra cada capacidad como `PASS`, `FAIL`, `BLOCKED` o `NOT_RUN`; no instales ni conectes servicios durante este diagnóstico.

Usa la asignación recomendada en [MODELS.md](../docs/MODELS.md), incluidos los valores de esfuerzo. Es una preferencia de trabajo, no un benchmark ni una afirmación de calidad medida.

Entrega dependencias y fuentes detectadas, versiones, hashes y licencias disponibles, comando exacto, limitaciones y siguiente paso. Separa estado técnico (`PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`) del visual. No afirmes que M2–M7 están implementados sin evidencia en el plan y la interfaz real.

Aceptación: el doctor termina con resultado legible; cada limitación tiene evidencia y el entorno no ha cambiado más allá de lo necesario para ejecutar la comprobación.
