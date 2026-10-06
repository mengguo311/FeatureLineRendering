"""Hash the explicitly tracked stage delivery, excluding this manifest itself."""
import runtime as rt
import collections,json,re,subprocess,time

def main():
    target=rt.ART/'results/DELIVERY_INVENTORY.json'
    scopes=[str(p.relative_to(rt.ROOT)) for p in (rt.EXP,rt.ART,rt.OUT)]
    names=subprocess.check_output(['git','ls-files','-z','--',*scopes],cwd=rt.ROOT).decode().split('\0')
    records={}
    for name in sorted(set(n for n in names if n)):
        path=rt.ROOT/name
        if path==target:continue
        assert path.is_file() and not path.is_symlink(),name
        assert any(path.is_relative_to(p) for p in (rt.EXP,rt.ART,rt.OUT)),name
        assert path.stat().st_size<100_000_000,name
        assert path.suffix not in ('.pdf','.so','.pyc'),name
        assert not name.endswith(('_author.txt','.source.full.html')),name
        records[name]=dict(bytes=path.stat().st_size,sha256=rt.sha(path))
    count=collections.Counter((rt.ROOT/n).suffix for n in records)
    seals=list((rt.ART/'seals').glob('*.json'));missing=[];cached=set()
    for seal in seals:
        for name,value in json.loads(seal.read_text())['files'].items():
            if name.startswith(str(rt.OUT.relative_to(rt.ROOT))+'/'):
                cached.add(name);continue
            if name not in records or records[name]['sha256']!=value:missing.append(name)
    assert not missing,missing
    logs=[json.loads(line) for line in (rt.ART/'logs/resources.jsonl').read_text().splitlines()]
    links=[]
    for doc in ['REPORT_ZH.md','RESEARCH_ZH.md','REPRODUCE.md','INDEX.html']:
        text=(rt.ART/doc).read_text()
        for link in re.findall(r'\]\(([^)]+)\)',text)+re.findall(r'(?:href|src)="([^"]+)"',text):
            if link.startswith(('http','data:','#')):continue
            assert (rt.ART/link.split('#')[0]).exists(),(doc,link)
            links.append(dict(document=doc,target=link))
    status=dict(status='PASS_DELIVERY_INVENTORY',utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        scientific_verdict='NO_GO_CONTOUR_OVERFILL',shape_status='PARTIAL_SHAPE_RECOVERY',
        manifest_excludes_itself=True,tracked_stage_files=len(records),tracked_stage_bytes=sum(v['bytes'] for v in records.values()),
        suffix_counts=dict(count),primary_scene_count=2,primary_asset_arms_per_scene=4,additional_diagnostic_assets=2,
        primary_reserved_views=16,complete_videos=2,frames_per_video=33,
        source_PLYs='Original SH3 seed1729 iteration30000 read-only inputs; hashes in INPUT_FREEZE.json',
        codex_model=dict(model='gpt-6-astra',reasoning_effort='ultra',config_unchanged=True),
        seals=len(seals),all_sealed_noncache_files_in_delivery=True,ignored_reconstructable_render_caches=len(cached),
        cache_rebuild_tool='experiments/'+rt.TAG+'/hydrate_render_cache.py',
        root_free_min_bytes=min(v['root_free'] for v in logs),shared_git_free_min_bytes=min(v['git_free'] for v in logs),
        stage_peak_observed_bytes=max(v['stage_bytes'] for v in logs),resource_samples=len(logs),
        checked_local_links=links,files=records)
    rt.atomic_json(target,status)
    print(json.dumps({k:v for k,v in status.items() if k not in ('files','checked_local_links')},ensure_ascii=False))

if __name__=='__main__':main()
