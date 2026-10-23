# Contrato con el laboratorio de rigging

`creation-lab` produce geometría y evidencia; `lab` prepara, riggea y evalúa
deformaciones. Comparten repositorio y catálogo de fuentes, no su entorno Python.

| Área | Dueño y función |
| --- | --- |
| `models/`, `index.json` | Originales y licencias del catálogo |
| `lab/` | UniRig, corpus actual, deformaciones, clips y revisión de rigs |
| `gallery/`, `tools/` | Visor y publicación existentes |
| `creation-lab/` | Briefs, recetas, creación, QA y candidatos |
| `.agents/skills/` | Instrucciones reutilizables de creación y rigging |

## Entrega y comandos

El comando `handoff` entrega un manifiesto versionado que referencia el run
de origen, GLB, `.blend`, hashes, unidades, dimensiones, orientación, procedencia,
licencia y resultados técnicos/visuales. La CLI documenta el formato exacto.
El receptor está en `lab/creation_adapter.py`; `lab/lab.py` lo expone mediante
`ingest` y la opción `rig --candidate`. Usa el entorno UniRig existente en WSL.

Desde la raíz de `3d-assets`:

```bash
python3 lab/lab.py ingest --candidate creation-lab/.local/runs/<handoff>/candidate.json
# Copiar el valor preparedManifest impreso por ingest:
python3 lab/lab.py rig --candidate lab/.local/runs/<ingest>/creation-prepared.json --stage all
```

En Windows, sustituye `python3 lab/lab.py` por `.\lab\lab.cmd`; las rutas de
argumentos pertenecen a WSL. Las referencias UNC del handoff original de este
checkout se traducen a su ruta Linux, conservando el contenido y los hashes.
`--candidate` y `--asset` son excluyentes. `--timeout` limita cada etapa.

`ingest` verifica la entrega cerrada, sus artefactos y la cadena de revisiones,
y exige QA técnica, visual y de derechos aprobada. Copia la evidencia y los
originales a un run independiente antes de preparar la geometría. El `.blend`
original se conserva como archivo; la entrada de Blender 4.2 es el GLB.
Las referencias que escapen del ámbito permitido, symlinks, hashes diferentes
y evidencia incompleta se rechazan.

El manifiesto preparado y su inventario quedan sellados. `rig --candidate`
vuelve a verificarlos y copia esa entrega a su propio run antes de ejecutar
extracción, esqueleto, pesos y fusión. Conserva tanto la salida normalizada
como `restored/restored.glb` en las coordenadas físicas originales.
La procedencia incluye la licencia, autor, handoff, revisión, hashes originales,
transformaciones y evidencia de validación. El resultado permanece candidato.

## Diferencia con la entrada actual

Al inspeccionar `lab/corpus.json`, la entrada aceptada por `lab.py` es:

- `human`: Man, fuente `HMnuH5geEG`, malla `BaseHuman`.
- `quadruped`: Wolf, fuente `P1gU3Qkr9r`, malla `Wolf`.

La preparación del corpus espera modelos del catálogo con una malla y rig
originales; elimina rig/animación de la copia y normaliza la dimensión mayor a
2 m. Los candidatos nuevos se reciben por el adaptador, sin ampliar esos IDs ni
sobrescribir sus preparaciones, inferencias o mapas anatómicos.

El adaptador recibe geometría estática con ejes declarados. Prepara las mallas
en coordenadas de mundo y registra las matrices de normalización e inversa:
escala uniforme hasta dimensión mayor de 2 m, centrado XY y suelo Z=0. Después
del rigging aplica la inversa a la jerarquía completa, incluidos los huesos.
Comprueba geometría, asignación de materiales, UV, texturas, dimensiones y pesos
al exportar y reimportar. No se usa la restauración para corregir cambios de
geometría o apariencia producidos por el motor: esos cambios son fallos.

Un robot de ruedas puede requerir articulaciones rígidas; decidir rigging por
función antes de usar un autorig orgánico. La prueba técnica con el canario no
certifica anatomía, pivotes ni calidad de deformación de un asset de producción.

## Concurrencia y publicación

El humano, cuadrúpedo y la galería de deformación conservan sus interfaces e
inventarios. El adaptador reutiliza el lock de UniRig, el runner de procesos,
los checkpoints locales y los registros de error existentes. Los nuevos runs
no actualizan los punteros `rig-human`, `rig-quadruped` ni el inventario visual.
La revisión anatómica de un candidato genérico requiere un mapa específico;
no se le asigna automáticamente el mapa de un humano o cuadrúpedo.

El constructor actual publica un inventario explícito que excluye el laboratorio.
No agregar runs ni dependencias a ese inventario. El verificador actual escanea
código de `creation-lab/.local` aunque Git lo ignore: no guardar secretos,
conversaciones, entornos o enlaces simbólicos allí. Los renders/GLB locales son
evidencia del trabajo, no una publicación automática.

Para operar el receptor y revisar deformaciones, leer [gg3d-rigging](../../.agents/skills/gg3d-rigging/SKILL.md) y [lab/STATUS.md](../../lab/STATUS.md). La validación de la fuente y la restauración comprobada no aprueban el rig para clips.
