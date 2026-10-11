"""New method scope. The sealed paper-text scope remains unchanged."""
GPU='GPU-d2d1e4fd-e246-0633-3343-ccc0a0bd981a'
def validate_scope(c):
 if (c.get('method_variant')!='official_code_fix_v01' or c.get('scene')!='scan24'
     or c.get('automatic_scene_limit')!=1 or c.get('allowed_gpu_uuids')!=[GPU]
     or c.get('stable_seconds')!=60):raise ValueError('official route/GPU/scope mismatch')
 if c.get('purpose')=='native_validation':
  if list(c.get('stage_commands',{}))!=['smoke']:raise ValueError('validation cannot launch training')
 else:raise ValueError('formal pipeline not yet enabled')
