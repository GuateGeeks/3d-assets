"""Offline promotion of reviewed native references; never replaces an asset."""
import argparse
import copy
import shutil
import zipfile
from pathlib import Path

from acquire_institutions import ROOT, read, save, sha
from catalog import inspect, license_info


def merge_groups(existing, incoming):
    result = copy.deepcopy(existing)
    result.setdefault('schemaVersion', 1)
    groups = {group['id']: group for group in result.setdefault('groups', [])}
    for group in incoming.get('groups', []):
        if group['id'] in groups:
            old = groups[group['id']]
            old['modelIds'] = list(dict.fromkeys(old['modelIds'] + group['modelIds']))
        else:
            addition = copy.deepcopy(group)
            result['groups'].append(addition)
            groups[group['id']] = addition
    aliases = result.setdefault('aliases', [])
    for alias in incoming.get('aliases', []):
        if alias not in aliases:
            aliases.append(copy.deepcopy(alias))
    return result


def promote(run):
    from PIL import Image
    acquisition = read(run / 'acquisition.json')
    duplicate = read(run / 'deduplication.json')
    visual = read(run / 'visual-review.json')
    if visual['result'] != 'PASS' or duplicate['baselineModels'] != duplicate['baselineFingerprintCount']:
        raise ValueError('Incomplete review')
    compared = {x['id']: x for x in duplicate['comparisons']}
    if not {x['id'] for x in acquisition['items']} <= set(compared):
        raise ValueError('Comparison inventory differs from acquisition')
    if set(visual['eligibleIds']) != {x['id'] for x in acquisition['items']}:
        raise ValueError('Visual review eligibility differs from promotion inventory')
    for relative, digest in read(run / 'baseline-model-files.json').items():
        if sha(ROOT / relative) != digest:
            raise ValueError('Baseline changed: ' + relative)
    for relative, digest in visual['images'].items():
        if sha(run / relative) != digest:
            raise ValueError('Visual review image changed')
    for item in acquisition['items']:
        mid = item['id']
        assessment = read(run / 'prepared' / mid / 'review.json')
        if assessment['technical'] != 'PASS' or assessment['glbSha256'] != item['sha256']:
            raise ValueError('Technical review mismatch')
        if (ROOT / 'models' / mid).exists():
            raise ValueError('Refusing to replace an existing model')
        row = compared[mid]
        if row['geometryMatches'] or row['geometryPeerMatches']:
            raise ValueError('Geometry match requires explicit individual review')
    evidence = ROOT / 'sources/external/institutions' / run.name
    evidence.mkdir(parents=True, exist_ok=False)
    save(evidence / 'deduplication.json', duplicate)
    public_review = copy.deepcopy(visual)
    public_review['images'] = {}
    for relative, digest in visual['images'].items():
        destination = evidence / 'review' / Path(relative).name
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(run / relative, destination)
        public_review['images'][destination.relative_to(ROOT).as_posix()] = digest
    save(evidence / 'visual-review.json', public_review)
    area_plan = read(ROOT / 'selection.json')
    dependencies = read(ROOT / 'gallery/dependencies.json')
    groups, aliases, added = {}, [], []
    for item in acquisition['items']:
        mid = item['id']
        comparison = compared[mid]
        family = item['family']
        canonical = comparison['exactMatches'][0] if comparison['exactMatches'] else mid
        group = groups.setdefault(family, {'id': family, 'title': family,
                                           'relation': 'functional-family-or-variant', 'modelIds': []})
        if canonical not in group['modelIds']:
            group['modelIds'].append(canonical)
        if canonical != mid:
            aliases.append({'id': mid, 'canonicalId': canonical, 'sourceUrl': item['sourceUrl'],
                            'reason': 'Identical native GLB SHA-256; no duplicate asset copied'})
            continue
        folder = ROOT / 'models' / mid
        folder.mkdir()
        prepared = run / 'prepared' / mid
        shutil.copyfile(prepared / 'model.glb', folder / 'model.glb')
        if sha(folder / 'model.glb') != item['sha256']:
            raise ValueError('Native GLB changed during copy')
        source = evidence / mid
        source.mkdir()
        metadata_path = Path(item['sourceMetadata'])
        if not metadata_path.is_file():
            # Acquisition may have run in WSL and promotion in native Windows.
            metadata_path = run / ('downloads/' + mid + '/metadata.json' if item['providerId'] == 'sketchfab'
                                   else Path(item['sourceMetadata']).name)
        shutil.copyfile(metadata_path, source / 'metadata.json')
        license_data = license_info(item['licenseRaw'])
        if item['providerId'] == 'nasa':
            license_data = {'id': 'LicenseRef-NASA-Media-Usage-Guidelines', 'url': item['licenseUrl'],
                            'attributionRequired': True, 'commercialUse': None, 'derivatives': None,
                            'shareAlike': False,
                            'conditions': 'Uso educativo e informativo sujeto a las condiciones NASA. No implica aval de NASA. Sus insignias y logotipos tienen protección específica; comprobar usos comerciales y material de terceros. No se declara CC0.'}
        changes = 'Ninguna: GLB nativo sin conversión, decimación, cambios de textura, escala, ejes, materiales ni animaciones. Miniatura renderizada por GuateGeeks.'
        credit = ('"' + item['titleOriginal'] + '", por ' + item['author'] + ' / ' + item['provider'] + '. '
                  + item['sourceUrl'] + '. ' + item['licenseRaw'] + ': ' + item['licenseUrl'] + '.')
        if item['providerId'] == 'sketchfab':
            captured = read(source / 'metadata.json')
            rights = {'sourceUrl': 'https://api.sketchfab.com/v3/models/' + item['asset'],
                      'modelUid': item['asset'], 'isDownloadable': captured['isDownloadable'],
                      'license': captured['license'], 'author': captured['user']['displayName'],
                      'retrievedAt': item['retrievedAt']}
        elif item['providerId'] == 'smithsonian':
            rights = {'sourceUrl': 'https://api.si.edu/openaccess/api/v1.0/search',
                      'objectRecordId': item['objectRecordId'], 'packageId': item['asset'],
                      'mediumUsageAccess': 'CC0', 'selectedResource': item['selectedResource'],
                      'retrievedAt': item['retrievedAt'],
                      'scope': 'The matched 3d_voyager medium is CC0; other media in a record can have different rights.'}
        else:
            rights = {'sourceUrl': item['licenseUrl'], 'pageSha256': sha(run / 'nasa-usage.txt'),
                      'sourceRecord': item['sourceUrl'], 'creditedSource': item['author'],
                      'scope': 'Educational and informational reference under NASA media guidelines; no endorsement or trademark rights granted.',
                      'retrievedAt': item['retrievedAt'], 'license': license_data}
        save(source / 'license-evidence.json', rights)
        assessment = read(prepared / 'review.json')
        public_assessment = copy.deepcopy(assessment)
        public_assessment['images'] = {}
        for name, digest in assessment['images'].items():
            if sha(prepared / name) != digest:
                raise ValueError('Technical render changed')
            destination = source / 'renders' / name
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(prepared / name, destination)
            public_assessment['images'][destination.relative_to(ROOT).as_posix()] = digest
        save(source / 'technical-review.json', public_assessment)
        text = credit + '\n\nCambios: ' + changes + '\n'
        if license_data.get('conditions'):
            text += '\nCondiciones: ' + license_data['conditions'] + '\n'
        if license_data['commercialUse'] is False:
            text += '\nNo permite uso comercial. Las adaptaciones conservan la condición ShareAlike cuando corresponda.\n'
        (folder / 'LICENSE.txt').write_text(text, encoding='utf-8')
        with zipfile.ZipFile(folder / 'originals.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.write(folder / 'model.glb', 'model.glb')
            archive.write(folder / 'LICENSE.txt', 'LICENSE.txt')
        provenance = {
            'pack': item['provider'] + ' native GLB', 'sourceMember': 'model.glb',
            'originalFiles': [{'file': 'models/' + mid + '/model.glb', 'url': item['downloadUrl'],
                               'bytes': item['bytes'], 'sha256': item['sha256']}],
            'originalDownloadSha256': sha(folder / 'originals.zip'),
            'nativeBytesUnchanged': True, 'conversionTool': None,
            'renderTool': 'Blender ' + assessment['blenderVersion'],
            'dimensionsBlender': assessment['dimensionsBlender'],
            'scaleInterpretation': 'Native numeric dimensions retained; do not assume scientifically verified real-world scale.'}
        for key, path in [('licenseEvidence', source / 'license-evidence.json'),
                          ('metadataEvidence', source / 'metadata.json'),
                          ('technicalReviewEvidence', source / 'technical-review.json'),
                          ('visualReviewEvidence', evidence / 'visual-review.json')]:
            provenance[key] = path.relative_to(ROOT).as_posix()
            provenance[key + 'Sha256'] = sha(path)
        metadata = {
            'id': mid, 'assetId': item['providerId'] + ':' + item['asset'],
            'providerId': item['providerId'], 'provider': item['provider'],
            'title': item['title'], 'titleOriginal': item['titleOriginal'],
            'author': item['author'], 'authorUrl': item['authorUrl'],
            'sourceUrl': item['sourceUrl'], 'metadataUrl': rights['sourceUrl'],
            'downloadUrl': item['downloadUrl'], 'thumbnailUrl': None,
            'description': item['reason'] + ' Uso curricular y exactitud científica pendientes de revisión docente.',
            'category': 'Referencias científicas y educativas', 'tags': [item['titleOriginal'], family],
            'areas': item['areas'], 'queries': [], 'products': ['code-studio', 'socrates'],
            'subjects': sorted({s for a in area_plan['areas'] if a['id'] in item['areas'] for s in a['subjects']}),
            'licenseRaw': item['licenseRaw'], 'license': license_data,
            'attribution': credit, 'modifications': changes,
            'file': 'models/' + mid + '/model.glb',
            'sourceMetadataFile': (source / 'metadata.json').relative_to(ROOT).as_posix(),
            'originalDownload': 'models/' + mid + '/originals.zip',
            'bytes': item['bytes'], 'sha256': item['sha256'],
            'apiTriangleCount': None, 'apiAnimated': None, 'gltf': inspect((folder / 'model.glb').read_bytes()),
            'retrievedAt': item['retrievedAt'], 'reviewStatus': 'pending',
            'educationalReview': 'Uso curricular, escala y precisión científica pendientes de revisión docente.',
            'reviewFlags': ['scientific-reference-review'] + (['noncommercial-license'] if license_data['commercialUse'] is False else []),
            'unfulfilledQueries': [], 'provenance': provenance,
            'qa': {'technical': 'PASS', 'visual': 'PASS', 'rights': 'PASS', 'educational': 'NOT_RUN',
                   'geometryFingerprint': comparison['geometryFingerprint']}}
        save(folder / 'metadata.json', metadata)
        save(folder / 'source.json', {'Provider': item['provider'], 'Source': item['sourceUrl'],
                                     'Licence': item['licenseRaw'], 'Attribution': credit})
        thumb = ROOT / 'gallery/thumbnails' / (mid + '.webp')
        Image.open(prepared / 'source-three-quarter.png').convert('RGB').save(thumb, 'WEBP', quality=88)
        dependencies['thumbnails'].append({'id': mid, 'file': thumb.relative_to(ROOT).as_posix(),
                                           'url': None, 'sha256': sha(thumb), 'modelLicense': item['licenseRaw'],
                                           'origin': 'Own CPU render of native GLB; same model license and credit'})
        added.append(mid)
    save(ROOT / 'gallery/dependencies.json', dependencies)
    group_path = ROOT / 'groups/institutions.json'
    existing = read(group_path) if group_path.exists() else {'schemaVersion': 1, 'groups': [], 'aliases': []}
    save(group_path, merge_groups(existing, {'groups': list(groups.values()), 'aliases': aliases}))
    save(evidence / 'promotion.json', {'added': added, 'aliases': aliases, 'baselineModels': duplicate['baselineModels'],
                                      'nativeBytesUnchanged': True, 'educationalReview': 'NOT_RUN'})
    print('PROMOTED', len(added), 'ALIASES', len(aliases))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    promote(parser.parse_args().run)
