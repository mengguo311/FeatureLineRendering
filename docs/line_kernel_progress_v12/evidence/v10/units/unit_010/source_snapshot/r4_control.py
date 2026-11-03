"""Read saved control catalogs; never execute previous producers."""
from runtime_io import *
from relaxed_delivery import scientific

def compare_library(current,path):
 path=Path(path);old=json.loads(path.read_text())
 assert current['complete'] and old['complete'],'CONTROL_REPLAY_INCOMPLETE'
 assert current['selected'] is None and old['selected'] is None,'CONTROL_REPLAY_NONZERO_SELECTION'
 a=scientific(current);b=scientific(old)
 assert a==b,'CONTROL_REPLAY_SCIENTIFIC_RECORD_MISMATCH '+str(path)
 pack=dict(np.load(path.parent/'GEOMETRY.npz',allow_pickle=False));count=0
 for rec,prev in zip(current['records'],old['records']):
  for key in ('q','template','local_movable'):
   if key+'_array' in prev:
    np.testing.assert_array_equal(rec[key],pack[prev[key+'_array']],err_msg='CONTROL_REPLAY_GEOMETRY '+key);count+=1
 return dict(complete=True,source=str(path),source_sha256=sha(path),neighbors=len(old['neighbors']),records=len(old['records']),geometry_arrays=count,selected=None,comparison='exact scientific records and every saved q/template/movable array; branch diagnostics excluded')

def compare_state(before,after,m0,m1,v0,v1,events):
 assert not events and v0==v1,'CONTROL_STATE_NEW_EVENT_OR_VERSION'
 assert set(before)==set(after),'CONTROL_STATE_OBJECT_IDS'
 for gid,a in before.items():
  b=after[gid];assert a['version']==b['version'] and a['leaves']==b['leaves'] and a['seed_origins']==b['seed_origins']
  np.testing.assert_array_equal(a['rows'],b['rows']);np.testing.assert_array_equal(a['q'],b['q'])
 assert set(m0)==set(m1),'CONTROL_STATE_MEMBER_FIELDS'
 for k in m0:np.testing.assert_array_equal(m0[k],m1[k],err_msg='CONTROL_STATE '+k)
 return dict(identical=True,all_membership_fields=True,all_current_curves_rows_versions=True,objects=len(before),rows=len(m0['edge_id']),new_events=0,next_version=v1)
