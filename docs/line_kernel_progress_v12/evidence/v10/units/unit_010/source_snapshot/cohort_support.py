"""Freeze every tracked origin from this unit's own cold-loadable START."""
from runtime_io import *
from carry_forward_support import save_diagnostics as original_save

def freeze_references(c,d,stage,binding,guard):
 guard('readiness');stage=Path(stage);verify_checkpoint(stage,binding);refs={}
 with np.load(stage/'MODELS.npz',allow_pickle=False) as bank:
  lookup={int(g):i for i,g in enumerate(bank['group_id'])}
  for gid,o in d['objects'].items():
   for sid in o['seed_origins']:
    assert sid==gid,'START_ORIGIN_NOT_INDEPENDENT'
    j=lookup[gid];q=bank['knots_p'][bank['knot_offsets'][j]:bank['knot_offsets'][j+1]].copy();rows=bank['rows'][bank['row_offsets'][j]:bank['row_offsets'][j+1]].copy()
    np.testing.assert_array_equal(q,o['q']);np.testing.assert_array_equal(rows,o['rows']);q.flags.writeable=False;rows.flags.writeable=False
    refs[sid]=dict(q=q,rows=rows)
 assert sorted(refs)==d['cohort_receipt']['tracked_origins']
 d['_fixed_references']={'UNIT009_START':refs};d['_reference_binding']=dict(UNIT009_START=dict(stage=str(stage),binding=binding))

def save_diagnostics(stage,c,d,guard):
 original_save(stage,dict(c,fixed_reference_stages=d['_reference_binding']),d,guard)
