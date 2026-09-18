"""Witnessed-view prize-collecting path cover, deterministic bounded approximation.

NOT a min-cost-flow optimum: path witnesses and turns are non-additive. A beam
proposes simple paths; node-disjoint set packing and bounded exchanges choose
whole paths. Unretained junction branches are exported, never silently declared
to be resolved topology. No positions or input tangents are changed.
"""
import numpy as np
from .stroke_graph import whole_path_witness


class PathProblem:
    def __init__(self,g,objective,arm='C',seed=0):
        self.g=g;self.cfg=objective;self.arm=arm;self.p=g['p'];self.n=len(self.p)
        self.geometry=arm=='B';self.mask=g['physical'].copy() if self.geometry else g['full'].copy()
        if arm=='C-no-corner':self.mask &= ~g['corner']
        self.support=g['support'].copy();self.evaluated=g['evaluated'];self.length_px=g['length_px']
        quality=g['node_support'].sum(0)/np.maximum(g['node_evaluated'].sum(0),1)
        if arm=='N':
            rng=np.random.default_rng(seed);idx=np.flatnonzero(self.mask);perm=rng.permutation(idx)
            self.support[:,idx]=self.support[:,perm];quality=quality[rng.permutation(len(quality))]
        self.mean_support=(self.support*self.evaluated).sum(0)/np.maximum(self.evaluated.sum(0),1)
        # A shuffled value from a hidden donor remains a low score. The physical
        # visibility mask is NOT shuffled, and the same full edge budget is kept.
        self.mean_support=np.clip(self.mean_support,0,1)
        geom=.8*g['continuation']-.35*np.minimum(g['gap'],2)-.25*(1-g['tangent_agreement'])
        self.edge_value=geom if self.geometry else geom+.6*self.mean_support+.2*g['id_affinity']-.5*(1-self.mean_support)
        self.node_value=np.clip(2*g['l']/float(g['unit']),.5,3)
        if not self.geometry:self.node_value=self.node_value*g['source_weight']*quality
        self.adj=[[] for _ in range(self.n)];self.edge_index={}
        for e in np.flatnonzero(self.mask):
            i,j=map(int,g['pairs'][e]);self.adj[i].append((j,int(e)));self.adj[j].append((i,int(e)));self.edge_index[(min(i,j),max(i,j))]=int(e)
        for row in self.adj:row.sort(key=lambda z:(-self.edge_value[z[1]],z[0]))

    def turn(self,a,b,c,e0,e1):
        u=self.p[b]-self.p[a];v=self.p[c]-self.p[b]
        cosine=np.clip(np.dot(u,v)/max(np.linalg.norm(u)*np.linalg.norm(v),1e-12),-1,1)
        angle=float(np.degrees(np.arccos(cosine)))
        if angle>self.cfg['max_turn_deg']:return False,0.,False
        shared=self.evaluated[:,e0]&self.evaluated[:,e1]&(self.support[:,e0]>=.6)&(self.support[:,e1]>=.6)
        protected=not self.geometry and self.arm!='C-no-corner' and angle>=35 and shared.sum()>=3
        cost=max(0,(angle-35)/(self.cfg['max_turn_deg']-35))**2
        if protected:cost*=.15
        return True,cost,protected

    def score(self,nodes,edges,turn_cost=None):
        nodes=np.asarray(nodes,int);edges=np.asarray(edges,int);cfg=self.cfg
        if turn_cost is None:
            turn_cost=0.
            for k in range(1,len(nodes)-1):
                ok,cost,_=self.turn(nodes[k-1],nodes[k],nodes[k+1],edges[k-1],edges[k])
                if not ok:return -np.inf,{}
                turn_cost+=cost
        length=float(self.g['length'][edges].sum()/float(self.g['unit']))
        witness,views,q=(1.,[],[]) if self.geometry else whole_path_witness(edges,self.evaluated,self.support,self.length_px,cfg['witness_fraction'],cfg['witness_threshold'])
        terms=dict(node_reward=float(cfg['node_weight']*self.node_value[nodes].sum()),
            link_reward=float(cfg['link_weight']*self.edge_value[edges].sum()),
            path_reward=float(cfg['path_reward']*np.tanh(length/cfg['length_scale'])*witness),
            stroke_count_penalty=float(cfg['start_cost']),
            short_penalty=float(cfg['short_cost']*max(0,1-length/cfg['short_units'])),
            abnormal_curvature_penalty=float(cfg['turn_penalty']*turn_cost),
            duplicate_penalty=0.,unsupported_bridge_penalty=0.,cross_depth_penalty=0.)
        score=terms['node_reward']+terms['link_reward']+terms['path_reward']-sum(terms[k] for k in terms if 'penalty' in k)
        return score,dict(**terms,total=float(score),length_units=length,witness_score=witness,witness_views=views,view_quality=q)


