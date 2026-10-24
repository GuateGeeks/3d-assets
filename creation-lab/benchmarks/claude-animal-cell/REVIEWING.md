# Revisión ciega · célula animal (benchmark Claude v1)

Revisas **un** run identificado solo por un ID ciego. No conoces ni debes buscar el
modelo autor, el código, otras réplicas ni revisiones previas. Lee únicamente tu
carpeta de paquete y este archivo. No uses web, skills, MCP ni subagentes.

## Paquete

- `brief.json`: encargo, partes, `biologicalChecks` y `blockoutChecks`.
- `packet.json`: ID ciego, etapa (`blockout` o `detail`), lista de checks a evaluar
  en orden, etiquetas y posiciones de etiqueta declaradas por el autor.
- `renders/`: seis imágenes reales: `front`, `side`, `back`, `three-quarter`,
  `wireframe` y `reimport-three-quarter` (GLB reimportado).

## Procedimiento

1. Abre **las seis imágenes** con la herramienta de lectura y calcula su
   `sha256sum`. No juzgues imágenes que no abriste.
2. Para cada una de las trece partes registra `visibility` (`visible`, `hidden`,
   `unclear`), las vistas que lo demuestran y la razón. `views` nunca va vacío: para
   una parte oculta o dudosa lista las vistas donde la buscaste (enmienda v1.3). Un ID o etiqueta no prueba
   que la estructura sea reconocible. Una parte oculta es no evaluable, nunca PASS.
3. Evalúa cada check de `packet.json` en su orden con `PASS`, `FAIL`, `BLOCKED` o
   `NOT_RUN` y una razón observable. En blockout solo se evalúa disposición y
   visibilidad de volúmenes; no certifiques detalle ausente.
4. Dictamina por separado `visual` (lectura, contraste, oclusión, intersecciones,
   coherencia entre fuente y reimportación) y `content` (los checks). `content` PASS
   exige todos los checks PASS y todas las partes visibles. `visual` PASS también
   exige las trece partes `visible`: con alguna `hidden`/`unclear`, ambos gates son
   FAIL o BLOCKED (regla de `iterate.py`; enmienda v1.2).
5. Cada defecto indica `view`, `detail` y `requestedChange` concreto. No escribas ni
   sugieras código. Un FAIL o BLOCKED requiere al menos un defecto accionable.
6. La vista `wireframe` la genera el worker común congelado con un alambre de
   0.18 mm; a esta escala y 768 px las aristas apenas se ven y la imagen se parece
   a tres cuartos. Es igual para todas las réplicas: úsala solo como vista extra si
   muestra algo, y no la cuentes como defecto del autor (enmienda v1.1).
7. Solo en etapa `detail`: puntúa biología visible (0–30), legibilidad (0–25),
   composición (0–15), forma/sombreado (0–15) y utilidad educativa (0–15). Una nota
   alta no anula un gate fallido. En blockout usa `"scores": null`.

## Salida

Escribe `review.json` en tu carpeta de paquete (UTF-8), compruébalo con
`python3 /home/adawolfs/projects/makecode/3d-assets/creation-lab/benchmarks/claude-animal-cell/bench.py lint-review --packet TU_CARPETA`
(solo lee tu paquete; corrige hasta `"valid": true`) y entrega un resumen breve con
`SubagentHandback`:

```json
{"blindId": "...", "openedImages": true,
 "imageSha256": {"front": "...", "side": "...", "back": "...", "three-quarter": "...",
                 "wireframe": "...", "reimport-three-quarter": "..."},
 "visual": {"status": "PASS|FAIL|BLOCKED|NOT_RUN", "reason": "..."},
 "content": {"status": "...", "reason": "..."},
 "parts": [{"id": "membrana", "visibility": "visible", "views": ["three-quarter"], "reason": "..."}],
 "checks": [{"check": "<texto exacto>", "status": "...", "reason": "..."}],
 "defects": [{"view": "front", "detail": "...", "requestedChange": "..."}],
 "scores": {"biology": 0, "readability": 0, "composition": 0, "shapeShading": 0, "educationalUse": 0}}
```

Esta revisión es asistida por un modelo de la misma familia que una de las
condiciones; no representa una evaluación docente externa.
