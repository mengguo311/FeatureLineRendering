"""Frozen ROI Gaussian-score convergence, no new views/votes/renders."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'experiments/gaer_attribution_capacity_v02'))
import numpy as np
from scipy.sparse import csr_matrix,coo_matrix
from runtime import *
from diagnostics import row_sample

def main():
 P=json.loads((ART/'PROTOCOL.json').read_text());results={};checks=0
 for scene,record in P['scenes'].items():
  results[scene]={}
  for key in P['roi_views']:
   a=np.load(ART/'downloads'/scene/f'{key}_ROI_full_CSR.npz');pixels=a['query_pixels_yx'];off=a['accepted_offsets'];ids=a['accepted_original_ids'];w=a['accepted_weights'];shape=(len(pixels),record['count']);C=row_sample(pixels,a['sample_points_yx']);M=row_sample(pixels,a['minus_yx']);Pp=row_sample(pixels,a['plus_yx']);colors=a['effective_SH3_colors'];delta=a['delta_RGB'];norm=np.linalg.norm(delta,axis=1);unit=delta/np.maximum(norm[:,None],1e-12);scores={};top={};rows=[];certificates=[];rawfull=csr_matrix((w,ids,off),shape=shape);fullside=np.asarray((M+Pp)@np.asarray(rawfull.sum(1)).ravel()).ravel()
   for K in (8,16,32,'full'):
    if K=='full':mat=csr_matrix((w,ids,off),shape=shape)
    else:
     rr=[];cc=[];dd=[]
     for j in range(len(pixels)):
      lo,hi=off[j:j+2];order=np.argsort(-w[lo:hi],kind='stable')[:K];rr.extend([j]*len(order));cc.extend(ids[lo:hi][order]);dd.extend(w[lo:hi][order])
     mat=coo_matrix((dd,(rr,cc)),shape=shape).tocsr()
    center=C@mat;dw=(M@mat-Pp@mat).tocsr();dw.eliminate_zeros();visible=(center>0).astype(float);D=abs(dw).multiply(visible).tocsr();rr,cc=dw.nonzero();vals=np.asarray(dw[rr,cc]).ravel();terms=(colors[cc]-1)*vals[:,None];aligned=np.maximum((terms*unit[rr]).sum(1),0);signed=coo_matrix((aligned,(rr,cc)),shape=dw.shape).tocsr().multiply(visible).tocsr();methods={}
    for method in ('center','oneD','multiD','color_signed'):
     vectors=[]
     for j,r in enumerate(record['rois'][key]):
      sl=slice(j*25,(j+1)*25)
      if method=='oneD':win=a[f'K{K}_winner'][sl];vec=np.bincount(win[win>=0],minlength=record['count']).astype(float)
      else:vec=np.asarray({'center':center,'multiD':D,'color_signed':signed}[method][sl].sum(0)).ravel()
      vectors.append(vec);top[f'{K}_{method}_{j}']=np.lexsort((np.arange(len(vec)),-vec))[:8].astype(np.int32)
     methods[method]=np.stack(vectors)
     if K=='full':assert np.allclose(methods[method],a[f'score_{method}'],atol=1e-10,rtol=1e-8);checks+=1
    scores[str(K)]=methods
    if K!='full':
     residual=np.maximum(0,fullside-np.asarray((M@mat+Pp@mat).sum(1)).ravel());absdw=abs(dw).tocsr()
     for j in range(len(a['sample_points_yx'])):
      lo,hi=D.indptr[j:j+2];lower=0.;upper=0.;best=-1
      if lo<hi:
       candidates=D.indices[lo:hi];vals=D.data[lo:hi];order=np.lexsort((candidates,-vals));best=int(candidates[order[0]]);lower=float(vals[order[0]]-residual[j])
       al,ah=absdw.indptr[j:j+2];other=absdw.data[al:ah][absdw.indices[al:ah]!=best];upper=float((other.max() if len(other) else 0)+residual[j])
      certified=bool(best>=0 and a['normal_ok'][j] and lower>upper+4e-6)
      if certified:assert best==int(a['Kfull_winner'][j]);checks+=1
      certificates.append(dict(K=K,sample=j,retained_center_best=best,winner_lower_D=lower,all_other_and_unseen_upper_D=upper,side_mass_residual=float(residual[j]),full_winner_certified_by_sufficient_interval=certified,actual_old_rule_winner_equals_full=bool(a[f'K{K}_winner'][j]==a['Kfull_winner'][j])))

   for j,r in enumerate(record['rois'][key]):
    for method in ('center','oneD','multiD','color_signed'):
     ft=top[f'full_{method}_{j}'];fullscore=scores['full'][method][j]
     for K in (8,16,32):
      kt=top[f'{K}_{method}_{j}'];overlap=len(np.intersect1d(ft,kt));rows.append(dict(roi=j,category=r['category'],fragment=r['fragment'],method=method,K=K,top8_overlap=overlap,top8_Jaccard=overlap/(16-overlap),K_top8_fullscore_fraction_of_full_top8=float(fullscore[kt].sum()/max(fullscore[ft].sum(),1e-20)),aggregated_score_retained_fraction=float(scores[str(K)][method][j].sum()/max(fullscore.sum(),1e-20))))
   p=ART/'downloads'/scene/f'{key}_ROI_ranking_top8.npz';npz(p,**top);results[scene][key]=dict(rankings=rows,truncation_winner_intervals=certificates,legacy_field_note='winner_certified_margin_pixels in initial K8/16/32 results counts only retained-set margins and is NOT full-winner certification; these sufficient intervals include missing-center candidates and all unseen endpoint mass')
 atomic_json(ART/'tests/ROI_RANKING_CONVERGENCE.json',dict(passed=True,full_score_reconstruction_checks=checks,scope='same frozen ROI samples/normal/delta; no eight-view reranking or extra voting; color signed uses same original full observed RGB direction',scenes=results));print('ROI_RANKING_AUDIT_PASS',checks)
if __name__=='__main__':main()