def proposals(problem,search,progress=None):
    p=problem;active=np.array([i for i,row in enumerate(p.adj) if row],int)
    # Uniform deterministic seeds in immutable ID order; no ROI or image selection.
    seeds=active[np.linspace(0,len(active)-1,min(search['seed_cap'],len(active)),dtype=int)] if len(active) else []
    output={};checkpoints=set(search['checkpoints']);width=search['beam_width']
    for si,s in enumerate(seeds):
        beam=[((int(s),),(),0.,0.)]
        for length in range(2,search['max_nodes']+1):
            new=[]
            for nodes,edges,cost,estimate in beam:
                extended=False
                for j,e in p.adj[nodes[-1]]:
                    if j in nodes:continue
                    extra=0.
                    if len(nodes)>=2:
                        ok,extra,_=p.turn(nodes[-2],nodes[-1],j,edges[-1],e)
                        if not ok:continue
                    nn=nodes+(j,);ee=edges+(e,);cc=cost+extra
                    # Cheap additive beam priority. Complete witness scores enter
                    # proposal ranking, packing and exchanges, not a false optimum.
                    rank=estimate+p.cfg['node_weight']*p.node_value[j]+p.cfg['link_weight']*p.edge_value[e]-p.cfg['turn_penalty']*extra
                    new.append((nn,ee,cc,rank));extended=True
                if not extended and len(nodes)>=3:
                    score,terms=p.score(nodes,edges,cost)
                    if score>0:output[min(nodes,nodes[::-1])]=(nodes,edges,score,terms)
            if not new:break
            new.sort(key=lambda x:(-x[3],x[0]));beam=new[:width]
            if length in checkpoints:
                for nodes,edges,cost,_ in beam:
                    score,terms=p.score(nodes,edges,cost)
                    if score>0:output[min(nodes,nodes[::-1])]=(nodes,edges,score,terms)
        if progress and si%512==0:progress(si,len(seeds),len(output))
    return sorted(output.values(),key=lambda x:(-x[2],x[0]))


def pack(proposed,n,rounds=2,max_conflicts=2):
    owner=np.full(n,-1,int);selected={};gains=[]
    for k,row in enumerate(proposed):
        ids=np.asarray(row[0],int)
        if np.all(owner[ids]<0):owner[ids]=k;selected[k]=row
    initial=float(sum(row[2] for row in selected.values()))
    for turn in range(rounds):
        changes=0
        for k,row in enumerate(proposed):
            if k in selected:continue
            ids=np.asarray(row[0],int);conflicts=set(owner[ids].tolist())-{-1}
            if len(conflicts)>max_conflicts:continue
            loss=sum(selected[j][2] for j in conflicts)
            if row[2]<=loss+1e-9:continue
            for j in conflicts:owner[np.asarray(selected[j][0],int)]=-1;del selected[j]
            selected[k]=row;owner[ids]=k;gains.append(float(row[2]-loss));changes+=1
        if not changes:break
    result=[selected[k] for k in sorted(selected)]
    flat=[i for row in result for i in row[0]]
    if len(flat)!=len(set(flat)):raise AssertionError('node-disjoint constraint failed')
    return result,dict(proposals=len(proposed),initial_objective=initial,final_objective=float(sum(x[2] for x in result)),swaps=len(gains),swap_gains=gains)


def local_greedy(problem):
    p=problem;adj=[[] for _ in range(p.n)];parent=np.arange(p.n)
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    selected=[];rejected=dict(cycle=0,degree=0,turn=0,nonpositive=0)
    for e in sorted(np.flatnonzero(p.mask),key=lambda e:(-p.edge_value[e],int(e))):
        i,j=map(int,p.g['pairs'][e])
        if p.edge_value[e]<=0:rejected['nonpositive']+=1;continue
        if len(adj[i])>=2 or len(adj[j])>=2:rejected['degree']+=1;continue
        if root(i)==root(j):rejected['cycle']+=1;continue
        if any(adj[a] and not p.turn(adj[a][0][0],a,b,adj[a][0][1],e)[0] for a,b in [(i,j),(j,i)]):
            rejected['turn']+=1;continue
        adj[i].append((j,int(e)));adj[j].append((i,int(e)));parent[root(i)]=root(j);selected.append(int(e))
    seen=set();rows=[]
    for s in range(p.n):
        if s in seen or len(adj[s])!=1:continue
        nodes=[s];edges=[];seen.add(s)
        while True:
            options=[(j,e) for j,e in adj[nodes[-1]] if j not in seen]
            if not options:break
            j,e=options[0];nodes.append(j);edges.append(e);seen.add(j)
        if len(nodes)>=3:
            score,terms=p.score(nodes,edges);rows.append((tuple(nodes),tuple(edges),score,terms))
    return rows,dict(selected_edges=len(selected),rejected=rejected,proposals=0)


def junction_audit(problem,rows):
    selected={e for row in rows for e in row[1]};result=[]
    for i,adj in enumerate(problem.adj):
        if len(adj)<3:continue
        retained=[int(e) for _,e in adj if e in selected]
        rejected=[dict(neighbor=int(j),edge=int(e),reason='not chosen by competing path cover') for j,e in adj if e not in selected]
        result.append(dict(node=i,retained=retained,unretained_branches=rejected,
            interpretation='potential graph junction; NOT a certified real 3D junction'))
    return result
