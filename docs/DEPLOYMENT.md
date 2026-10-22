# Despliegue verificado

Fecha: 22 de octubre de 2026.

- Galería: https://guategeeks.com/3d-assets/
- Revisión del sitio publicado: `487651271ad45495e6c640adf32c1db2018244b3`.
- Validación CI aprobada: https://github.com/GuateGeeks/3d-assets/actions/runs/39849811227
- Compilación y despliegue aprobados: https://github.com/GuateGeeks/3d-assets/actions/runs/39850234177
- 342 modelos GLB y 342 miniaturas; tamaño del sitio 181.2 MiB.

Se verificaron en navegador el renderizado de modelos estáticos y animados, los filtros por licencia/área/movimiento, búsqueda en español, estado vacío y recuperación, reproducción/pausa de clips y navegación móvil hacia el visor y de regreso. Se revisaron las composiciones de escritorio (1440 × 1000) y teléfono (390 × 844), sin desbordamiento horizontal.

La acción de validación comprueba JavaScript, integridad de modelos y miniaturas, evidencias de licencia, rutas y ausencia de credenciales. El primer intento de despliegue se ejecutó antes de activar Pages y falló en Configure GitHub Pages; tras habilitar GitHub Actions como origen, la ejecución enlazada terminó correctamente.

Los despliegues posteriores se lanzan desde Actions → Deploy gallery to GitHub Pages → Run workflow, sobre main. No requieren la clave de Poly Pizza ni el token personal utilizado para preparar el repositorio.
