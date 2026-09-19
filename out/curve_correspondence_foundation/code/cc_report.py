"""Numerical decision logic and mechanically consistent Markdown."""

def arm_gates(summary,g):
    return dict(G1=bool(summary['yield_pass']),G2=bool(summary['fit_pass'] and summary['C_pass'] and summary['DEV_pass'] and summary['C_coverage']>=g['C_track_coverage'] and summary['DEV_coverage']>=g['DEV_track_coverage']),G3=bool(summary['repeat_pass']),G4=bool(summary['certificate'] and summary['C_null'] and summary['DEV_null']))

def core_verdict(scenes):
    values=list(scenes.values())
    if any(v in ['ENGINEERING_NOT_READY','UNDETERMINED'] for v in values):return 'ENGINEERING_NOT_READY'
    if 'STOP_CORRESPONDENCE' in values:return 'STOP_CORRESPONDENCE'
    if 'INSUFFICIENT_POSTERIOR_QUALITY' in values:return 'INSUFFICIENT_POSTERIOR_QUALITY'
    if all(v=='PIVOT_IMAGE_ONLY' for v in values):return 'PIVOT_IMAGE_ONLY'
    if all(v=='FOUNDATION_GO' for v in values):return 'FOUNDATION_GO'
    if all(v in ['FOUNDATION_GO','CURVE_CORRESPONDENCE_GO_MANUAL_PENDING'] for v in values):return 'CURVE_CORRESPONDENCE_GO_MANUAL_PENDING'
    return 'UNDETERMINED'

def markdown(result):
    text=['# Curve correspondence foundation results','',f"Core machine verdict: **{result['core_verdict']}**.",'','One frozen non-learning correspondence formulation; no mesh, neural field, GS retraining, ICP or per-asset scaling.','', '| Scene | Route | Segments | Candidate pairs | Selected pairs | Identity hypotheses | Image curves | GS curves | Verdict |','|---|---|---:|---:|---:|---:|---:|---:|---|']
    for r in result['scenes']:
        text.append(f"| {r['scene']} | {r.get('qualifier','NONE')} | {r.get('segments',0)} | {r.get('candidates',0)} | {r.get('pairs',0)} | {r.get('identities',0)} | {r.get('image_tracks',0)} | {r.get('gs_tracks',0)} | {r['verdict']} |")
    text+=['','## Exact primary and execution totals','','| Quantity | Count |','|---|---:|']
    for k,v in sorted(result['totals'].items()):text.append(f'| {k} | {v} |')
    text+=['','These are primary F counts; repeated/ablation curves are not independent primary tracks. All arm counts and rejection reasons are in the per-scene records. Empty denominators cannot pass a gate.','', '## Machine gates','', '| Scene / arm | G1 yield | G2 prediction | G3 repeatability | G4 identity/nulls |','|---|---|---|---|---|']
    for r in result['scenes']:
        for arm,gates in r.get('gates',{}).items():text.append('| '+r['scene']+' / '+arm+' | '+' | '.join('PASS' if gates[g] else 'FAIL' for g in ['G1','G2','G3','G4'])+' |')
    text+=['','## Interpretation and review status','','Necessary machine-gate failure is determinate even while visual review is pending. Zero independent reviews have occurred. The randomized review package is prepared, with keys outside it; no internal inspection is described as independent.','', 'GS is a post-identity support/visibility veto in this formulation. Retained geometry is unchanged by construction; only error/coverage benefit could justify a frozen-GS claim. Image-only posterior invariance is structural, not measured GS evidence.','', 'C and DEV score frozen outputs. All-in-frame scoring is conservative about occlusion, with denominators retained. Detector residuals are not geometric truth or independent semantic precision. Prior internal challenge boxes are coarse diagnostics only.','', 'Drums and Ficus remain INSUFFICIENT_POSTERIOR_QUALITY; neither blocks the per-scene core machine verdict. Lego cannot claim independent-seed invariance. The failed corrected local-pixel baseline yielded zero accepted positions in both core scenes, including image-only.','', 'This result tests the registered minimal formulation, not the impossibility of classical curve SfM. There was no threshold rescue, detector change, hand selection of successful tracks, gap completion or final UDF/stroke investment.','', '## Artifact access','','See `scenes/SCENE/F/` for ordered extraction, every proposed candidate, alternatives, cycles, accepted/rejected fits, LOO arms and the F seal. `scenes/SCENE/C/` is the independent C reconstruction; `repeats/` holds every eligible posterior veto. `evaluation/SCENE/` contains per-view held-out predictions, repeatability, actual PNG/MP4 and review packages. Large compressed arrays/traces stay server-side and are exactly inventoried in MANIFEST.json.','', 'Verification, access audit, raw RED/GREEN evidence and reproduction instructions are separate artifacts.']
    return '\n'.join(text)+'\n'

def verify_markdown(result,text):
    return text==markdown(result)
