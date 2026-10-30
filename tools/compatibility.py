"""Validate the explicit inventory of reviewed display-only material derivatives."""
import hashlib,json,math
from pathlib import PurePosixPath
from catalog import inspect

def verify_display_variants(root, site, models):
    manifest=json.loads((root/'gallery/compat/index.json').read_text(encoding='utf-8'))
    native={m['id']:m for m in models};seen=set()
    def checked(path,digest):
        value=PurePosixPath(path)
        if value.is_absolute() or '..' in value.parts or '\\' in path:
            raise ValueError('Unsafe display evidence path')
        raw=(root/path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Display integrity mismatch: '+path)
        if site is not None and (site/path).read_bytes()!=raw:raise ValueError('Stale display artifact: '+path)
        return raw
    for variant in manifest['variants']:
        mid=variant['id'];model=native[mid]
        if mid in seen:raise ValueError('Duplicate display variant')
        seen.add(mid)
        if variant['file']!='gallery/compat/models/'+mid+'.glb':raise ValueError('Unsafe display model path')
        if variant['sourceFile']!=model['file'] or variant['sourceSha256']!=model['sha256']:raise ValueError('Stale display source')
        if variant['licenseRaw']!=model['licenseRaw'] or variant['attribution']!=model['attribution']:raise ValueError('Display rights differ from original')
        if any(variant['qa'].get(key)!='PASS' for key in ['technical','visual','rights']):raise ValueError('Unapproved display variant')
        checked(model['file'],model['sha256']);raw=checked(variant['file'],variant['sha256'])
        if len(raw)!=variant['bytes'] or not inspect(raw)['selfContained']:raise ValueError('Incomplete display GLB')
        report=json.loads(checked(variant['technicalEvidence'],variant['technicalEvidenceSha256']))
        if report['technical']!='PASS' or report['originalSha256']!=model['sha256'] or report['displaySha256']!=variant['sha256']:raise ValueError('Display review mismatch')
        expected_images={'source-three-quarter.png','source-front.png','source-side.png','source-back.png','source-wireframe.png','reimport-three-quarter.png'}
        if set(report['images'])!=expected_images:raise ValueError('Incomplete display render review')
        geometry=json.loads(checked(variant['geometryEvidence'],variant['geometryEvidenceSha256']))
        if geometry['result']!='PASS' or geometry['sourceSha256']!=model['sha256'] or geometry['displaySha256']!=variant['sha256']:raise ValueError('Display geometry evidence mismatch')
        tolerance=geometry['absoluteTolerance'];distances=geometry['maxNearestVertexDistances']
        if not math.isfinite(tolerance) or tolerance<=0 or len(distances)!=2 or any(not math.isfinite(d) or d<0 or d>tolerance for d in distances):raise ValueError('Display geometry changed')
        for name,digest in report['images'].items():checked(str(PurePosixPath(variant['technicalEvidence']).parent/name),digest)
        review=json.loads(checked(variant['visualEvidence'],variant['visualEvidenceSha256']))
        if review['result']!='PASS' or mid not in review['eligibleIds'] or review['displaySha256ById'].get(mid)!=variant['sha256'] or review['sourceSha256ById'].get(mid)!=model['sha256']:raise ValueError('Display visual approval missing')
        if not review['images']:raise ValueError('Display visual images missing')
        for path,digest in review['images'].items():checked(path,digest)
    if site is not None and (site/'gallery/compat/index.json').read_bytes()!=(root/'gallery/compat/index.json').read_bytes():raise ValueError('Stale display manifest')
    return len(seen)
