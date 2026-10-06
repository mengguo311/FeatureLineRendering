import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from runtime import *
from data import *
from renderer_adapter import load_checkpoint
from evaluation import prepare
from color_operator import ColorOperator
import torch,numpy as np
resource_guard();before=input_snapshot();atomic_json(OUT/'original_inputs_before.json',before)
manifest=freeze_data();m=load_checkpoint(CHECKPOINT);uids,labels,selected=selection();views=prepare(manifest,m,('train','dev-in','dev-out'))
records=[]
for subset in (selected,np.ones(len(uids),bool)):
    # Real B0, train + actual failing development camera, same exact operator before production fit.
    operator=ColorOperator(m,[views[0],views[-1]],torch.tensor(subset,device='cuda'));records.append(operator.validate())
assert input_snapshot()==before
original=json.loads((INPUT/'models/panels_high/actual_config.json').read_text())
train_manifest=json.loads((V1/'experiments/object_neighborhood_edge_control_v1/results/manifests/train_panels_high.json').read_text())
atomic_json(ART/'PRECHECK.json',{'base_commit':'245e0560665dc45c41420f6aa2ab32782504d782','checkpoint_sha256':sha(CHECKPOINT),'selection_sha256':sha(SELECTION),'identity_sha256':sha(IDENTITY),'input_snapshot_sha256':sha(OUT/'original_inputs_before.json'),'input_count':len(before),'input_unchanged_after_native_integration':True,'native_operator_actual_checkpoint_tests':records,'original_training_source_commit':train_manifest['source']['commit'],'original_training_source_hashes':train_manifest['source']['source_sha256'],'G00_policy':'rerun all four arms with same native training loop; no unverifiable reuse claim','guard':resource_guard(),'python':PYTHON,'torch_version':torch.__version__,'gpu':torch.cuda.get_device_name(0),'test_state':'TEST_CLOSED'})
print(json.dumps({'input_count':len(before),'checkpoint':sha(CHECKPOINT),'operator_tests':records},indent=2))
