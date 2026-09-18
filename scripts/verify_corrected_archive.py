#!/usr/bin/env python3
"""Hash-only verification of preserved archives and frozen original inputs."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.foundation import freeze_json
from src.corrected_reporting import sha256
root=ROOT/'out/multiscene_foundation_corrected';cfg=json.loads((root/'config.json').read_text());records=[]
inputs=json.loads((root/'input_hashes.json').read_text())
for name,item in cfg['frozen_posteriors'].items():inputs[item['path']]=dict(sha256=item['sha256'])
for scene in cfg['scenes'].values():
    for c in scene['cameras'].values():inputs[c['path']]=dict(sha256=c['sha256'])
for name,key,pathkey in [('multiscene_foundation','files','path'),('point_feature_foundation','artifacts','absolute_path')]:
    manifest=ROOT/'out'/name/'MANIFEST.json';archive=json.loads(manifest.read_text());inputs[str(manifest)]=dict(sha256=sha256(manifest))
    for row in archive[key]:
        if row.get('sha256'):inputs[row[pathkey]]=dict(sha256=row['sha256'])
for path,item in sorted(inputs.items()):
    p=Path(path);observed=sha256(p) if p.is_file() else None
    records.append(dict(path=path,expected_sha256=item['sha256'],observed_sha256=observed,passed=observed==item['sha256']))
    if not records[-1]['passed']:print('MISMATCH',path,flush=True)
freeze_json(root/'PRESERVED_INPUT_VERIFICATION.json',dict(passed=all(r['passed'] for r in records),files=len(records),records=records,scope='Hash-only access, including prior archived artifacts and frozen checkpoint/camera-image bytes. No TEST photograph decoding or scientific consumption.'))
print('preserved input hashes',len(records),'passed',all(r['passed'] for r in records),flush=True)
