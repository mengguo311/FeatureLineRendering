from runtime import *
lock=json.loads((ROOT/'orchestration/INPUT_LOCK.json').read_text())
forbidden={v['original_model'] for v in lock['scenes'].values()}
phase=sys.argv[1]; result={};start=time.monotonic()
for p,want in lock['files'].items():
    check_budget(180)
    if p in forbidden:
        result[p]=dict(status='EXCLUDED_NOT_READ',reason='Forbidden source-GS, not a scientific input');continue
    got=sha(p);result[p]=dict(expected=want,actual=got,match=got==want)
    if got!=want:
        js(OUT/f'INPUT_HASHES_{phase}.json',result);raise AssertionError('INPUT_HASH_MISMATCH '+p)
extra=[RENDER_CODE/'format.py',RENDER_CODE/'renderer.py',RENDER_CODE/'common.py',
       BASE.parent/'c2l50_8build_joint_gs_v01/build/libjoint.so',BASE.parent/'official_code_fix_v01/source/utils/sh_utils.py']
for p in extra:
    if str(p) not in result:result[str(p)]=dict(actual=sha(p),status='CONSUMED_HELPER_HASHED')
js(OUT/f'INPUT_HASHES_{phase}.json',result)
if phase=='after':
    before=json.loads((OUT/'INPUT_HASHES_before.json').read_text())
    assert result==before,'Inputs/helpers changed during run'
print('HASH_AUDIT',phase,'verified',len(result)-len(forbidden),'forbidden_skipped',len(forbidden),'seconds',time.monotonic()-start)
