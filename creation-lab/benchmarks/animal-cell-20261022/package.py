"""Package selected benchmark artifacts without changing the original runs."""
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
OUTPUT = BASE.parents[1] / '.local/benchmarks/animal-cell-20261022'


def main():
    results = json.loads((BASE/'results.json').read_text(encoding='utf-8'))
    destination = OUTPUT/'deliveries'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination.mkdir(parents=True, exist_ok=False)
    archive = destination/'celula-animal-seis-alternativas.zip'
    inventory = []
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        for name in ['README.md','RESULTS.md','brief.json','protocol.json','authoring-receipt.json',
                     'results.json','reviews.json','format-validation.json','repairs.json',
                     'HARNESS-NOTES.md','viewer-http-validation.json',
                     'viewer-ui-validation.json','integration-validation.json']:
            package.write(BASE/name, 'benchmark/'+name)
        for review in sorted((BASE/'reviews-blind').rglob('*.json')):
            package.write(review, 'benchmark/'+review.relative_to(BASE).as_posix())
        for entry in results['entries']:
            run = ROOT/entry['artifactDirectory']
            for file in sorted(run.rglob('*')):
                rel = file.relative_to(run).as_posix()
                if not file.is_file() or not (rel in {'asset.glb','source.blend','parts.json','generator.py','manifest.json','COMPLETE','build-checks.json','source-quality.json','build-result.json','reopen-result.json','reimport-result.json'} or rel.startswith('renders/')):
                    continue
                name = entry['id']+'/'+rel
                digest = hashlib.sha256(file.read_bytes()).hexdigest()
                inventory.append({'path':name,'sha256':digest,'bytes':file.stat().st_size,'runId':entry['runId']})
                package.write(file, name)
        package.writestr('CONTENIDO.json', json.dumps({'schemaVersion':1,'files':inventory}, ensure_ascii=False,indent=2)+'\n')
        package.writestr('LEEME.txt', 'Célula animal para secundaria, etiquetas en español.\nCada carpeta A-F contiene un GLB, su fuente Blender y partes/funciones en parts.json.\nConsulta benchmark/RESULTS.md: las propuestas tienen distintas calificaciones; un archivo disponible no implica aprobación biológica.\nLa evidencia completa e intentos iniciales permanecen en el repositorio local. Los manifiestos originales incluyen hashes de esa evidencia, incluso archivos no incluidos en este paquete.\nEl visor interactivo se inicia desde el repositorio según benchmark/README.md.\nGeometría procedural original; declaración de licencia CC0-1.0 en brief.json.\n')
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:raise ValueError('ZIP integrity failure')
    receipt = {'path':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
               'bytes':archive.stat().st_size,'files':len(inventory),'zipIntegrity':'PASS'}
    (destination/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':main()
