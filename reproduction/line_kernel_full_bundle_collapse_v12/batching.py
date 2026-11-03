"""One global means copy; unchanged v11 mathematics on small local groups."""
import limits
import json
from pathlib import Path
import numpy as np
from core import collapse
from io_tools import sha, save_npz, write_json, same_bytes, array_sha

NUMERICAL = {'nonfinite target geometry', 'asymmetric target covariance',
             'nonpositive target covariance', 'degenerate principal axis',
             'degenerate longitudinal extent', 'invalid derived geometry'}

def group_index(asset, membership):
    n = len(asset['means']); ids = membership['line_kernel_id']; edge = membership['edge_id']
    if ids.dtype != np.dtype('int64') or not np.array_equal(ids, np.arange(n)):
        raise ValueError('original row identity mismatch')
    if edge.dtype != np.dtype('int64') or edge.shape != (n,) or np.any(edge < -1):
        raise ValueError('edge schema mismatch')
    if not same_bytes(asset['primitive_id'], membership['primitive_id']):
        raise ValueError('primitive identity mismatch')
    if any(v.shape[0] != n for v in membership.values()):
        raise ValueError('membership field length mismatch')
    rows = np.flatnonzero(edge >= 0)
    rows = rows[np.argsort(edge[rows], kind='stable')]
    cuts = np.r_[0, np.flatnonzero(np.diff(edge[rows]))+1, len(rows)] if len(rows) else np.array([0])
    return [(int(edge[rows[a]]), rows[a:b]) for a,b in zip(cuts[:-1],cuts[1:])]

class Journal:
    def __init__(self, root, binding, interval=128):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.binding = binding; self.interval = interval; self.manifest = self.root/'MANIFEST.json'
        self.state = dict(binding=binding, chunks=[], completed_groups=0)
        if self.manifest.exists():
            self.state = json.loads(self.manifest.read_text())
            if self.state['binding'] != binding: raise ValueError('journal binding mismatch')
    def restore(self, means, index):
        records=[]
        for c in self.state['chunks']:
            for name,h in c['files'].items():
                if sha(self.root/name) != h: raise ValueError('journal hash mismatch')
            rec=json.loads((self.root/c['records']).read_text())
            for r in rec:
                gid,rows=index[len(records)]
                if r['group_id'] != gid or not np.array_equal(r['rows'],rows):
                    raise ValueError('journal group mismatch')
                records.append(r)
            with np.load(self.root/c['updates'],allow_pickle=False) as z:
                expected=np.concatenate([np.asarray(r['rows'],dtype=np.int64) for r in rec if r['status']=='SUCCESS']) if any(r['status']=='SUCCESS' for r in rec) else np.empty(0,dtype=np.int64)
                if not np.array_equal(expected,z['row_index']) or not np.isfinite(z['means']).all():
                    raise ValueError('journal update mismatch')
                means[z['row_index']]=z['means']
        if len(records)!=self.state['completed_groups']:raise ValueError('journal cursor mismatch')
        return records
    def commit(self, records, means):
        start=self.state['completed_groups']; fresh=records[start:]
        if not fresh:return
        k=len(self.state['chunks']); rname=f'{k:04d}_records.json'; aname=f'{k:04d}_updates.npz'
        rowparts=[np.asarray(r['rows'],dtype=np.int64) for r in fresh if r['status']=='SUCCESS']
        rows=np.concatenate(rowparts) if rowparts else np.empty(0,dtype=np.int64)
        save_npz(self.root/aname,dict(row_index=rows,means=means[rows]))
        write_json(self.root/rname,fresh)
        new=dict(binding=self.binding,chunks=self.state['chunks']+[dict(records=rname,updates=aname,
                 files={rname:sha(self.root/rname),aname:sha(self.root/aname)})],completed_groups=len(records))
        write_json(self.manifest,new);self.state=new

