"""Additional immutable control/row identity readiness, no producer imports."""
import numpy as np
import frontier_loader

def validate_control_identity(asset,control,guard,expected):
 guard('readiness');n=len(asset['means']);cp=control['control'];pieces=control['piece_control_indices'];offsets=control['parent_control_offsets']
 assert cp.shape==(expected['controls'],3) and pieces.shape==(expected['pieces'],2) and offsets.shape==(expected['parents'],2),'CONTROL_SCHEMA_COUNTS'
 assert np.isfinite(cp).all()
 for key in ('primitive_id','internal_piece_id','arc_t'):
  assert asset[key].shape==(n,) and control[key].shape==(n,)
  np.testing.assert_array_equal(asset[key],control[key],err_msg='CONTROL_ROW_IDENTITY '+key)
 for key in ('control_index','piece_control_indices','parent_control_offsets','primitive_id','internal_piece_id'):assert np.issubdtype(control[key].dtype,np.integer),key
 pid=control['primitive_id'];piece=control['internal_piece_id'];indices=control['control_index'];basis=control['basis'];derivative=control['derivative_basis']
 assert indices.shape==basis.shape==derivative.shape==(n,2)
 assert np.isfinite(basis).all() and np.isfinite(derivative).all() and np.isfinite(control['arc_t']).all()
 assert np.all((pid>=0)&(pid<len(offsets))) and np.all((piece>=0)&(piece<len(pieces)))
 assert np.all((indices>=0)&(indices<len(cp))) and np.all((pieces>=0)&(pieces<len(cp)))
 assert np.all((offsets[:,0]>=0)&(offsets[:,1]<=len(cp))&(offsets[:,0]<offsets[:,1]))
 np.testing.assert_array_equal(indices,pieces[piece],err_msg='CONTROL_PIECE_INDICES')
 assert np.all(indices>=offsets[pid,0,None]) and np.all(indices<offsets[pid,1,None]),'CONTROL_PARENT_RANGE'
 maximum=0.
 for first in range(0,n,8192):
  guard('readiness');sl=slice(first,first+8192);means=(cp[indices[sl]]*basis[sl,:,None]).sum(1)
  np.testing.assert_allclose(means,asset['means'][sl],rtol=0,atol=1e-10,err_msg='CONTROL_BASIS_CENTERS')
  maximum=max(maximum,float(np.max(np.abs(means-asset['means'][sl]),initial=0)))
 return dict(verified=True,rows=n,controls=len(cp),pieces=len(pieces),parents=len(offsets),center_rtol=0,center_atol=1e-10,max_center_error=maximum,source_ids_are_physical_identity=False)

def load(c,guard):
 d=frontier_loader.load(c,guard)
 with np.load(c['controls'],allow_pickle=False) as control:d['control_identity_receipt']=validate_control_identity(d['asset'],control,guard,c['control_identity']['expected'])
 return d
