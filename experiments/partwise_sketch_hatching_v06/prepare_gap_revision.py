"""Preserve pre-evaluation cache-schema failure and freeze the narrow adapter fix."""
import runtime
from runtime import ACTIVE_UNIT as UNIT,sha,js,now
from pathlib import Path
import json
import shutil
from run_gap_unit import cache

assert UNIT.name=='unit_005'
p=json.loads((UNIT/'PROTOCOL.json').read_text())
failure=json.loads((UNIT/'logs/build_001.receipt.json').read_text());assert failure['returncode']==1
assert not (UNIT/'BUILD_MATCH.json').exists() and not (UNIT/'dev').exists() and not (UNIT/'arc').exists()
assert list((UNIT/'build_match').iterdir())==[]
# Real BUILD cache regression: all four immutable caches must adapt before retry.
for v in (v for v in p['views'] if v['kind']=='build'):
    a=cache(p,v);assert a['old_alpha'].shape==a['support'].shape
archive=UNIT/'interrupted_attempt_001';archive.mkdir(exist_ok=False)
(UNIT/'build_match').rename(archive/'build_match')
here=Path(__file__).resolve().parent;snap=UNIT/'source_snapshot_002'
shutil.copytree(here,snap,ignore=shutil.ignore_patterns('__pycache__'))
js(UNIT/'SOURCE_REVISION_002.json',dict(utc=now(),protocol_sha256=sha(UNIT/'PROTOCOL.json'),
    cause='BUILD cache has legacy_ink and support, not legacy_raw_alpha. Original build_001 failed before rendering any comparison.',
    change='Read old_alpha through unchanged compose(legacy_ink, support). No mechanism, camera, input, budget or evaluation change.',
    regression='All four frozen BUILD caches adapted successfully before retry; source array shapes checked.',
    preserved='Original source_snapshot, PROTOCOL, DECISION, failure rc1/log and empty BUILD directory remain.',
    source_hashes={f.name:sha(f) for f in snap.iterdir() if f.is_file()}))
js(UNIT/'SOURCE_REVISION_002_LOCK.json',dict(sha256=sha(UNIT/'SOURCE_REVISION_002.json'),utc=now()))
print('REVISION_FROZEN',sha(UNIT/'SOURCE_REVISION_002.json'),flush=True)
