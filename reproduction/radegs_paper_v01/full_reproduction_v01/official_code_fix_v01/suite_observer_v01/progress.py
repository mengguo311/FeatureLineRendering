def counts(rows):
    result={'train_started':0,'train_completed':0,'export_completed':0,'mesh_completed':0,'official_metrics':0,'quality_review_passed':0}
    mapping={'train':'train_completed','export':'export_completed','tsdf':'mesh_completed','eval':'official_metrics','quality_review':'quality_review_passed'}
    for row in rows:
        stages=set(row.get('verified_stages',[]))
        result['train_started']+=int(row.get('iteration_records',0)>0 or 'train' in stages)
        for stage,key in mapping.items():result[key]+=int(stage in stages)
    return result
