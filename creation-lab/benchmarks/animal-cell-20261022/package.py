"""Package selected benchmark artifacts without changing the original runs."""
import argparse
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from benchmark_io import contained_file, read_complete_manifest, review_matches_run

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
OUTPUT = BASE.parents[1] / '.local/benchmarks/animal-cell-20261022'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=Path, default=OUTPUT)
    parser.add_argument('--results', type=Path, default=BASE/'results.json')
    parser.add_argument('--output', type=Path, default=None, help='New delivery directory')
    args = parser.parse_args(argv)
    results = json.loads(args.results.read_text(encoding='utf-8-sig'))
    review_path = args.results.parent/'reviews.json'
    review_data = json.loads(review_path.read_text(encoding='utf-8-sig')) if review_path.exists() else {}
    review_entries = review_data.get('entries', []) if isinstance(review_data, dict) else []
    candidates = {review.get('id'):review for review in review_entries if isinstance(review, dict)}
    verified_reviews = []
    selected = []
    for entry in results['entries']:
        if entry.get('id') not in tuple('ABCDEF') or not re.fullmatch(r'[A-Za-z0-9_-]+',entry.get('runId','')):
            raise ValueError('Results must contain completed runs for A-F')
        run = args.runs/entry['id']/entry['runId']
        if not run.resolve().is_relative_to(args.runs.resolve()):
            raise ValueError('Unsafe run path')
        manifest = read_complete_manifest(run)
        if not manifest or hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest()!=entry.get('manifestSha256'):
            raise ValueError(f'Missing or changed completed run: {run}')
        for name, expected in manifest['artifacts'].items():
            if hashlib.sha256(contained_file(run, name).read_bytes()).hexdigest()!=expected:
                raise ValueError(f'Changed artifact: {run}/{name}')
        review = candidates.get(entry['id'])
        verified = review_matches_run(run, review, manifest)
        if verified:verified_reviews.append(review)
        entry = dict(entry)
        entry['technical'] = manifest['technical']
        for field in ('visual','biological'):
            value = review.get(field, 'NOT_RUN') if verified else 'NOT_RUN'
            entry[field] = value.get('status','NOT_RUN') if isinstance(value,dict) else value
        entry['score'] = review.get('score') if verified else None
        selected.append((entry,run))
    if sorted(entry['id'] for entry, _ in selected)!=list('ABCDEF'):
        raise ValueError('Results must contain exactly one run for each A-F condition')
    destination = args.output or OUTPUT/'deliveries'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination.mkdir(parents=True, exist_ok=False)
    archive = destination/'celula-animal-seis-alternativas.zip'
    inventory = []
    results = {**results, 'entries':[entry for entry, _ in selected],
               'sourceResultsSha256':hashlib.sha256(args.results.read_bytes()).hexdigest(),
               'reviewScope':'Only exact-run reviews with matching image, GLB and parts hashes are current.'}
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as package:
        for name in ['README.md','RESULTS.md','brief.json','protocol.json','authoring-receipt.json',
                     'format-validation.json','repairs.json',
                     'HARNESS-NOTES.md','viewer-http-validation.json',
                     'viewer-ui-validation.json','integration-validation.json']:
            package.write(BASE/name, 'benchmark/history/'+name)
        for name in ('results.json','reviews.json'):
            package.write(BASE/name, 'benchmark/history/'+name)
        package.writestr('benchmark/results.json',json.dumps(results,ensure_ascii=False,indent=2)+'\n')
        package.writestr('benchmark/reviews.json',json.dumps({'schemaVersion':1,'entries':verified_reviews},ensure_ascii=False,indent=2)+'\n')
        for review in sorted((BASE/'reviews-blind').rglob('*.json')):
            package.write(review, 'benchmark/history/'+review.relative_to(BASE).as_posix())
        for entry, run in selected:
            for file in sorted(run.rglob('*')):
                rel = file.relative_to(run).as_posix()
                if not file.is_file() or not (rel in {'asset.glb','source.blend','parts.json','generator.py','manifest.json','COMPLETE','build-checks.json','source-quality.json','build-result.json','reopen-result.json','reimport-result.json'} or rel.startswith('renders/')):
                    continue
                name = entry['id']+'/'+rel
                digest = hashlib.sha256(file.read_bytes()).hexdigest()
                inventory.append({'path':name,'sha256':digest,'bytes':file.stat().st_size,'runId':entry['runId']})
                package.write(file, name)
        package.writestr('CONTENIDO.json', json.dumps({'schemaVersion':1,'files':inventory}, ensure_ascii=False,indent=2)+'\n')
        summary = '\n'.join(f'{entry["id"]}: run {entry["runId"]}; técnica {entry["technical"]}; visual {entry["visual"]}; biología {entry["biological"]}; puntos {entry["score"] if entry["score"] is not None else "sin revisión vigente"}.' for entry,_ in selected)
        package.writestr('LEEME.txt', 'Célula animal para secundaria, etiquetas en español.\nCada carpeta A-F contiene los artefactos del run identificado abajo.\nConsulta benchmark/results.json y benchmark/reviews.json para esta selección: sólo incluyen como vigentes las revisiones del run exacto y sus hashes comprobados. La ausencia de revisión no equivale a aprobación educativa.\n\n'+summary+'\n\nbenchmark/history/ contiene exclusivamente el contexto y las calificaciones del piloto original; no califica los nuevos runs de este paquete.\nLos manifiestos originales también incluyen hashes de evidencia no incluida aquí. La evidencia completa se restaura desde los fixtures del repositorio.\nEl visor se inicia desde el repositorio siguiendo creation-lab/benchmarks/animal-cell-20261022/README.md.\nLa declaración original de procedencia y licencia está en benchmark/history/brief.json.\n')
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:raise ValueError('ZIP integrity failure')
    receipt = {'path':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
               'bytes':archive.stat().st_size,'files':len(inventory),'zipIntegrity':'PASS'}
    (destination/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':main()
