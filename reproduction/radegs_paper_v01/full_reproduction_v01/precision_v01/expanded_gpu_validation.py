"""Serial full original smoke + expanded precision checks, behind shared gate."""
import argparse
import json
import os
from pathlib import Path
from safety import sha256,atomic_json
from gpu_stages import smoke,report


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--config',required=True);args=ap.parse_args()
    cfg=json.loads(Path(args.config).read_text())
    assert os.environ['CUDA_VISIBLE_DEVICES']==cfg['allowed_gpu_uuids'][0]
    from diff_gaussian_rasterization import _C
    native=Path(_C.__file__).resolve()
    assert str(native)==cfg['candidate_native'] and sha256(native)==cfg['inputs']['candidate_native']
    native_receipt=Path(cfg['state_dir'])/'actual_native.json'
    atomic_json(native_receipt,{'path':str(native),'sha256':sha256(native)})
    # The original GPU tests, oracle and tolerances are unmodified.
    smoke(cfg)
    from gpu_geometry_extended import main as extended
    ext=extended(cfg)
    smoke_report=Path(cfg['reports']['smoke']);sr=json.loads(smoke_report.read_text())
    assert sr['status']=='PASS' and sr['inputs']==cfg['inputs']
    report(cfg,'checkpoint_diagnostic',[native_receipt,smoke_report,*sr['outputs'],ext],
           {'operation':'candidate full original smoke plus real-covariance/rotated-camera oracle',
            'optimizer_steps':0,'training_ready_requires_evidence_review':True})


if __name__=='__main__':main()
