from env import *
if __name__=='__main__':
 a=json.loads((ROOT/'INPUT_AUDIT.json').read_text());assert all(x['calibration']['engineering_calibration_go'] for x in a.values())
 review('01_measurement_GO','已实际view_image看过三scene原RGB和原C8 X-RAY。建筑窗框有位置线，屋面缺/碎线；头骨颅盖有大量非真实轮廓的纹理/错位线；Ficus顶部有显著向外长线。三scene DEV渲染校准通过，但alpha非主体mask、depth非GT。GO：冻结下列位置作为希望解释的两个结构目标及纹理/毛刺样负例，最近真实C8有序parent小区间自动选取，不根据测量结果挑赢家。目标称正向假设，不是已知物理真边。每scene四case×三view×三arm，最多本轮固定规则一次实测。完整source贡献alpha*T，候选AABB完整枚举并all-N核对，原native/cov-plane深度用于独立侧面patch，禁止用GS短轴当法线。若本轮line不优于错位/纯源区域对照，科学NO_GO并停止升级；允许输出可追溯参与关系而非强建primitive。',[ROOT/'INPUT_AUDIT.json']+[ROOT/'scenes'/s/'stage0/REFERENCE.jpg' for s in SCENES])
 targets={
 'scan24':[('window_frame',[385,180],'structural_hypothesis'),('roof_wall_eave',[178,155],'structural_hypothesis'),('roof_marks',[192,69],'appearance_or_weak_candidate'),('stray_ground_line',[326,448],'spike_looking_negative')],
 'scan65':[('cap_seam',[280,245],'structural_hypothesis'),('socket_rim',[249,350],'structural_hypothesis'),('cap_marks',[199,115],'appearance_or_weak_candidate'),('outside_skull_line',[472,248],'spike_looking_negative')],
 'ficus':[('stem',[393,456],'structural_hypothesis'),('thin_leaf_edge',[523,89],'structural_hypothesis'),('pot_marks',[388,616],'appearance_or_weak_candidate'),('top_spike',[575,32],'spike_looking_negative')]}
 cfg=dict(version='v00',input_arm='original C2L50 8BUILD arms/C',no_core_labels=True,views=VIEWS,dev=DEV,targets=targets,selection=dict(nearest_max_pixels=12,parent_min_children=9,window_half_arclength_pixels=12,sample_count=9),offsets=[-6,-4,-2,0,2,4,6],controls=['line','shifted_12px','source_geometry_axis'],source_only=True,near=.2,finite_q=9,alpha_cap=.999,trans_stop=1e-5,source_floor={'scan24':.0144,'scan65':.0144,'ficus':.3},calibration=dict(rgb_mae=.02,alpha_mae=.02,center_surface_p95=.15,query_renderer_abs=5e-7,allN_abs=2e-12),patch=dict(min_points=10,min_alpha=.5,max_center_surface_relative=.02,max_center_surface_pixels=4,min_2d_spread=.005,max_rms_pixels=1,join_pixels=2,depth_step_pixels=4,max_single_angle_deg=15,min_fold_angle_deg=25,max_ray_layer_pixels=8,min_side_L1=.35),crossview=dict(min_weighted_ID_overlap=.15,min_pairing_margin=.05,max_normal_deg=20,min_views=2),prohibition='No model changes; no physical surface claim; no whole-scene classification from ROI; no threshold retuning on secondary views',budget=dict(case_count=12,query_arms=3,max_dev_revisions=2,task_GiB=10))
 assert not (ROOT/'CONFIG.json').exists();js(ROOT/'CONFIG.json',cfg)
 rows=[]
 for s in SCENES:
  l=npz(linepath(s)/'gaussians.npz');c=cam(s,DEV[s]);uv,z=projection(l['means'],c);counts=np.bincount(l['primitive_id']);parents=json.loads((linepath(s)/'parents.json').read_text());valid=(z>.2)&np.isfinite(uv).all(1)&(counts[l['primitive_id']]>=9)
  im=Image.open(ROOT/'scenes'/s/'stage0/original_rgb.png').convert('RGB');di=ImageDraw.Draw(im)
  for idx,(name,target,intent) in enumerate(targets[s]):
   dist=np.linalg.norm(uv-np.array(target),axis=1);dist[~valid]=np.inf;k=int(dist.argmin());pid=int(l['primitive_id'][k]);ids=np.flatnonzero(l['primitive_id']==pid);ids=ids[np.lexsort((l['arc_t'][ids],l['internal_piece_id'][ids]))];chain=uv[ids];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(chain,axis=0),axis=1))];ki=int(np.flatnonzero(ids==k)[0]);keep=(abs(arc-arc[ki])<=12);ii=ids[keep]
   if len(ii)>9:ii=ii[np.unique(np.rint(np.linspace(0,len(ii)-1,9)).astype(int))]
   case=dict(scene=s,case=name,intent=intent,dev=DEV[s],target_uv=target,nearest_distance=float(dist[k]),parent_id=pid,child_ids=ii.tolist(),internal_piece_ids=l['internal_piece_id'][ii].astype(int).tolist(),source_views=parents[pid]['source_views'],original_parent_metadata=parents[pid],selection_valid=bool(dist[k]<=12 and len(ii)>=5),selection_note='Nearest original parent with >=9 children; actual child samples within 24px projected arc; not fitted/created geometry. If <5 samples or >12px target distance keep unavailable.')
   rows.append(case);col=['red','blue','orange','magenta'][idx];di.ellipse((target[0]-12,target[1]-12,target[0]+12,target[1]+12),outline=col,width=2);di.text((target[0]+14,target[1]),name,fill=col)
   for x,y in uv[ii]:di.ellipse((x-1.5,y-1.5,x+1.5,y+1.5),fill=col)
  out=ROOT/'scenes'/s/'CASES_FROZEN.jpg';im.save(out)
 js(ROOT/'CASE_FREEZE.json',dict(cases=rows,selection_source='Actual view_image of frozen RGB/C8. Manual diagnostic targets, no GT. All candidates retained regardless outcomes.'))
 state('CASES_FROZEN',status='READY_FOR_TDD',children=[],cases=len(rows))
