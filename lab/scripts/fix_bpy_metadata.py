"""Correct the cp39 WHEEL tag shipped inside the official bpy 4.2.0 cp311 wheel."""
import base64
import csv
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def replace(path, data):
    temporary = path.with_name(path.name + '.partial')
    temporary.write_bytes(data)
    os.replace(temporary, path)  # Avoid modifying uv's hard-linked cache files in place.


def main():
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError('This metadata correction is only for the cp311 profile')
    dist = importlib.metadata.distribution('bpy')
    if dist.version != '4.2.0':
        raise RuntimeError('Unexpected bpy version; inspect its wheel instead of patching')
    wheel = Path(dist.locate_file('bpy-4.2.0.dist-info/WHEEL'))
    old = b'Tag: cp39-cp39-manylinux_2_28_x86_64'
    new = b'Tag: cp311-cp311-manylinux_2_28_x86_64'
    original = wheel.read_bytes()
    report_path = ROOT / 'lab/reports/bpy-wheel-metadata.json'
    if new in original and old not in original:
        print('bpy cp311 metadata already corrected')
        return
    if old not in original or original.count(b'Tag: ') != 1:
        raise RuntimeError('Unexpected bpy wheel metadata; refusing to modify it')
    corrected = original.replace(old, new)
    replace(wheel, corrected)
    record = wheel.with_name('RECORD')
    rows = list(csv.reader(io.StringIO(record.read_text())))
    for row in rows:
        if row[0] == 'bpy-4.2.0.dist-info/WHEEL':
            row[1] = 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(corrected).digest()).decode().rstrip('=')
            row[2] = str(len(corrected))
    output = io.StringIO()
    csv.writer(output, lineterminator='\n').writerows(rows)
    replace(record, output.getvalue().encode())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({'package': 'bpy', 'version': '4.2.0',
        'originalTag': old.decode(), 'correctedTag': new.decode(),
        'originalWheelMetadataSha256': hashlib.sha256(original).hexdigest(),
        'correctedWheelMetadataSha256': hashlib.sha256(corrected).hexdigest(),
        'scope': 'installed WHEEL and RECORD metadata only; extension binaries unchanged'}, indent=2) + '\n')
    print('Corrected bpy 4.2.0 cp311 wheel metadata and recorded the change.')


if __name__ == '__main__':
    main()
