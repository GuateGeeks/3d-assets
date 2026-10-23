# 00 · Bootstrap del laboratorio

Prepara el entorno local del laboratorio 3D y deja un diagnóstico reproducible. Lee [aceptación](../docs/ACCEPTANCE.md), [plan de hitos](../docs/IMPLEMENTATION-PLAN.md), [integración](../docs/INTEGRATION.md) y [modelos recomendados](../docs/MODELS.md). No supongas que existe un `STATUS.md`; usa el plan y la CLI para distinguir lo implementado de lo futuro.

Ejecuta `python creation-lab/create.py doctor --blender "D:\SteamLibrary\steamapps\common\Blender\blender.exe"` para verificar la instalación nativa disponible; registra la versión observada y el hash del ejecutable. También puedes probar `--bpy-python PYTHON` solo si existe un entorno `bpy` 4.2 ya instalado. Trabaja en CPU, sin descargar software o assets, sin llamadas API y sin alterar UniRig.

Inspecciona las fuentes fijadas y licencias del registro local si existen. Comprueba si Blender Lab MCP está realmente conectado y enumera las herramientas expuestas. Solo si está conectado, prueba en una escena desechable consultar estado, capturar evidencia visual y realizar una modificación pequeña verificable. Una configuración de ejemplo no demuestra conexión. Registra cada capacidad como `PASS`, `FAIL`, `BLOCKED` o `NOT_RUN`; no instales ni conectes servicios durante este diagnóstico.

Usa la asignación recomendada en [MODELS.md](../docs/MODELS.md), incluidos los valores de esfuerzo. Es una preferencia de trabajo, no un benchmark ni una afirmación de calidad medida.

Entrega dependencias y fuentes detectadas, versiones, hashes y licencias disponibles, comando exacto, limitaciones y siguiente paso. Separa estado técnico (`PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`) del visual. No afirmes que M2–M7 están implementados sin evidencia en el plan y la interfaz real.

Aceptación: el doctor termina con resultado legible; cada limitación tiene evidencia y el entorno no ha cambiado más allá de lo necesario para ejecutar la comprobación.
