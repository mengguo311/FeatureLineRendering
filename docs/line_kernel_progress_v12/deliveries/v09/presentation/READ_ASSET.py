from pathlib import Path
import json,numpy as np
r=Path(__file__).parent
for x in json.loads((r/'ASSET_INDEX.json').read_text()):
 g=np.load(r/x['gaussians'],allow_pickle=False);m=np.load(r/x['membership'],allow_pickle=False);q=np.load(r/x['models'],allow_pickle=False)
 assert len(g['means'])==x['rows']==len(m['edge_id'])
 assert np.array_equal(m['line_kernel_id'],np.arange(x['rows']))
 print(x['namespace'],x['scene'],x['unit'],x['arm'],x['rows'],int((m['edge_id']>=0).sum()),'COLD_LOAD_OK')
