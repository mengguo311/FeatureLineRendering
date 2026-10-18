from env import *
from pathlib import PurePosixPath
def safe_member(name):
 p=PurePosixPath(name)
 if not name or p.is_absolute() or '..' in p.parts or '\\' in name or name=='.':raise ValueError('Unsafe member')
 return name
def check_members(root,manifest):
 for f,x in manifest['members'].items():
  safe_member(f);p=Path(root)/f;assert p.is_file() and not p.is_symlink() and sha(p)==x['sha256'],f
def validate_partition(mask,lab,unknown):
 assert np.all(lab[~mask]==0);assert np.all((lab[mask]>0)|unknown[mask]);assert np.all(lab>=0);return True
def verify_frozen():
 r=json.loads((ROOT/'METHOD_FREEZE.json').read_text());assert sha(ROOT/'CONFIG_FREEZE.json')==r['config_sha256'];assert sha(ROOT/'HYPOTHESIS_FREEZE_ZH.md')==r['hypothesis_sha256'];return True
def gate_downstream(previous):return 'READY' if previous in ['GO','GO_PROXY'] else 'NOT_RUN'
