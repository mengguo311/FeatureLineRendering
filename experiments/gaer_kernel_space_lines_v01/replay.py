"""Deterministic replay to new-stage out/, keeping frozen delivered assets intact."""
import json
import numpy as np
import runtime as rt
from core import build_graph,mesh_and_glb

def main():
    rt.guard('deterministic_graph_replay')
    f=json.loads((rt.ART/'INPUT_FREEZE.json').read_text());results={}
    for scene,rec in f['scenes'].items():
        z=np.load(rt.ROOT/rec['selected_npz']);g=build_graph(z['xyz'],z['original_ids'])
        frozen=np.load(rt.ART/'assets'/scene/'FULL_GRAPH.npz')
        for key in ['xyz','ids','neighbors','local_scale','tangent','eigenvalues','linearity','candidate_pairs','distance','distance_limit','alignment','endpoint_knn_rank','reason_A','reason_B','choices','A','B']:
            np.testing.assert_array_equal(g[key],frozen[key])
        assert g['radius']==float(frozen['radius'])
        arms={};dst=rt.OUT/'replay'/scene;dst.mkdir(parents=True,exist_ok=True)
        for arm in ['A','B']:
            v,faces,data=mesh_and_glb(g['xyz'],g[arm],g['radius']);p=dst/(arm+'.glb');rt.scoped(p).write_bytes(data)
            assert data==(rt.ART/'assets'/scene/arm/'candidate_graph.glb').read_bytes()
            arms[arm]=dict(glb_byte_exact=True,edges=len(g[arm]),glb_sha256=rt.sha(p))
        results[scene]=dict(all_graph_arrays_exact=True,arms=arms)
    rt.write_json(rt.ART/'REPLAY_VERIFICATION.json',dict(status='PASS',utc=rt.utc(),scenes=results,original_assets_overwritten=False))
    rt.guard('deterministic_graph_replay_complete')
    print(json.dumps(dict(status='PASS',scenes=results)))
if __name__=='__main__':main()
