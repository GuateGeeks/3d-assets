# Diagnosticar fuente, GLB y reimportación

Usar cuando la reimportación difiere de la fuente. Evidencia de origen:
[diagnóstico del piloto](../../../../creation-lab/benchmarks/animal-cell-20261022/HARNESS-NOTES.md)
y [adaptador de rigging](../../../../lab/reports/CREATION-ADAPTER.md).

Separa tres mediciones: geometría evaluada de la fuente, accessors binarios del
GLB y objetos reconstruidos por el importador. Compara posiciones en el mismo
sistema físico, winding, triángulos, normales, UV, materiales/texturas y límites.
Conserva las versiones exactas de Blender/exportador/importador: que el GLB
preserve las normales de origen y Blender las cambie al importar es distinto
de que el exportador las haya perdido.

Un diagnóstico que ignora normales puede demostrar que coinciden las demás
superficies; no sustituye la comparación completa. Para direcciones de normales,
registra tolerancia y dot mínimo/ángulo observado. Para límites, informa cada
eje y la diferencia en unidades físicas: conservar el eje mayor no demuestra
que todos los límites estén intactos. No amplíes tolerancias para aprobar un run.

Busca triángulos de área casi cero y aristas colapsadas antes de reparar. Un
helper de esfera que duplica un polo por segmento puede producir degenerados;
un polo único con abanico de triángulos evita ese defecto. En cortes y tapas,
comprueba centros coincidentes y winding. Esos hallazgos no prueban por sí solos
la causa de todos los cambios de sombreado: hubo fallos sin degenerados.

Triangular, soldar o fijar normales puede cambiar la fuente y su apariencia.
Haz reparaciones explícitas en una variante/run nuevo y vuelve a comparar; no
las introduzcas como saneamiento invisible del harness común. Conserva los
conteos brutos y cualquier copia soldada usada solo para diagnosticar costuras.

La reapertura del `.blend` y la importación del GLB deben ocurrir en procesos
limpios. Usa `--python-exit-code 1` al ejecutar scripts con Blender para que una
excepción Python no termine pareciendo éxito. Un código cero tampoco demuestra
calidad: exige informes y artefactos completos, y abre el render reimportado.

Para geometría riggeada, conserva las comprobaciones de jerarquía, matrices
inverse-bind y pesos del adaptador. No reduzcas su gate a dimensiones externas
ni traslades una solución estática a skins sin medir las coordenadas deformadas.
