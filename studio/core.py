"""Portable contracts and immutable evidence for the unified 3D lab."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import struct
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

GATES = ('technical', 'visual', 'content', 'provenance')
STATUSES = ('PASS', 'FAIL', 'BLOCKED', 'NOT_RUN')
ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,95}$')


def now():
    return datetime.now(timezone.utc).isoformat()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f'nonfinite JSON number: {value}')


def read_json(path: Path) -> dict:
    result = json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=_pairs, parse_constant=_reject_constant)
    if not isinstance(result, dict):
        raise ValueError('expected a JSON object')
    return result


def write_json(path: Path, data: dict) -> None:
    path = Path(path)
    encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def checked_path(root: Path, relative: str, must_exist: bool = True) -> Path:
    relative = os.fspath(relative)
    if not relative or '\\' in relative or ':' in relative or '\x00' in relative:
        raise ValueError('invalid artifact path')
    pieces = relative.split('/')
    if relative.startswith('/') or any(piece in ('', '.', '..') for piece in pieces):
        raise ValueError('artifact path must be a normalized relative path')
    root = Path(root)
    if root.is_symlink():
        raise ValueError('artifact root cannot be a symlink')
    root = root.resolve()
    candidate = root
    for piece in pieces:
        candidate = candidate / piece
        if candidate.is_symlink():
            raise ValueError('symlinks are not permitted in artifacts')
    if not candidate.resolve().is_relative_to(root):
        raise ValueError('artifact escapes root')
    if must_exist and not candidate.is_file():
        raise ValueError(f'artifact is not a regular file: {relative}')
    return candidate


def create_run(workspace: Path, operation: str, inputs: dict) -> Path:
    if not operation or not isinstance(inputs, dict):
        raise ValueError('operation and input object required')
    workspace = Path(workspace).resolve()
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex[:10]
    run = checked_path(workspace, 'runs/' + run_id, False)
    run.mkdir(parents=True, exist_ok=False)
    (run / 'events').mkdir()
    write_json(run / 'run.json', {'schemaVersion':1, 'kind':'run', 'id':run_id,
        'operation':operation, 'inputs':inputs, 'createdAt':now(),
        'gates':{gate:'NOT_RUN' for gate in GATES}})
    return run


def record_event(run: Path, event: dict) -> Path:
    if not checked_path(Path(run), 'run.json').is_file():
        raise ValueError('unknown run')
    data = {**event, 'recordedAt':now(), 'eventId':uuid.uuid4().hex}
    encoded = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + hashlib.sha256(encoded.encode()).hexdigest()[:16] + '.json'
    path = checked_path(Path(run), 'events/' + name, False)
    with path.open('x', encoding='utf-8') as handle:
        handle.write(encoded)
    return path


def _required(data, *keys):
    for key in keys:
        if key not in data:
            raise ValueError(f'missing {key}')


def _finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError('nonfinite number')
    if isinstance(value, dict):
        for child in value.values(): _finite(child)
    elif isinstance(value, list):
        for child in value: _finite(child)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _vector(value, positive=False):
    if not isinstance(value, list) or len(value) != 3 or not all(_number(x) and (x > 0 if positive else True) for x in value):
        raise ValueError('expected a finite three-vector' + (' with positive scale' if positive else ''))


BUILTIN_ASSETS = ('button','servo','character')
MICROBIT_BUTTONS = ('a','b','logo')
LED_CHANNEL = re.compile(r'led\.[0-4]\.[0-4]')


def _channel(value):
    return isinstance(value,str) and (value in ('pressed','angle') + MICROBIT_BUTTONS or LED_CHANNEL.fullmatch(value) is not None)


def _channel_range(channel):
    if channel == 'angle': return (-180,180)
    return (0,1) if channel in ('pressed',) + MICROBIT_BUTTONS else (0,255)


def _grid(value):
    return (isinstance(value,list) and len(value)==5 and all(isinstance(row,list) and len(row)==5
            and all(_number(cell) and 0<=cell<=255 for cell in row) for row in value))


def _identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('invalid identifier')


def _coordinates(data):
    if not isinstance(data, dict) or data.get('units') not in ('m','mm') or data.get('up') not in ('X','Y','Z') or data.get('front') not in ('+X','-X','+Y','-Y','+Z','-Z') or data['front'][1] == data['up']:
        raise ValueError('explicit orthogonal units/up/front required')


def validate_record(data: dict) -> dict:
    if not isinstance(data, dict) or data.get('schemaVersion') != 1:
        raise ValueError('unsupported schemaVersion; expected 1')
    _finite(data)
    kind = data.get('kind')
    _identifier(data.get('id'))
    if kind == 'brief':
        _required(data,'goal','targetRuntime','coordinates','dimensionsMeters','budgets','references','style','provenance','acceptanceGates')
        if not all(isinstance(data[key],str) and data[key].strip() for key in ('goal','targetRuntime','style')):
            raise ValueError('brief goal, target runtime and style required')
        _coordinates(data['coordinates']); _vector(data['dimensionsMeters'],True); _provenance(data['provenance'])
        for key in ('triangles','drawCalls','textureSize'):
            value=data['budgets'].get(key)
            if not isinstance(value,int) or isinstance(value,bool) or value<=0: raise ValueError('positive integer budget required: '+key)
        if not isinstance(data['references'],list) or set(data['acceptanceGates'])!=set(GATES):
            raise ValueError('brief references and all acceptance gates required')
    elif kind == 'scene':
        _required(data, 'title', 'duration', 'mode', 'instances')
        if not _number(data['duration']) or not 0 < data['duration'] <= 300 or data['mode'] not in ('interactive','timeline'):
            raise ValueError('invalid scene duration or mode')
        if not isinstance(data['title'],str) or not data['title'].strip(): raise ValueError('scene title required')
        if not isinstance(data['instances'],list) or not data['instances'] or len(data['instances']) > 100:
            raise ValueError('scene requires 1..100 instances')
        ids = set()
        for instance in data['instances']:
            if not isinstance(instance,dict): raise ValueError('instance must be an object')
            _required(instance,'id','asset','position','rotation','scale')
            _identifier(instance['id'])
            if instance['id'] in ids: raise ValueError('duplicate instance ID')
            ids.add(instance['id'])
            if not isinstance(instance['asset'],str): raise ValueError('asset identifier required')
            asset = instance['asset']
            if asset not in BUILTIN_ASSETS and not re.fullmatch(r'(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_.-]+\.glb',asset):
                raise ValueError('asset must be a built-in or relative GLB path')
            if '..' in asset.split('/'): raise ValueError('asset escapes project')
            if 'behavior' in instance and (instance['behavior']!='microbit' or asset in BUILTIN_ASSETS):
                raise ValueError("behavior must be 'microbit' on a GLB asset")
            _vector(instance['position']); _vector(instance['rotation']); _vector(instance['scale'],True)
        channels = set()
        tracks = data.get('tracks',[])
        if not isinstance(tracks,list): raise ValueError('tracks must be an array')
        for track in tracks:
            if not isinstance(track,dict): raise ValueError('track must be an object')
            _required(track,'target','channel','keyframes')
            if not isinstance(track['target'],str) or not _channel(track['channel']): raise ValueError('unknown track channel')
            channel = (track['target'],track['channel'])
            if track['target'] not in ids or channel in channels:
                raise ValueError('unknown or multiply-owned track channel')
            channels.add(channel)
            owner = next(item for item in data['instances'] if item['id']==track['target'])
            kind_of = track['channel']
            if (kind_of=='pressed' and owner['asset']!='button') or (kind_of=='angle' and owner['asset']!='servo') \
               or (kind_of not in ('pressed','angle') and owner.get('behavior')!='microbit'):
                raise ValueError('track channel not supported by asset')
            low,high = _channel_range(kind_of)
            frames = track['keyframes']
            if not isinstance(frames,list) or not frames: raise ValueError('keyframes required')
            previous = -1
            for frame in frames:
                if not isinstance(frame,dict): raise ValueError('keyframe must be an object')
                _required(frame,'time','value')
                if not _number(frame['time']) or not previous < frame['time'] <= data['duration'] or frame['time'] < 0 or not _number(frame['value']):
                    raise ValueError('keyframe times must strictly increase within duration')
                if not low <= frame['value'] <= high: raise ValueError(f'{kind_of} value out of range')
                previous = frame['time']
        bindings=data.get('bindings',[])
        if not isinstance(bindings,list) or len(bindings)>100: raise ValueError('bindings must be an array of at most 100 controls')
        owners={item['id']:item['asset'] for item in data['instances']}
        targets=set()
        for binding in bindings:
            fields={'source','sourceChannel','target','targetChannel','released','pressed'}
            if not isinstance(binding,dict) or set(binding)!=fields: raise ValueError('invalid binding fields')
            if (not isinstance(binding['source'],str) or not isinstance(binding['target'],str)
                or owners.get(binding['source'])!='button' or owners.get(binding['target'])!='servo'
                or binding['sourceChannel']!='pressed' or binding['targetChannel']!='angle'):
                raise ValueError('bindings support only button pressed to servo angle')
            if binding['target'] in targets: raise ValueError('binding target has multiple owners')
            targets.add(binding['target'])
            if any(not _number(binding[key]) or not -180<=binding[key]<=180 for key in ('released','pressed')):
                raise ValueError('binding angles must be finite within -180..180')
        patterns=data.get('patternBindings',[])
        if not isinstance(patterns,list) or len(patterns)>100: raise ValueError('patternBindings must be an array of at most 100 entries')
        behaviors={item['id']:item.get('behavior') for item in data['instances']}
        pairs=set()
        for pattern in patterns:
            if not isinstance(pattern,dict) or set(pattern)!={'source','target','released','pressed'}: raise ValueError('invalid pattern binding fields')
            if pattern['source'] not in MICROBIT_BUTTONS or not isinstance(pattern['target'],str) or behaviors.get(pattern['target'])!='microbit':
                raise ValueError('pattern binding needs source a|b|logo and a microbit target')
            pair=(pattern['source'],pattern['target'])
            if pair in pairs: raise ValueError('duplicate pattern binding for source and target')
            pairs.add(pair)
            if not _grid(pattern['released']) or not _grid(pattern['pressed']): raise ValueError('pattern grids must be 5x5 numbers within 0..255')
        if 'camera' in data:
            camera=data['camera']
            if (not isinstance(camera,dict) or set(camera)!={'elevation','azimuth'} or not _number(camera['elevation']) or not _number(camera['azimuth'])
                or not 5<=camera['elevation']<=89 or not -180<=camera['azimuth']<=180):
                raise ValueError('camera needs finite elevation 5..89 and azimuth -180..180 degrees')
    elif kind == 'project':
        _required(data,'title','scene','files','provenance')
        _inventory(data['files'])
        if data['scene'] not in [entry['path'] for entry in data['files']]: raise ValueError('scene absent from inventory')
        _provenance(data['provenance'])
        if data.get('brief') and data['brief'] not in [entry['path'] for entry in data['files']]: raise ValueError('brief absent from inventory')
    elif kind == 'asset':
        _required(data,'revision','artifacts','coordinates','bounds','provenance','capabilities')
        _identifier(data['revision']); _inventory(data['artifacts']); _coordinates(data['coordinates'])
        _vector(data['bounds'],True); _provenance(data['provenance'])
        if not isinstance(data['capabilities'],list): raise ValueError('capabilities must be a list')
    elif kind == 'rig':
        _required(data,'asset','skeletonHash','joints','coordinates','provenance')
        _hash(data['skeletonHash']); _coordinates(data['coordinates']); _provenance(data['provenance'])
        joints=data['joints']
        if not isinstance(joints,list) or not joints: raise ValueError('joints required')
        names=set()
        for joint in joints:
            _required(joint,'name','parent')
            if joint['name'] in names or (joint['parent'] is not None and joint['parent'] not in names): raise ValueError('joint hierarchy must be unique and parent-first')
            names.add(joint['name'])
    elif kind == 'motion':
        _required(data,'skeletonHash','duration','sampleRate','rootMotion','artifacts','provenance')
        _hash(data['skeletonHash']); _inventory(data['artifacts']); _provenance(data['provenance'])
        if not _number(data['duration']) or data['duration']<=0 or not _number(data['sampleRate']) or not 0<data['sampleRate']<=240 or data['rootMotion'] not in ('in-place','world'):
            raise ValueError('invalid motion duration, rate or root-motion policy')
    elif kind == 'run':
        _required(data,'operation','inputs','createdAt','gates')
        if not isinstance(data['inputs'],dict): raise ValueError('run inputs must be an object')
        for gate in GATES:
            if data['gates'].get(gate) not in STATUSES: raise ValueError('invalid gate')
    elif kind == 'package':
        _required(data,'files','reviews'); _inventory(data['files'])
        for gate in GATES:
            review=data['reviews'].get(gate,{})
            if review.get('status') != 'PASS': raise ValueError(f'{gate} review is not PASS')
            _required(review,'path','sha256'); _hash(review['sha256'])
    else:
        raise ValueError(f'unknown record kind: {kind}')
    return data


def _hash(value):
    if not isinstance(value,str) or not re.fullmatch('[0-9a-f]{64}',value): raise ValueError('SHA-256 required')


def _provenance(value):
    if not isinstance(value,dict) or not all(isinstance(value.get(k),str) and value[k].strip() for k in ('author','license','source')):
        raise ValueError('author, license and source provenance required')


def _inventory(files):
    if not isinstance(files,list) or not files: raise ValueError('nonempty artifact inventory required')
    seen=set()
    for entry in files:
        _required(entry,'path','sha256'); _hash(entry['sha256'])
        path=entry['path']
        if not isinstance(path,str) or path in seen: raise ValueError('duplicate/invalid inventory path')
        # Validate syntax independently of filesystem existence.
        if not path or path.startswith('/') or '\\' in path or ':' in path or any(p in ('','.','..') for p in path.split('/')):
            raise ValueError('invalid inventory path')
        seen.add(path)


def verify_inventory(root: Path, files: list) -> list[Path]:
    _inventory(files)
    paths=[]
    for entry in files:
        path=checked_path(root,entry['path'])
        if sha256(path)!=entry['sha256']: raise ValueError(f'artifact hash mismatch: {entry["path"]}')
        paths.append(path)
    return paths


def validate_glb(path: Path) -> dict:
    path=Path(path)
    size=path.stat().st_size
    if size<20 or size>1024*1024*1024: raise ValueError('GLB size outside 20 bytes..1 GiB')
    with path.open('rb') as handle:
        magic,version,length=struct.unpack('<III',handle.read(12))
        if magic!=0x46546C67 or version!=2 or length!=size: raise ValueError('invalid GLB header/length')
        chunks=[]; document=None
        while handle.tell()<size:
            header=handle.read(8)
            if len(header)!=8: raise ValueError('truncated GLB chunk')
            chunk_length,chunk_type=struct.unpack('<II',header)
            if chunk_length%4 or handle.tell()+chunk_length>size: raise ValueError('invalid GLB chunk length')
            if not chunks and chunk_type!=0x4E4F534A: raise ValueError('GLB JSON must be first')
            if chunk_type==0x4E4F534A:
                if document is not None or chunk_length>32*1024*1024: raise ValueError('invalid GLB JSON chunk')
                document=json.loads(handle.read(chunk_length).decode('utf-8'),object_pairs_hook=_pairs,parse_constant=_reject_constant)
            else: handle.seek(chunk_length,1)
            chunks.append(chunk_type)
        if not isinstance(document,dict) or document.get('asset',{}).get('version')!='2.0': raise ValueError('glTF 2.0 asset required')
        for item in document.get('buffers',[])+document.get('images',[]):
            uri=item.get('uri')
            if uri and not uri.startswith('data:'): raise ValueError('external resource in GLB')
    return {'version':2,'bytes':size,'sha256':sha256(path),'meshes':len(document.get('meshes',[])),
            'skins':len(document.get('skins',[])), 'animations':[{'name':a.get('name',''),'channels':len(a.get('channels',[]))} for a in document.get('animations',[])],
            'scope':'container-and-embedded-resource-check; not full glTF or visual validation'}


def build_package(root: Path, manifest: dict, output: Path) -> dict:
    validate_record(manifest)
    if manifest['kind']!='package': raise ValueError('package manifest required')
    paths=verify_inventory(root,manifest['files'])
    expected={entry['path']:entry['sha256'] for entry in manifest['files']}
    entries={entry['path']:path for entry,path in zip(manifest['files'],paths)}
    hashes=dict(expected)
    for gate in GATES:
        review=manifest['reviews'][gate]
        path=checked_path(root,review['path'])
        reviewed=path.read_bytes()
        if hashlib.sha256(reviewed).hexdigest()!=review['sha256']: raise ValueError('review hash mismatch')
        report=json.loads(reviewed.decode('utf-8-sig'),object_pairs_hook=_pairs,parse_constant=_reject_constant)
        if not isinstance(report,dict) or report.get('status')!='PASS' or report.get('subjects')!=expected:
            raise ValueError('review must approve this exact artifact inventory')
        if review['path'] in hashes and hashes[review['path']]!=review['sha256']: raise ValueError('conflicting review hash')
        entries[review['path']]=path
        hashes[review['path']]=review['sha256']
    for name in entries:
        if name=='package.json' or any(part.startswith('.') or part in ('node_modules','__pycache__') for part in name.split('/')):
            raise ValueError('private/build path cannot enter package')
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    # Hash the very chunks written into the archive, not a previous read of the path.
    # Exclusive creation preserves earlier deliveries; only our partial output is removed.
    try: destination=output.open('xb')
    except FileExistsError: raise ValueError('package output already exists') from None
    try:
        with destination, zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('package.json',json.dumps(manifest,indent=2,allow_nan=False))
            for name in entries:
                path=checked_path(root,name)
                digest=hashlib.sha256()
                with path.open('rb') as source, archive.open(name,'w') as member:
                    while chunk:=source.read(1024*1024):
                        digest.update(chunk); member.write(chunk)
                if digest.hexdigest()!=hashes[name]: raise ValueError('artifact hash mismatch during archive: '+name)
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return {'status':'PASS','path':str(output),'sha256':sha256(output),'files':len(entries), 'published':False}
