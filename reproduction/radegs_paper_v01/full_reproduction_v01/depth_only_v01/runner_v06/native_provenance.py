"""Resolve the current build's provenance, never an older hard-coded manifest."""
import json,hashlib
from pathlib import Path

def provenance_for(c):
 p=Path(c['native_build_manifest']);m=json.loads(p.read_text())
 if m['native_sha256']!=c['inputs']['native']:raise ValueError('native/config provenance mismatch')
 return {'source_manifest_path':str(p),'source_manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'native_sha256':m['native_sha256'],'native_path':m['native'],'numerical_revision':c['numerical_revision']}
