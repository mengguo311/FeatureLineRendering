"""Manual coarse region records transcribed from TRAIN-only contacts by Codex."""
import json,sys
from pathlib import Path
sys.path.insert(0,'.')
from src.foundation import freeze_json
from src.multiscene_training import utc,sha256
root=Path('out/multiscene_foundation'); out=root/'annotations'
targets={
'lego':[(1,[102,118,178,212],'cab posts and roof seams'),(1,[178,51,278,115],'bucket rim and hinge assembly'),(53,[56,203,215,252],'side chassis boundary'),(79,[150,238,240,317],'front panel seams')],
'chair':[(1,[195,52,328,200],'fabric to back-frame seam'),(1,[90,125,266,305],'seat upholstery piping'),(27,[151,252,285,299],'seat to lower frame boundary'),(79,[88,169,267,303],'seat border and arm attachments')],
'drums':[(1,[188,112,253,178],'upper tom physical rim'),(1,[283,176,321,287],'bass drum hoop'),(1,[105,287,174,365],'cymbal stand junctions'),(27,[190,97,253,160],'tom rim and shell seam')],
'ficus':[(1,[181,173,220,274],'trunk and branch junctions'),(1,[166,258,228,280],'planter lip'),(27,[174,126,224,241],'branch junctions'),(79,[179,201,228,261],'lower trunk junctions')]
}
# Boxes are coarse diagnostic regions, not exact edge spans or 3D correspondences.
challenges={
'lego':{'repeated_texture':[[33,274,233,335],[92,312,279,361],[17,234,359,280]],'shadow_highlight':[[159,119,200,217],[137,119,233,227],[51,187,207,243]],'smooth_silhouette':[[82,209,175,265],[123,276,242,319],[55,202,213,251]],'multilayer':[[174,61,257,171],[153,59,266,174],[130,86,302,207]]},
'chair':{'repeated_texture':[[124,145,259,279],[119,249,291,292],[154,70,267,164]],'shadow_highlight':[[207,64,300,122],[165,166,309,250],[80,143,181,236]],'smooth_silhouette':[[194,49,324,197],[170,143,325,265],[82,139,149,231]],'multilayer':[[104,115,188,183],[104,159,176,270],[106,186,284,276]]},
'drums':{'repeated_texture':[[136,222,254,314],[81,199,207,277],[222,199,302,268]],'shadow_highlight':[[136,222,254,314],[81,199,207,277],[144,51,211,76]],'smooth_silhouette':[[70,151,127,204],[86,130,141,179],[83,182,146,213]],'multilayer':[[133,147,283,267],[115,145,291,276],[110,141,267,267]]},
'ficus':{'repeated_texture':[[161,83,270,179],[131,54,266,162],[138,116,293,219]],'shadow_highlight':[[162,289,231,333],[166,290,235,333],[196,208,240,263]],'smooth_silhouette':[[158,266,236,344],[158,267,237,345],[200,214,244,266]],'multilayer':[[160,148,251,215],[158,138,248,215],[145,134,255,213]]}
}
for scene in targets:
 value=dict(author='Codex implementing assistant',created_utc=utc(),image_domain='TRAIN only, 400px original image coordinates',
  independent=False,method_output_seen=False,kind='coarse internal target candidates and challenge rectangles',
  certified_target_spans=0,required_cross_view_target_spans=12,
  limitation='These four candidate regions are not twelve precise spans with verified >=3 F-view correspondences. No independent annotator is available. No precision or G5 certification may use them.',
  targets=[dict(view=v,box=box,label=label) for v,box,label in targets[scene]],
  challenges=[dict(view=v,box=boxes[k],category=cat) for cat,boxes in challenges[scene].items() for k,v in enumerate([1,27,53])],
  contact_sha256=sha256(out/f'{scene}_train.png'))
 freeze_json(out/f'{scene}_internal.json',value)
print('frozen 16 internal target candidates, 48 coarse challenge rectangles; zero certified spans')
