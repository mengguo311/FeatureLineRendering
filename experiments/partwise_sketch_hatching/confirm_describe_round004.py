"""Confirm retained data after outer-session failure; describe all saved witnesses.

No new rendering, selection, thresholds, or revised scientific gates.
"""
import run_round004 as r
import collections,json
import numpy as np
from PIL import Image,ImageDraw


def main():
    lock=json.loads((r.D/'RECOVERY_LOCK.json').read_text())
    for p,h in lock['sources'].items():assert r.sha(r.W/p)==h,p
    for p,h in lock['evidence'].items():assert r.sha(r.R/p)==h,p
    r.verify_lock();r.resources()
    validation=json.loads((r.R/'VALIDATION.json').read_text())
    log=json.loads((r.R/'runtime/validation_execution.log').read_text())
    assert validation==log and validation['complete'] and validation['paired_rows_recomputed']==114
    failure=json.loads((r.R/'SESSION_FAILURE.json').read_text())
    assert failure['outer_tool_returncode']==143 and failure['child_returncode'] is None
    assert not (r.R/'VALIDATION_EXECUTION.json').exists()
    data=json.loads((r.R/'ATTRIBUTION.json').read_text());selection=json.loads((r.R/'SELECTION.json').read_text())
    assert len(data['records'])==61 and len(data['frames'])==14
    assert len(selection['pairs'])==61 and selection['unique_control_count']==25 and selection['missing_control_count']==8
    frame_indices=collections.defaultdict(set);by_owner=collections.defaultdict(list)
    for row in data['records']:
        c=row['case'];frame_indices[c['raw_path']].update(c['witnesses']['all_local_dense_indices'])
        by_owner[c['stroke_id']].append(row)
    summaries={}
    for sid,rows in sorted(by_owner.items()):
        s={'case_records':len(rows),'missing_control_records':sum(x['control'] is None for x in rows),
           'loss_stages':dict(collections.Counter(x['case']['loss_stage'] for x in rows)),
           'paired_witness_counts':{k:sum(x['case']['witnesses'][k] for x in rows) for k in
              ['local_rejected_count','rejected_but_exact_mesh_visible','rejected_but_analytic_visible',
               'rejected_and_rounded_analytic_rejects','rejected_exact_mesh_other_part','rejected_exact_mesh_occluded_same_part']}}
        unique=collections.Counter();errors=collections.defaultdict(list)
        for path,indices in frame_indices.items():
            if not any(x['case']['raw_path']==path for x in rows):continue
            t=r.load_owner(r.R/path)['trace'];ii=np.array(sorted(indices),int)
            ii=ii[t['inside'][ii]&~t['zpass'][ii]]
            gap=t['z'][ii]-t['exact_mesh_depth'][ii]
            unique['rejected_dense_points']+=len(ii)
            unique['exact_mesh_visible']+=int(((t['exact_mesh_part'][ii]==1)&(abs(gap)<=.006)).sum())
            unique['same_part_exact_occlusion']+=int(((t['exact_mesh_part'][ii]==1)&(gap>.006)).sum())
            unique['other_part_exact_hit']+=int((t['exact_mesh_part'][ii]!=1).sum())
            for k,v in [('point_minus_exact_mesh',gap),('point_minus_rounded_mesh_buffer',t['z'][ii]-t['pixel_depth'][ii]),
                        ('rounded_mesh_ray_minus_buffer',t['rounded_mesh_depth'][ii]-t['pixel_depth'][ii])]:
                errors[k].extend(v[np.isfinite(v)].tolist())
        s['unique_dense_witness_counts']=dict(unique)
        s['unique_dense_depth_ranges_world']={k:{'count':len(v),'min':min(v) if v else None,'max':max(v) if v else None} for k,v in errors.items()}
        summaries[sid]=s
    descriptive={'scope':'All frozen case neighborhoods, unique dense indices within each owner/frame. No changed scientific metric. Paired counts repeat witnesses across neighboring samples; unique counts remove that duplication.',
                 'per_id':summaries,'missing_control_records':[x['pair'] for x in data['records'] if x['control'] is None],
                 'case_flag_patterns':dict(collections.Counter(''.join('1' if b else '0' for b in x['case']['flags']) for x in data['records'])),
                 'control_flag_patterns':dict(collections.Counter(''.join('1' if b else '0' for b in x['control']['flags']) for x in data['records'] if x['control'] is not None))}
    r.write(r.R/'WITNESS_SUMMARY.json',descriptive)
    # All 18 ID/frame crops enlarged only for readability, no ink rescaling.
    panes=[]
    for path in sorted(frame_indices):
        d=r.load_owner(r.R/path);rows=[x for x in data['records'] if x['case']['raw_path']==path]
        targets=[x[g] for x in rows for g in ['case','control'] if x[g] is not None]
        uv=np.array([x['uv'] for x in targets]);lo=np.maximum(0,np.floor(uv.min(axis=0)).astype(int)-5);hi=np.minimum(512,np.ceil(uv.max(axis=0)).astype(int)+6)
        mag=min(6.,180/(hi[0]-lo[0]),140/(hi[1]-lo[1]));newsize=tuple(np.maximum(1,np.rint((hi-lo)*mag).astype(int)))
        views=[('Before z-test',r.ta_down(d['pre_z'])),('After z-test',r.ta_down(d['stages']['raw'])),
               ('Width + AA',d['stages']['downsample']),('ID support',d['identified'].astype(np.uint8)*255),
               ('Hatch influence',d['hatch_leave_one_out_delta'].astype(np.uint8)),('Final influence',d['full_leave_one_out_delta'].astype(np.uint8))]
        pane=Image.new('RGB',(1200,210),'white');pd=ImageDraw.Draw(pane);p=rows[0]['pair']
        pd.text((4,4),f'{p["trajectory"]} {p["frame"]:02d} | {p["stroke_id"]} | nearest-neighbor {mag:.2f}x | red cases / blue controls',fill='black')
        for n,(name,a) in enumerate(views):
            crop=Image.fromarray(255-a).convert('RGB').crop((*lo,*hi)).resize(newsize,Image.Resampling.NEAREST)
            pos=(n*200+(200-newsize[0])//2,55+(140-newsize[1])//2);pane.paste(crop,pos)
            pd.text((n*200+5,30),name,fill='black')
            for x in rows:
                for group,color in [('case','red'),('control','blue')]:
                    if x[group] is None:continue
                    point=(np.array(x[group]['uv'])-lo+.5)*np.array(newsize)/(hi-lo)-.5+pos
                    cx,cy=point;pd.ellipse((cx-2,cy-2,cx+2,cy+2),outline=color,width=1)
        panes.append(pane)
    for start in range(0,len(panes),6):
        page=panes[start:start+6];sheet=Image.new('RGB',(1200,210*len(page)),'white')
        for n,pane in enumerate(page):sheet.paste(pane,(0,210*n))
        sheet.save(r.R/'figures'/f'stage_enlarged_{start//6:02d}.png')
    confirmation={'complete':True,'data_validation_complete':True,'saved_validation_equals_complete_final_log':True,
                  'lost_child_returncode_recovered':False,'outer_failure_retained':True,
                  'original_case_count':61,'original_control_slots':53,'unique_controls':25,'no_control_slots':8,
                  'original_gates_unchanged':True,'all_18_owner_frame_witness_archives_described':len(frame_indices)==18,
                  'recovery_lock_sha256':r.sha(r.D/'RECOVERY_LOCK.json'),'resources':r.resources()}
    r.write(r.R/'CONFIRMATION.json',confirmation)
    r.status('confirmed_data_and_described_pending_report',execution_state='in_progress',
             scientific_verdict='STAGE_AUDIT_COMPLETE_MATCHED_CONTROL_NO_GO',
             blockers=['8 of 61 cases have no same-ID same-frame eligible supported control',
                       '11 cases have mixed stage support; no single renderer defect established for all cases',
                       'Original validation outer session returned 143; child exit status unknown despite complete written data',
                       'Procedural GT only; inherited limited coverage; P1 and reconstructed lamp not established'])
    print(json.dumps({'confirmation_complete':True,'owner_frame_archives':len(frame_indices),'per_id':summaries}),flush=True)


if __name__=='__main__':main()
