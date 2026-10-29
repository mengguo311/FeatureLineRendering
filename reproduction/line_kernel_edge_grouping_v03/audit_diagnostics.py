"""Read saved memberships; audit and render diagnostic selections. Never regroup."""
from pilot import *
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

def enlarged_panel(path,items,title):
    w,h=600,360;canvas=Image.new('RGB',(1200,55+((len(items)+1)//2)*(h+45)),'white');draw=ImageDraw.Draw(canvas);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14);draw.text((8,8),title,fill='black',font=font)
    for i,(label,file) in enumerate(items):
        im=Image.open(file).convert('RGB');ar=np.asarray(im);yy,xx=np.nonzero(ar.min(2)<253)
        if len(xx):im=im.crop((max(0,int(xx.min())-5),max(0,int(yy.min())-5),min(im.width,int(xx.max())+6),min(im.height,int(yy.max())+6)))
        factor=min(w/im.width,h/im.height);im=im.resize((max(1,round(im.width*factor)),max(1,round(im.height*factor))),Image.Resampling.NEAREST);x=i%2*w;y=55+i//2*(h+45);draw.text((x+6,y+2),label,fill='black',font=font);canvas.paste(im,(x+(w-im.width)//2,y+37+(h-im.height)//2))
    canvas.save(path)

def audit(scene,method,r,p,a,helpers,cameras):
    source=OUT/scene/method;out=OUT/'diagnostics'/scene/method;out.mkdir(parents=True,exist_ok=False);saved=dict(np.load(source/'MEMBERSHIP.npz'));l=dict(np.load(source/'LINKS.npz'));chains=dict(np.load(source/'CHAINS.npz'));ids=saved['edge_id'];n=len(ids);nr=len(r['x']);pairs=l['pair'];accepted=l['status']==3
    assert np.array_equal(saved['line_kernel_id'],np.arange(n));assert np.array_equal(saved['primitive_id'],a['primitive_id']);assert np.array_equal(saved['internal_piece_id'],a['internal_piece_id']);assert np.all((ids>=0)|(ids==-1));assert np.array_equal(saved['representative_id'],r['kernel_rep'])
    ii,jj=pairs[accepted].T;ports=l['port'][accepted];ep1=r['endpoints'][ii,ports[:,0]];ep2=r['endpoints'][jj,ports[:,1]];gap=np.linalg.norm(ep2-ep1,axis=1);assert np.max(gap,initial=0)<=1.5*p+1e-12
    degree=np.bincount(np.r_[ii,jj],minlength=nr);assert degree.max(initial=0)<=2
    theta=np.arccos(np.clip(abs(np.sum(r['t'][ii]*r['t'][jj],axis=1)),0,1))/RAD;assert theta.max(initial=0)<=30+1e-8
    direction=(ep2-ep1)/np.maximum(gap[:,None],1e-15);dot1=np.sum(direction*r['t'][ii]*(2*ports[:,0,None]-1),axis=1);dot2=np.sum(-direction*r['t'][jj]*(2*ports[:,1,None]-1),axis=1);nonzero=gap>1e-12*p;connector=np.arccos(np.clip(np.minimum(dot1[nonzero],dot2[nonzero]),-1,1))/RAD;assert connector.max(initial=0)<=35+1e-8
    primary_rep=np.full(nr,-1,np.int64);valid=r['kernel_rep']>=0;primary_rep[r['kernel_rep'][valid]]=ids[valid]
    # Each emitted group is one connected component of accepted primary links.
    primary_link=(primary_rep[ii]>=0)&(primary_rep[ii]==primary_rep[jj]);graph=coo_matrix((np.ones(2*primary_link.sum()),(np.r_[ii[primary_link],jj[primary_link]],np.r_[jj[primary_link],ii[primary_link]])),shape=(nr,nr)).tocsr();_,cc=connected_components(graph,directed=False)
    groups=json.loads((source/'GROUPS.json').read_text())['groups'];stats=[];maxwindow=0.;maxchain=0
    chainlookup={}
    for lo,hi in zip(chains['offsets'][:-1],chains['offsets'][1:]):
        nodes=chains['nodes'][lo:hi];edge=int(chains['representative_edge_id'][nodes[0]]);chainlookup[edge]=nodes
    for g in groups:
        edge=g['edge_id'];mask=ids==edge;rows=np.flatnonzero(mask);reps=np.unique(r['kernel_rep'][mask]);assert edge==int(rows.min());assert len(np.unique(cc[reps]))==1;assert len(reps)>=3;assert r['length'][reps].sum()>=4*p-1e-12;assert len(reps)<=20000
        nodes=chainlookup[edge];assert np.array_equal(np.sort(nodes),reps);xx=r['x'][nodes];chord=np.diff(xx,axis=0);dist=np.linalg.norm(chord,axis=1);unit=chord/np.maximum(dist[:,None],1e-15);turn=np.arccos(np.clip(np.sum(unit[:-1]*unit[1:],axis=1),-1,1))/RAD;pos=np.cumsum(dist)[:-1];prefix=np.r_[0,np.cumsum(turn)];left=np.searchsorted(pos,pos-8*p);window=prefix[1:]-prefix[left];mw=float(window.max(initial=0));assert mw<=90+1e-7;maxwindow=max(maxwindow,mw);maxchain=max(maxchain,len(nodes))
        parent,count=np.unique(a['primitive_id'][mask],return_counts=True);composition=sorted(zip(parent.tolist(),count.tolist()),key=lambda v:(-v[1],v[0]));stats.append(dict(edge_id=edge,kernels=len(rows),parents=len(parent),parent_composition=composition,total_turn_degrees=float(turn.sum()),max_8p_window_turn_degrees=mw,supported_length_p=float(r['length'][reps].sum()/p),extent_p=(np.ptp(a['means'][mask],axis=0)/p).tolist(),cycle=g['cycle']))
    stats.sort(key=lambda d:(-d['kernels'],d['edge_id']));cross=[g for g in stats if g['parents']>1]
    crosslink=a['primitive_id'][r['mid'][ii]]!=a['primitive_id'][r['mid'][jj]]
    alt=np.flatnonzero(l['status']==2);np.savez_compressed(out/'JUNCTION_ALTERNATIVES.npz',candidate_link_row=alt,representative_pair=pairs[alt],ports=l['port'][alt],cost=l['cost'][alt],provisional=np.ones(len(alt),bool))
    summary=dict(scene=scene,method=method,complete_rows=n,assigned=int((ids>=0).sum()),unknown=int((ids<0).sum()),emitted_groups=len(stats),cross_parent_groups=len(cross),cross_parent_kernels=sum(g['kernels'] for g in cross),cross_parent_groups_all_parents_at_least_6_kernels=sum(all(c>=6 for _,c in g['parent_composition']) for g in cross),primary_cross_parent_links=int((primary_link&crosslink).sum()),accepted_graph_cross_parent_links=int(crosslink.sum()),max_degree=int(degree.max(initial=0)),max_gap_over_p=float(gap.max(initial=0)/p),max_tangent_degrees=float(theta.max(initial=0)),max_connector_degrees=float(connector.max(initial=0)),max_8p_window_turn_degrees=maxwindow,max_component_representatives=maxchain,cycles=sum(g['cycle'] for g in stats),largest_cross_parent=cross[:3],group_statistics=stats,geometry_audit=json.loads((source/'GEOMETRY_AUDIT.json').read_text()))
    js(out/'INDEPENDENT_AUDIT.json',summary)
    selections=cross[:3];js(out/'SELECTION.json',dict(rule='Three largest saved primary groups with >1 old parent; no regrouping, parameter change or hidden sample',groups=selections,negative_rule='First saved example of each rejection category'))
    colors=np.full((n,3),.68)
    for rank,g in enumerate(selections):colors[ids==g['edge_id']]=COLORS[rank]
    fullasset={k:a[k] for k in ['means','covariance','opacity']};fullasset['colors']=colors;fullitems=[];isoitems=[];provenanceitems=[];negativeitems=[]
    for c in cameras:
        view=c['view'];file=out/(view+'_CROSS_PARENT_FULL.png');image_save(file,helpers['render'](fullasset,c,(1,1,1),.0144)['rgb']);fullitems.append((method+' '+view+' | ALL kernels; cross-parent selection',file))
        for rank,g in enumerate(selections):
            mask=ids==g['edge_id'];asset={k:fullasset[k][mask] for k in fullasset};file=out/(view+'_CROSS_PARENT_'+str(rank+1)+'.png');image_save(file,helpers['render'](asset,c,(1,1,1),.0144)['rgb']);isoitems.append((f"{view} edge {g['edge_id']}: {g['kernels']} kernels / {g['parents']} parents",file))
            parent=a['primitive_id'][mask];pp=np.unique(parent);asset['colors']=COLORS[np.searchsorted(pp,parent)%len(COLORS)];file=out/(view+'_PROVENANCE_'+str(rank+1)+'.png');image_save(file,helpers['render'](asset,c,(1,1,1),.0144)['rgb']);provenanceitems.append((view+' edge '+str(g['edge_id'])+' | original parent colors, NOT truth',file))
        seen=set()
        for case in json.loads((source/'NEGATIVE_CASES.json').read_text()):
            if case['kind'] in seen:continue
            seen.add(case['kind']);rows=np.asarray(case['kernel_rows']);asset={k:a[k][rows] for k in ['means','covariance','opacity']};rep=saved['representative_id'][rows];asset['colors']=COLORS[(rep!=rep[0]).astype(int)];file=out/(view+'_NEGATIVE_'+case['kind']+'.png');image_save(file,helpers['render'](asset,c,(1,1,1),.0144)['rgb']);negativeitems.append((view+' '+case['kind']+' | actual endpoint seedlets',file))
    panel(out/'CROSS_PARENT_FULL_PANEL.png',fullitems,scene+' '+method+' | complete asset, cross-parent groups highlighted',cell=(cameras[0]['width'],cameras[0]['height']))
    enlarged_panel(out/'CROSS_PARENT_ISOLATED_PANEL.png',isoitems,scene+' '+method+' | saved cross-parent groups; native render crops enlarged')
    enlarged_panel(out/'PARENT_PROVENANCE_PANEL.png',provenanceitems,scene+' '+method+' | provenance diagnostic; different colors do NOT imply different edges')
    enlarged_panel(out/'NEGATIVE_PANEL.png',negativeitems,scene+' '+method+' | rejected / ambiguous proposals; no added connector geometry')
    js(out/'SEAL.json',dict(complete=True,files={f.name:sha(f) for f in sorted(out.iterdir()) if f.is_file()}))
    return {k:v for k,v in summary.items() if k!='group_statistics'}

if __name__=='__main__':
    from grouping import RAD
    helpers=load_helpers();cameras=json.loads((OUT/'CAMERAS.json').read_text());summaries=[];comparisons=[];guard();js(OUT/'DIAGNOSTICS_START.json',dict(utc=now(),pid=os.getpid(),no_regrouping=True))
    for scene in ['scan24','ficus','scan65']:
        r=dict(np.load(OUT/scene/'REPRESENTATIVES.npz'));p=json.loads((OUT/scene/'RESULT.json').read_text())['p'];a=dict(np.load(BASE/'arms/C/scenes'/scene/'full/gaussians.npz'))
        for method in ['baseline','hough']:
            guard();summary=audit(scene,method,r,p,a,helpers,cameras[scene]);summaries.append(summary);print('AUDITED',scene,method,summary['primary_cross_parent_links'],flush=True)
        b=dict(np.load(OUT/scene/'baseline/LINKS.npz'));h=dict(np.load(OUT/scene/'hough/LINKS.npz'));nr=len(r['x']);bk=b['pair'][:,0].astype(np.int64)*nr+b['pair'][:,1];hk=h['pair'][:,0].astype(np.int64)*nr+h['pair'][:,1];new=~np.isin(hk,bk,assume_unique=True);bs=np.load(OUT/scene/'baseline/MEMBERSHIP.npz')['edge_id'];hs=np.load(OUT/scene/'hough/MEMBERSHIP.npz')['edge_id'];comparison=dict(scene=scene,hough_only_candidates=int(new.sum()),hough_only_candidates_accepted=int((new&(h['status']==3)).sum()),hough_shared_family_legal_candidates=int(h['shared_hough_family'].sum()),primary_id_changed_rows=int((bs!=hs).sum()),hough_minus_baseline_assigned=int((hs>=0).sum()-(bs>=0).sum()));comparisons.append(comparison)
    js(OUT/'INDEPENDENT_AUDIT_SUMMARY.json',dict(scenes_methods=summaries,comparisons=comparisons))
    js(OUT/'DIAGNOSTICS_EXIT.json',dict(utc=now(),returncode=0,all_six_audits_passed=True));print('ALL_AUDITS_PASS',flush=True)
