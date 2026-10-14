import os,json,shutil,tarfile,zipfile,hashlib,time,traceback
from common import *
start=time.time();status('PACKAGING',children=[os.getpid()],next_action='Independent archive member verification')
try:
    assert shutil.disk_usage('/').free>2**30 and shutil.disk_usage(T).free>10*2**30
    code=T/'code';code.mkdir(exist_ok=True)
    for p in C.glob('*.py'):shutil.copy2(p,code/p.name)
    write(T/'CODE_FINAL_SHA.json',{str(p):sha(p) for p in sorted(C.glob('*.py'))})
    (T/'ASTRA_FINAL.md').write_text(f'''# 本轮实际完成

完成16预设×11原生视角，共176组soft/darkness/marked/skeleton与候选显示。scan24、scan65各5视角，Ficus固定train_r_80一视角。176张候选PNG、176张二值PNG、176张骨架PNG；33套分析字段；16项单元测试通过，176组回读一致，10张DTU A20与旧05缓存位级一致，3次全分析及单预设CLI复算一致。冻结来源29项未改变，旧boundary SHA不变。

暂定选图范围：建筑C2U20/A40/C1L50；头骨A40/C1L50/C2U20；Ficus A30/C1U20/M75T30。这些是可选项，不是用户已选定方案。B00过度删线，完整保留为负例。粗尺度可能合并细窗格、齿间或小叶边界；灰度变淡不等于真实信噪比提升，请一并看二值候选。没有GT SNR排名，没有新3D模型，没有自动重跑05。

优先下载图：
- {T}/scenes/scan24/0000/THRESHOLD.jpg
- {T}/scenes/scan24/0000/SCALE.jpg
- {T}/scenes/scan65/0000/THRESHOLD.jpg
- {T}/scenes/scan65/0000/MIX.jpg
- {T}/selection/scan24_0036_CHOICES.jpg
- {T}/selection/scan65_0036_CHOICES.jpg
- {T}/selection/scan65_0036_BINARY.jpg
- {T}/selection/scan24_C2U20_ALL5.jpg
- {T}/selection/scan65_A40_ALL5.jpg
- {T}/selection/ficus_train_r_80_CHOICES.jpg

完整解释：REPORT_ZH.md；快速选图：SELECTION_GUIDE_ZH.md；本地原生图索引：GALLERY.html。场景和视角条件见REGISTRY/SOURCE_FREEZE，Ficus不是RaDe训练来源。历史EVAL已见，不是盲测。

PREVIEWS.tar.gz为精选原生对照板；NATIVE_scan24/scan65/ficus.zip是全部候选原生PNG和参数（黑白/骨架在完整包）；DELIVERABLE.tar.gz含代码、float32 RGB便携输入、全部地图/图片/报告。各包的SHA256与独立MEMBERS清单在同目录，最终哈希/大小及解包成员复核结果见PACKAGE_VERIFY.json。实时STATUS及最终包验证清单在包外，避免打包自引用；包内CONTENT_COMPLETE.json记录内容完成范围。

本轮到此停止，children[]、no_automatic_continuation=true；不进行新训练、融合或源GS修改。
''')
    write(T/'CONTENT_COMPLETE.json',dict(phase='DETECTOR_CONTENT_COMPLETE',completed_presets=16,completed_views=11,completed_units=176,new_3d_models=0,children=[],no_automatic_continuation=True,package_verification='External PACKAGE_VERIFY.json and STATUS.json'))
    # Keep executable/code provenance separate from original inputs; omit launcher logs.
    excluded={'AGENT_LAUNCH.json','PROMPT.txt','launch.py','stderr.log','stdout.log','STATUS.json','RESULTS_MANIFEST.json','OUTPUTS_MANIFEST.json','PACKAGE_VERIFY.json','PACKAGE_EXIT.json'}
    def payloads():
        return sorted(p for p in T.rglob('*') if p.is_file() and p.name not in excluded and not (p.parent.name=='logs' and p.name.startswith('package')) and not p.name.endswith(('.tar.gz','.zip','.sha256','.MEMBERS.json','.tmp')))
    files=payloads()
    inventory=[dict(path=str(p),relative=str(p.relative_to(T)),bytes=p.stat().st_size,sha256=sha(p)) for p in files]
    write(T/'OUTPUTS_MANIFEST.json',dict(utc=utc(),files=inventory,scope='Content before archives. STATUS/package verification are external to avoid self-reference.'))
    files.append(T/'OUTPUTS_MANIFEST.json')
    previews=[T/'REPORT_ZH.md',T/'SELECTION_GUIDE_ZH.md',T/'ASTRA_FINAL.md',T/'PRESETS.json',T/'COUNTS.json',T/'CONTENT_COMPLETE.json']
    for scene,v in [('scan24','0000'),('scan65','0000'),('ficus','train_r_80')]:
        previews += [T/'scenes'/scene/v/(f+'.jpg') for f in ['THRESHOLD','MIX','SCALE']]
    for name in ['scan24_0036_CHOICES.jpg','scan65_0036_CHOICES.jpg','scan24_C2U20_ALL5.jpg','scan65_A40_ALL5.jpg','scan65_C1L50_ALL5.jpg','ficus_train_r_80_CHOICES.jpg','scan24_0000_BINARY.jpg','scan65_0036_BINARY.jpg','ficus_train_r_80_BINARY.jpg','scan24_ROI_windows.jpg','scan65_ROI_eyes_nose_teeth.jpg','ficus_ROI_leaves_stems.jpg']:
        previews.append(T/'selection'/name)
    previews.append(T/'analytic'/'CONTRAST_SWEEP.jpg')
    # Conservative bound before compressed tar. No thumbnail replacement.
    assert sum(p.stat().st_size for p in previews)<20*2**20,'Preview content exceeds promised budget'
    verified=[]
    def members(ps):return [dict(name=str(p.relative_to(T)),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(set(ps))]
    def verify_tar(path,expected):
        d={x['name']:x for x in expected}
        with tarfile.open(path,'r:gz') as a:
            ms=a.getmembers();assert len(ms)==len(d)
            for m in ms:
                assert m.isfile() and m.name in d
                f=a.extractfile(m);h=hashlib.sha256();size=0
                for block in iter(lambda:f.read(2**20),b''):h.update(block);size+=len(block)
                assert size==d[m.name]['bytes'] and h.hexdigest()==d[m.name]['sha256']
    def make_tar(name,ps):
        records=members(ps);out=T/(name+'.tar.gz')
        write(T/(name+'.MEMBERS.json'),dict(files=records))
        with tarfile.open(out,'w:gz',compresslevel=6) as a:
            for r in records:a.add(T/r['name'],arcname=r['name'],recursive=False)
        verify_tar(out,records);h=sha(out);(T/(name+'.tar.gz.sha256')).write_text(h+'  '+out.name+'\n')
        verified.append(dict(path=str(out),bytes=out.stat().st_size,sha256=h,members=len(records),independent_members_readback=True))
        print(name,out.stat().st_size,flush=True)
    def make_zip(scene):
        ps=list((T/'scenes'/scene).glob('*/presets/*/candidate.png'))+list((T/'scenes'/scene).glob('*/presets/*/recipe.json'))+list((T/'scenes'/scene).glob('*/RGB.png'))+[T/'PRESETS.json',T/'SELECTION_GUIDE_ZH.md']
        name='NATIVE_'+scene;records=members(ps);out=T/(name+'.zip');write(T/(name+'.MEMBERS.json'),dict(files=records))
        with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for r in records:z.write(T/r['name'],r['name'])
        with zipfile.ZipFile(out) as z:
            assert len(z.infolist())==len(records) and z.testzip() is None
            for r in records:assert hashlib.sha256(z.read(r['name'])).hexdigest()==r['sha256']
        h=sha(out);(T/(name+'.zip.sha256')).write_text(h+'  '+out.name+'\n')
        verified.append(dict(path=str(out),bytes=out.stat().st_size,sha256=h,members=len(records),independent_members_readback=True))
        print(name,out.stat().st_size,flush=True)
    make_tar('PREVIEWS',previews)
    for s in ['scan24','scan65','ficus']:make_zip(s)
    make_tar('DELIVERABLE',files)
    # Independently check the content inventory against final on-disk bytes,
    # in addition to checking each compressed member. Live logs are excluded.
    assert all(sha(r['path'])==r['sha256'] for r in inventory)
    total=sum(p.stat().st_size for p in T.rglob('*') if p.is_file());assert total<3*2**30
    assert shutil.disk_usage('/').free>2**30 and shutil.disk_usage(T).free>10*2**30
    original=json.loads((T/'SOURCE_FREEZE.json').read_text())['files'];assert all(sha(p)==h for p,h in original.items())
    write(T/'PACKAGE_VERIFY.json',dict(utc=utc(),packages=verified,task_total_bytes=total,task_cap_bytes=3*2**30,all_sources_unchanged_after_packaging=True,root_free_GiB=shutil.disk_usage('/').free/2**30,hdd_free_GiB=shutil.disk_usage(T).free/2**30,seconds=time.time()-start))
    write(T/'RESULTS_MANIFEST.json',dict(utc=utc(),method='Spatial RGB RGB-only preset sweep; no 3D production',counts=json.loads((T/'COUNTS.json').read_text()),source_manifest_sha256=sha(T/'SOURCE_FREEZE.json'),output_inventory=dict(path=str(T/'OUTPUTS_MANIFEST.json'),sha256=sha(T/'OUTPUTS_MANIFEST.json')),packages=verified,preview_absolute_paths=[str(p) for p in previews],code_manifest_sha256=sha(T/'CODE_FINAL_SHA.json'),provisional_choices=__import__('selection_boards').CHOICES))
    write(T/'PACKAGE_EXIT.json',dict(exit_code=0,pid=os.getpid(),utc=utc(),seconds=time.time()-start))
    status('COMPLETE',status='DONE_WITH_LIMITATIONS',children=[],completed_presets=16,completed_views=11,completed_units=176,visual_verdict='Useful selectable changes with visible detail-loss tradeoffs; no GT SNR or universal best claim',next_action='STOP. User may choose preset IDs; no automatic pipeline run',packages_verified=5,unit_tests_passed=16,source_unchanged=True)
except BaseException:
    write(T/'PACKAGE_EXIT.json',dict(exit_code=1,pid=os.getpid(),utc=utc(),traceback=traceback.format_exc()));status('PACKAGING_FAILED',children=[],last_event=traceback.format_exc());raise