def ledger_summary(ledger):
    counts={s:dict(groups=0,rows=0) for s in ['SUCCESS','SKIPPED_NUMERICAL','FAILED','NOT_RUN']}
    for r in ledger:
        counts[r['status']]['groups']+=1;counts[r['status']]['rows']+=r['row_count']
    return counts

def transform(asset, membership, p, guard, journal=None):
    index=group_index(asset,membership)
    output={**asset,'means':asset['means'].copy()}
    records=journal.restore(output['means'],index) if journal else []
    ledger=[dict(group_id=g,rows=rows.tolist(),row_count=len(rows),status='NOT_RUN',reason='not attempted') for g,rows in index]
    for i,r in enumerate(records):ledger[i]=r
    sizes=[];failure=None
    for i in range(len(records),len(index)):
        gid,rows=index[i];record=ledger[i]
        try:
            guard('group_'+str(gid))
            local={k:v[rows] for k,v in asset.items()};sizes.append(len(rows))
            try:
                result=collapse(local,np.arange(len(rows),dtype=np.int64),p)
                new=result['position_only']['means']
                if new.shape!=local['means'].shape or new.dtype!=local['means'].dtype:
                    raise RuntimeError('local output schema changed')
                if not np.isfinite(new).all():raise ValueError('invalid derived geometry')
                for k in local:
                    if k!='means' and not same_bytes(local[k],result['position_only'][k]):
                        raise RuntimeError('local nonmeans changed')
                displacement=np.linalg.norm(new-local['means'],axis=1)/p
                record.update(status='SUCCESS',reason=None,model=result['model'],
                    displacement_quantiles_p=np.quantile(displacement,[0,.5,.9,.95,.99,1]),
                    maximum_displacement_p=float(displacement.max()),
                    changed_rows=int(np.count_nonzero(np.any(new!=local['means'],axis=1))),
                    original_rows_sha256=array_sha(rows.astype('<i8')))
                output['means'][rows]=new
            except (ValueError,np.linalg.LinAlgError) as exc:
                if isinstance(exc,np.linalg.LinAlgError) or str(exc) in NUMERICAL:
                    record.update(status='SKIPPED_NUMERICAL',reason=type(exc).__name__+': '+str(exc))
                else:raise
            records.append(record)
            if journal and len(records)-journal.state['completed_groups']>=journal.interval:
                journal.commit(records,output['means'])
        except Exception as exc:
            failure=type(exc).__name__+': '+str(exc)
            if journal:
                # The atomic manifest is authoritative even if interruption
                # occurred immediately after its replacement. Pending chunks
                # without that commit are rolled back, never promoted.
                output['means'][:]=asset['means']
                recovered=Journal(journal.root,journal.binding,journal.interval)
                records=recovered.restore(output['means'],index);journal.state=recovered.state
                ledger=[dict(group_id=g,rows=rr.tolist(),row_count=len(rr),status='NOT_RUN',
                    reason='uncommitted at interruption') for g,rr in index]
                for j,saved in enumerate(records):ledger[j]=saved
                if i>=len(records):
                    ledger[i].update(status='NOT_RUN' if isinstance(exc,TimeoutError) else 'FAILED',reason=failure)
            else:
                output['means'][rows]=asset['means'][rows]
                if records and records[-1] is record:records.pop()
                record.update(status='NOT_RUN' if isinstance(exc,TimeoutError) else 'FAILED',reason=failure)
            break
    if journal:
        journal.commit(records,output['means'])
        write_json(journal.root/'LEDGER.json',dict(groups=ledger,summary=ledger_summary(ledger),failure=failure))
    return dict(asset=output,ledger=ledger,summary=ledger_summary(ledger),complete=failure is None,
                failure=failure,allocation=dict(global_means_copies=1,local_call_count=len(sizes),
                local_input_rows=sum(sizes),max_local_input_rows=max(sizes,default=0),
                shared_nonmeans=all(output[k] is asset[k] for k in asset if k!='means')))
