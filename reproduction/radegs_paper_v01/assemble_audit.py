"""Assemble documentation from stage-1 evidence. Never launches research workloads."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/radegs_paper_reproduction_v01'
E = OUT / 'evidence'
HDD = Path('/mnt/hdd1/u00134/radegs_paper_reproduction_v01')
REPO = HDD / 'sources/RaDe-GS'
SHA = {'C24': '2d4bc087f1b4bd62c96054fbe89d273490526b81', 'C25': '0b1fe5fe2d7655d3bfbd584862788cd449e24ef6', 'C26': 'd72f20792005ae1d6555a82aa2d15345f247604e'}
DTU = [24, 37, 40, 55, 63, 65, 69, 83, 97, 105, 106, 110, 114, 118, 122]
TNT = ['Barn', 'Caterpillar', 'Courthouse', 'Ignatius', 'Meetingroom', 'Truck']
OUTDOOR = ['bicycle', 'flowers', 'garden', 'stump', 'treehill']
INDOOR = ['room', 'counter', 'kitchen', 'bonsai']
SYNTHETIC = ['mic', 'chair', 'ship', 'materials', 'lego', 'drums', 'ficus', 'hotdog']


def read(p):
    return json.loads(p.read_text())


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def ref(version, path, start, end=None):
    return f'https://github.com/HKUST-SAIL/RaDe-GS/blob/{SHA[version]}/{path}#L{start}' + (f'-L{end}' if end else '')


def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    references = {
        'paper': 'https://arxiv.org/pdf/2406.01467v2',
        'paper_loss_setup': 'https://arxiv.org/pdf/2406.01467v2#page=6',
        'paper_tables_1_2_3': 'https://arxiv.org/pdf/2406.01467v2#page=7',
        'paper_table4': 'https://arxiv.org/pdf/2406.01467v2#page=8',
        'C24_release_scope': ref('C24', 'README.md', 8, 45),
        'C24_defaults': ref('C24', 'arguments/__init__.py', 47, 97),
        'C24_loss': ref('C24', 'train.py', 130, 165),
        'C24_edge': ref('C24', 'scene/cameras.py', 67, 77),
        'C24_distortion_forward': ref('C24', 'submodules/diff-gaussian-rasterization/cuda_rasterizer/forward.cu', 746, 799),
        'C24_distortion_backward': ref('C24', 'submodules/diff-gaussian-rasterization/cuda_rasterizer/backward.cu', 826, 861),
        'C24_depth_mapping_planes': ref('C24', 'submodules/diff-gaussian-rasterization/cuda_rasterizer/auxiliary.h', 20, 21),
        'C24_depth_normal_output': ref('C24', 'gaussian_renderer/__init__.py', 19, 90),
        'C24_camera_loader': ref('C24', 'scene/dataset_readers.py', 119, 180),
        'C24_colmap_split_init': ref('C24', 'scene/dataset_readers.py', 220, 271),
        'C24_synthetic_split_init': ref('C24', 'scene/dataset_readers.py', 274, 350),
        'C24_resolution': ref('C24', 'utils/camera_utils.py', 20, 56),
        'C24_filter': ref('C24', 'scene/gaussian_model.py', 174, 225),
        'C24_densification': ref('C24', 'scene/gaussian_model.py', 663, 747),
        'C24_training_schedule': ref('C24', 'train.py', 184, 214),
        'C24_seed': ref('C24', 'utils/general_utils.py', 114, 135),
        'C24_mesh': ref('C24', 'mesh_extract.py', 20, 107),
        'C24_eval_alignment': ref('C24', 'evaluate_dtu_mesh.py', 149, 214),
        'C24_eval_calibration': ref('C24', 'evaluate_dtu_mesh.py', 60, 75),
        'C24_eval_metric': ref('C24', 'dtu_eval/eval.py', 98, 165),
        'C24_license': ref('C24', 'LICENSE.md', 31, 59),
        'C25_modifications': ref('C25', 'README.md', 8, 15),
        'C25_data_commands': ref('C25', 'README.md', 57, 104),
        'C25_tnt_evaluator': ref('C25', 'eval_tnt/run.py', 58, 195),
        'C25_tnt_thresholds': ref('C25', 'eval_tnt/config.py', 32, 41),
        'C25_nvs_metrics': ref('C25', 'metric.py', 62, 103),
        'C26_new_scope': ref('C26', 'README.md', 8, 80),
        'C26_new_defaults': ref('C26', 'arguments/__init__.py', 58, 112),
        'C26_dtu_script': ref('C26', 'scripts/dtu.sh', 1, 7),
        'C26_tnt_script': ref('C26', 'scripts/tnt.sh', 1, 12),
    }
    critical_files = ['README.md', 'LICENSE.md', '.gitmodules', 'requirements.txt', 'arguments/__init__.py', 'train.py', 'gaussian_renderer/__init__.py', 'scene/dataset_readers.py', 'scene/cameras.py', 'scene/gaussian_model.py', 'utils/camera_utils.py', 'utils/graphics_utils.py', 'utils/general_utils.py', 'mesh_extract.py', 'evaluate_dtu_mesh.py', 'dtu_eval/eval.py', 'submodules/diff-gaussian-rasterization/cuda_rasterizer/forward.cu', 'submodules/diff-gaussian-rasterization/cuda_rasterizer/backward.cu', 'submodules/diff-gaussian-rasterization/cuda_rasterizer/auxiliary.h']
    files = []
    for path in critical_files:
        p = REPO / path
        files.append({'path': path, 'absolute_path': str(p), 'bytes': p.stat().st_size, 'sha256_exact_working_file_bytes': hashlib.sha256(p.read_bytes()).hexdigest(), 'git_blob_oid': subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD:' + path], text=True).strip(), 'immutable_url': ref('C24', path, 1)})
    versions = read(E / 'source_versions.json')
    versions['clone']['status_at_initial_snapshot'] = versions['clone'].pop('status_porcelain')
    manifest = {
        'schema_version': 1, 'audit_utc': now, 'scope': 'stage1_source_data_environment_audit_only',
        'workspace': str(ROOT), 'branch': 'gaer-rade-depth-lift-v01', 'base_commit': '52a409b806fd5d326ccce0d5657e25336beb68d5',
        'official_repository': 'https://github.com/HKUST-SAIL/RaDe-GS', 'historical_project_code_link': 'https://github.com/BaowenZ/RaDe-GS',
        'versions': versions, 'clone_verification': read(E / 'clone_verification.json'),
        'paper_and_project_acquisition': read(E / 'web_acquisition.json'),
        'references': references, 'C24_critical_files': files,
        'version_differences': [
            {'from': 'C24', 'to': 'C25', 'evidence': ['evidence/C24_C25_name_status.txt', 'evidence/C24_C25_core.diff'], 'findings': ['新增逐像素cos(theta)深度/坐标图选项；README明确删除depth distortion；normal默认仍0.05', '新增tetrahedra、TNT evaluator、render.py、metric.py；README所写metrics.py并不存在', '2024-07-27深度反传、2024-08-06新公式、2024-08-23二维滤波修复属于后续历史，不能静默回填C24']},
            {'from': 'C25', 'to': 'C26', 'evidence': ['evidence/C25_C26_name_status.txt', 'evidence/C25_C26_core.diff'], 'findings': ['PGSR multi-view geo/NCC、warp-patch-ncc、appearance整数模式3', 'normal开始迭代从15000变7000；Python3.12/cu130说明；Objaverse深度法线GT评测', 'scripts/dtu.sh与scripts/tnt.sh是C26证据，不能称作2024复现脚本']},
        ],
        'provenance_limits': ['C24是论文同期候选源码，不是被作者逐表绑定的reproduction tag；未证实它生成v2全部表格', 'C24 sparse checkout保留训练/评测源码、license和upstream git，排除assets、paper.pdf、SIBR_viewers；GLM只检出头文件/构建元数据等源码', 'C25/C26仅git对象和HDD文本快照，未切换C24训练工作树、未构建或运行', 'version_evidence文本快照经Python text读取可能规范化CRLF；精确上游身份以git tree blob OID为准'],
        'web_metadata_acquisition': read(E / 'web/acquisition.json'), 'data_access_probes': read(E / 'web/data_access_probes.json'),
        'external_source_pins': read(E / 'web/external_source_pins.json'),
        'data_archive_page_probe': read(E / 'web/dtu_archive_access.json'),
        'license_note_simple_knn': 'Pinned upstream simple-knn tree has no standalone LICENSE.md; source headers are retained byte-for-byte, no new license grant inferred.',
        'tool_source_proof': [
            {'method': 'urllib.request.urlopen PDF in memory -> pdftotext -layout - -', 'evidence': 'evidence/paper_v2.txt', 'receipt': 'evidence/web_acquisition.json', 'note': 'web open PDF因20,699,410 bytes太大失败；urllib成功，未把PDF落到root'},
            {'method': 'git clone --filter=blob:none --no-checkout; sparse-checkout; checkout --detach C24; pinned source submodules', 'evidence': 'evidence/clone_verification.json'},
            {'method': 'git show / git ls-tree / git log / restricted core git diff', 'evidence': 'evidence/source_versions.json'},
            {'method': 'bounded os.walk depth4 + explicit data roots depth3/5; no oldrefs traversal', 'evidence': 'evidence/data_discovery.json'},
            {'method': 'python3 -B reproduction/radegs_paper_v01/audit_local_metadata.py', 'evidence': 'evidence/local_metadata.json'},
            {'method': 'nvidia-smi GPU inventory + compute PID; /proc/PID/comm only; compiler versions; importlib.metadata filesystem reads', 'evidence': ['evidence/environment_snapshot.json', 'evidence/python_packages.json']},
            {'method': 'public webpage GET, archive HEAD only, HuggingFace metadata API; no dataset bodies', 'evidence': ['evidence/web/acquisition.json', 'evidence/web/data_access_probes.json', 'evidence/web/tnt_scene_links.json']},
        ],
    }
    write('SOURCE_MANIFEST.json', manifest)
    meta = read(E / 'local_metadata.json')
    scene_records = []
    for n in DTU:
        scene_records.append({'dataset': 'DTU', 'scene': f'scan{n}', 'paper_membership': 'v2 p7 Table1 confirmed', 'training_data_status': 'not_found_in_bounded_search', 'evaluation_gt_status': 'not_found_in_bounded_search', 'verified_local_complete': False})
    for n in TNT:
        scene_records.append({'dataset': 'TNT', 'scene': n, 'paper_membership': 'v2 p7 Table2 confirmed', 'training_data_status': 'raw_images_and_COLMAP_present_but_preprocessing_equivalence_unverified' if n == 'Truck' else 'not_found_in_bounded_search', 'local_evidence_index': 'real_scenes[0]' if n == 'Truck' else None, 'evaluation_gt_status': 'not_found_in_bounded_search', 'verified_local_complete': False})
    for n in OUTDOOR + INDOOR:
        scene_records.append({'dataset': 'Mip-NeRF360', 'scene': n, 'group': 'outdoor' if n in OUTDOOR else 'indoor', 'paper_membership': 'full_dataset_candidate_from_3DGS_full_eval; RaDe_v2_Table3_does_not_enumerate_scenes', 'training_data_status': 'not_found_in_bounded_search', 'verified_local_complete': False})
    for n in SYNTHETIC:
        scene_records.append({'dataset': 'SyntheticNeRF', 'scene': n, 'paper_membership': 'v2 p8 Table4 confirmed', 'training_data_status': '100_frame_train_subset_with_owned_source_symlink' if n in ['hotdog', 'materials', 'mic', 'ship'] else 'not_verified_in_allowed_roots; old_metadata_mentions_owned_cglib_source', 'test_data_status': 'not_present_in_inspected_subset; source_siblings_not_searched', 'verified_local_complete': False})
    inventory = {
        'schema_version': 1, 'audit_utc': now,
        'scope': {'roots': ['/home/u00134/3dgs_line', '/mnt/hdd1/u00134/hybrid_raster_trained_models_v1'], 'initial_max_depth': 4, 'initial_directories_visited': read(E / 'data_discovery.json')['directories_visited'], 'targeted_extensions': ['tier1/data/realcap to image headers and sparse/0 metadata', 'hybrid_raster_trained_models_v1/out/hybrid_raster_trained_models_v1 to depth5 then named training subsets/checkpoint headers', 'transport to depth3: derived native.npz/camera.json/line frames, not dataset RGB', 'explicit train symlinks resolve to /home/u00134/cglib/data/full/{hotdog,materials,mic,ship}/train; only linked train directory inspected'], 'not_searched': ['other users', 'oldrefs', 'whole disks', 'source cglib parent/sibling directories', 'unbounded archives'], 'absence_interpretation': 'not found within documented search, not proof of global machine absence'},
        'scenes': scene_records, 'actual_file_metadata': meta,
        'critical_findings': ['Truck: 251 JPEGs and 251 registered cameras; all names resolve; headers979x546 vs camera1957x1091; source stage/scale and GOF equivalence unverified', 'Truck: sparse point header136029 is COLMAP initialization, not laser ground truth', 'Train301 and DeepBlending playroom225/drjohnson263 are excluded from RaDe v2 quantitative suite', 'hotdog/materials/mic/ship:100 RGBA PNG800x800 each; camera matrices4x4; no test/val JSON in inspected subset; metadata alone does not certify archive completeness', 'Existing vanilla/2DGS PLY/checkpoints and transported native.npz are trained/derived assets, never from-scratch RaDe inputs', 'DTU15, TNT remaining5 and all Mip360 expected9 not found; no inspected dataset qualifies as complete geometry/NVS evaluation package', 'Raw image pixel bodies, large file hashes and archive content verification deferred'],
        'acquisition': {
            'DTU_preprocessed': {'source': 'C24 README#L36 -> 2DGS project -> public Drive', 'url': 'https://drive.google.com/file/d/1ODiOu72tAGPTnhVn0cFZ9MvymDgcoHxQ/view', 'filename': 'dtu.tar.gz', 'folder_display_size': '3.32 GB', 'verified_archive_body': False, 'access': 'folder HTTP200; listing visible; archive download not attempted', 'license': 'DTU official page says freely available and requests citation; inspected 2DGS archive listing has no independently verified archive license'},
            'DTU_GT': {'urls': ['https://roboimagedata2.compute.dtu.dk/data/MVS/Points.zip', 'https://roboimagedata2.compute.dtu.dk/data/MVS/SampleSet.zip'], 'required_layout': ['Calibration/cal18/pos_001.txt ... pos_064.txt', 'ObsMask/ObsMask{scan}_10.mat', 'ObsMask/Plane{scan}.mat', 'Points/stl/stl{scan:03}_total.ply'], 'use': 'evaluation/camera alignment/masking only; no GT geometry in training loss', 'head_content_length_bytes': [6966262016, 6905656531], 'access': 'both HEAD200; bodies not downloaded'},
            'TNT_preprocessed': {'url': 'https://huggingface.co/datasets/ZehaoYu/gaussian-opacity-fields', 'dataset_commit': '0c977df91a2cf3a456ee4e84036893a9fd9979aa', 'filename': 'TNT_GOF.zip', 'size_bytes': 8004621817, 'published_lfs_sha256': '772c034d40c1a1332757a7d2b10b91d56ede3e82930c74537278ca09940928ba', 'access': 'API public=true via private=false; gated=false; no body downloaded', 'provenance': 'C25 README historical pointer; not a C24 TNT recipe', 'license': 'no separate dataset card/license in inspected HF listing; retain original TNT conditions'},
            'TNT_GT': {'url': 'https://www.tanksandtemples.org/download/', 'six_scene_links_evidence': 'evidence/web/tnt_scene_links.json', 'required_per_scene': ['{Scene}.ply', '{Scene}.json', '{Scene}_COLMAP_SfM.log', '{Scene}_trans.txt'], 'predicted_trajectory': 'separate COLMAP_SfM.log matching preprocessed input order and coordinates', 'access': 'public page with Drive links; did not test each GT archive download or bypass any access barrier', 'license': 'current license page simultaneously states CC BY4.0 and a restrictive noncommercial/no-third-party grant; preserve this ambiguity, do not infer unrestricted redistribution', 'use': 'evaluation alignment/refinement/crop/scoring only'},
            'MipNeRF360': {'page': 'https://jonbarron.info/mipnerf360/', 'urls': ['https://storage.googleapis.com/gresearch/refraw360/360_v2.zip', 'https://storage.googleapis.com/gresearch/refraw360/360_extra_scenes.zip'], 'head_content_length_bytes': [12535427936, 4488140217], 'access': 'HEAD200 both; archive bodies and exact per-scene counts not inspected', 'license': 'dataset archive license not verified; MultiNeRF code Apache2.0 is not automatically a data license'},
            'SyntheticNeRF': {'url': 'https://drive.google.com/drive/folders/1cK3UDIJqKAAm7zyrxRYVFJ0BRMgrwhh4', 'filename': 'nerf_synthetic.zip', 'access': 'folder200 and archive name visible; no dataset download', 'schema': ['transforms_train.json', 'transforms_val.json', 'transforms_test.json', 'train/*.png', 'val/*.png', 'test/*.png'], 'license': 'bmild/nerf code MIT preserved as source evidence; rendered asset/archive licenses not verified; do not transfer code MIT to all data'},
        },
    }
    write('DATA_INVENTORY.json', inventory)
    disputes = [
        {'id': 'D1', 'topic': 'normal weight', 'paper_text': 5, 'C24_default': 0.05, 'recommendation': 'paper_text_weights_on_C24 and official_default_C24 separate immutable result namespaces; neither is author-result provenance', 'requires_user_resolution': True},
        {'id': 'D2', 'topic': 'Eq23 vs code', 'paper': 'sum over i,j of detached wi*wj*(di-dj)^2', 'C24': 'sum j<i of wi*wj*(h(di)-h(dj))^2 / stopgrad(M^2), multiplied by RGB-edge exp(-max_grad); distortion weight gradients suppressed in custom CUDA', 'recommendation': 'preserve C24 unchanged; paper-text weight branch still uses C24 loss; literal-equation port would be a separate approved implementation, not silent correction', 'requires_user_resolution': True},
        {'id': 'D3', 'topic': 'complete paper pipeline absent in C24', 'missing': ['TNT recipe/evaluator', 'tetrahedra extraction entry', 'NVS render/metric entry'], 'recommendation': 'future source-only backport design with explicit source commits/interface review, or author clarification; do not switch to C25/C26 training', 'requires_user_resolution': True},
        {'id': 'D4', 'topic': '20k and NVS protocol not fully specified', 'unknowns': ['20k stage boundary/learning-rate schedule vs 30k snapshot', 'exact Table3 scene subset/resolution and image lists', 'Synthetic background and final test protocol used by author', 'Table2 TNT exact resolution/split and tetrahedra settings'], 'recommendation': 'preregister candidate conventions separately from paper-proven facts; retain all target tables', 'requires_user_resolution': True},
    ]
    def command(argv, provenance, executed=False):
        return {'argv_template': argv, 'provenance': provenance, 'executed': executed, 'runnable_now': False}
    train = ['<isolated_python>', 'train.py', '-s', '<HDD_DATA>/DTU/scan24', '-m', '<HDD_RUNS>/<variant>/dtu_half30k/scan24', '-r', '2', '--use_decoupled_appearance', '--iterations', '30000', '--lambda_distortion', '100', '--lambda_depth_normal', '<0.05_or_5_after_user_decision>']
    protocol = {
        'schema_version': 1, 'created_utc': now, 'state': 'DRAFT_NOT_AUTHORIZED_FOR_EXECUTION', 'current_authorized_stage': 1, 'automatic_advance': False, 'source_pin': SHA['C24'], 'source_path': str(REPO), 'external_root': str(HDD),
        'nonnegotiable_gates': ['Every future stage requires subsequent user instruction; no scheduler/cron or background wait-for-GPU', 'GPU work only after fresh device/process snapshot proves exclusive idle ownership; spare VRAM or zero utilization is insufficient', 'Do not mutate original models/data/old lift/worktrees/global env; isolate data/env/cache/runs under HDD root', 'Geometry GT and heldout RGB only evaluation; no GT depth/normal loss added', 'Fresh initialization from verified COLMAP or synthetic random initializer; never existing vanilla Lego/Chair or other pretrained PLY'],
        'pending_user_decisions': disputes,
        'variants': [{'id': 'official_default_C24', 'lambda_distortion': 100, 'lambda_depth_normal': 0.05, 'implementation': 'untouched C24', 'author_table_equivalence': 'unproven'}, {'id': 'paper_text_weights_on_C24', 'lambda_distortion': 100, 'lambda_depth_normal': 5, 'implementation': 'untouched C24 with explicit CLI override only', 'author_table_equivalence': 'unproven; Eq23/24 implementation differences remain'}],
        'suite': {
            'DTU': {'scenes': [f'scan{n}' for n in DTU], 'table': 1, 'variants': ['half_resolution_20k', 'half_resolution_30k', 'full_resolution_30k'], 'resolution': 'native1600x1200 -> -r2=800x600; -r1 full; verify actual preprocessed archive first', 'split': 'C24 README no --eval => all sorted cameras training', 'initialization': 'preprocessed COLMAP sparse/0, not GT STL', 'appearance': 'C24 boolean --use_decoupled_appearance', 'metrics': {'CD': 'mm, (mean_d2s+mean_s2d)/2 after official masks/plane/alignment'}, 'mesh': 'TSDF + marching cubes; median depth, mask and alpha0.5, voxel0.002 internal scene units'},
            'TNT': {'scenes': TNT, 'table': 2, 'training_iterations': 30000, 'mesh_variants': ['TSDF_marching_cubes', 'marching_tetrahedra_sharp_symbol'], 'split_resolution': 'v2 not explicit; C25 recipe -r2 --eval is historical and not proof for v2', 'initialization': 'COLMAP using dataset poses', 'appearance': True, 'metrics': {'F1': 'dimensionless fraction [0,1], macro mean over6; never silently percentage'}, 'evaluator_thresholds_in_GT_coordinate_units': {'Barn': 0.01, 'Caterpillar': 0.005, 'Courthouse': 0.025, 'Ignatius': 0.003, 'Meetingroom': 0.01, 'Truck': 0.005}, 'C24_support': 'incomplete'},
            'MipNeRF360': {'outdoor': OUTDOOR, 'indoor': INDOOR, 'table': 3, 'membership_certainty': 'target full9 standard suite; author Table3 exact list not provided', 'proposed_resolution': 'images_4 outdoors, images_2 indoors, -r1 to avoid second resize; source3DGS full_eval only, not RaDe author-proven', 'split': 'C24 sorted image_name index%8==0 test when --eval; persist exact name lists', 'initialization': 'COLMAP sparse', 'appearance': False, 'metrics': {'PSNR': 'dB', 'SSIM': 'dimensionless', 'LPIPS': 'dimensionless; C25 metric uses VGG; C24 evaluation entry missing'}, 'aggregation': 'per-scene test-image averages then separate outdoor/indoor scene averages', 'C24_support': 'loader/train present; NVS executable chain missing'},
            'SyntheticNeRF': {'scenes': SYNTHETIC, 'table': 4, 'resolution': 'candidate full800x800 -r1; archive verification pending', 'split': 'separate transforms_train/test; C24 does not merge test even if eval=False; val not used by C24 loader', 'initialization': 'C24 100000 random points in [-1.3,1.3]^3 if points3d.ply absent; freeze source of any existing cached initialization', 'appearance': False, 'background': 'C24 default black; white -w is common synthetic convention, author Table4 exact choice not established', 'metrics': {'PSNR': 'dB, per-scene and arithmetic mean over8'}, 'regularization': 'v2 Table4 explicitly trains ours with regularization', 'C24_support': 'loader/train present; NVS executable chain missing'},
            'excluded_extensions': ['Objaverse GT depth/normal quantitative evaluation', 'PGSR multi-view losses/appearance3', 'Train and DeepBlending scenes', 'new 2026 formulations as substitutes for v2'],
        },
        'paper_to_code_data_command_eval': [
            {'paper': 'p6 Eq23-25 / p7 Table1', 'code': ['C24_defaults', 'C24_loss', 'C24_mesh', 'C24_eval_alignment', 'C24_eval_metric'], 'data': 'DTU preprocessed images+COLMAP+alpha; separate official GT/calibration/ObsMask', 'commands': ['train.py -s <DTU/scanN> -m <OUT> -r 2 --use_decoupled_appearance', 'mesh_extract.py -s <DTU/scanN> -m <OUT> -r 2', 'evaluate_dtu_mesh.py -s <DTU/scanN> -m <OUT> --DTU <GT> --iteration <K>'], 'evaluation': 'vis/results.json; CD mm, all15; parameter variant recorded', 'status': 'documented_official_chain_unexecuted_data_env_missing'},
            {'paper': 'p7 Table2 Our / Our#', 'code': ['C24_depth_normal_output', 'C25_tnt_evaluator', 'C25_tnt_thresholds'], 'data': '6 GOF-preprocessed scenes plus separate official GT/poses/align/crop', 'commands': ['historical only: C25 train.py ... -r2 --eval --use_decoupled_appearance', 'historical only: C25 mesh_extract_tetrahedra.py ...', 'eval_tnt/run.py --dataset-dir <GT/Scene> --traj-path <input_COLMAP_SfM.log> --ply-path <recon.ply> --out-dir <eval>'], 'evaluation': 'P/R/F1 at per-scene tau, official-coordinate registration/crop; TSDF vs tetra columns distinct', 'status': 'C24_missing_pipeline; C25_not_author_equivalent'},
            {'paper': 'p7 Table3 / p8 Table4 / p3 Fig2', 'code': ['C24_colmap_split_init', 'C24_synthetic_split_init', 'C24_depth_normal_output', 'C25_nvs_metrics'], 'data': 'Mip3609-candidate and Synthetic8 with untouched heldout splits', 'commands': ['C24 train.py -s <scene> -m <out> --eval <verified_resolution/background>', 'future reviewed C24-compatible render/eval wrapper required; C25 actual script metric.py, not README metrics.py'], 'evaluation': 'RGB metrics and RGB/depth/normal qualitative artifacts; no new Objaverse GT scores', 'status': 'C24_loader_exists; complete_export_eval_not_yet_implemented'},
        ],
        'stages': [
            {'id': 1, 'input': 'v2 PDF, official git, existing owned metadata, read-only hardware', 'commands': ['source/history/metadata audit only; see SOURCE_MANIFEST.tool_source_proof'], 'expected_artifacts': ['STAGE1_AUDIT_ZH.md', 'SOURCE_MANIFEST.json', 'DATA_INVENTORY.json', 'REPRODUCTION_PROTOCOL_DRAFT.json', 'STATUS.json'], 'gate': 'JSON parses, new authored files whitespace-clean, links resolve, clean C24 HEAD/gitlinks; no scientific result claims', 'status': 'audit_written_pending_final_validation'},
            {'id': 2, 'input': 'user next instruction and decisions D1-D4; public data URLs/licenses; static environment evidence', 'commands': [command(['conda', 'create', '--prefix', '<HDD>/envs/c24_py39', 'python=3.9'], 'C24 README python3.9; not run'), command(['<HDD>/envs/c24_py39/bin/python', '-m', 'pip', 'install', '<reviewed_pinned_requirements>'], 'pending dependency lock; source README unpinned')], 'acquisition_command_status': 'No fake archive download command: first resolve official Drive file endpoint/checksum, approve exact download list and HDD destinations. HEAD/API evidence already provided.', 'expected_artifacts': ['approved variant plan', 'locked environment/compiler specification', 'data manifest with all scene files/dimensions/split hashes/license notices', 'separate eval GT tree'], 'gate': 'no missing images/calibration/masks/GT; data equivalence proven before training; any schema repair separately reviewable', 'status': 'awaiting_user'},
            {'id': 3, 'input': 'isolated environment+complete scan24 input and C24 source; separately approved missing-pipeline plan', 'commands': [command(['<isolated_python>', '-m', 'pip', 'install', 'submodules/diff-gaussian-rasterization', 'submodules/simple-knn/'], 'C24 README; build only in later approved isolated env'), command(['<isolated_python>', '<future_reviewed_smoke_script>'], 'not implemented; no smoke or numerical check performed in stage1')], 'expected_artifacts': ['build log and .so provenance/ABI', 'approved exporter/evaluator bridge patch with SHA sources', 'smoke outputs and finite-value/gradient checks'], 'gate': 'exclusive GPU required before imports/workload that touch CUDA; correct native module path, no shared-binary reuse, no GT leakage', 'status': 'blocked_until_user_and_prerequisites'},
            {'id': 4, 'input': 'verified scan24 and selected explicitly named variant(s); fresh initialization', 'commands': [command(train, 'C24 README train recipe + explicit audit variant parameters')], 'expected_artifacts': ['exact argv/cfg/source/data/env manifest', 'initialization and split record', 'training log/iteration7000,30000 PLY/chkpnt15000', 'raw expected_depth, median_depth, alpha, normals and RGB via approved exporter'], 'gate': 'source clean or separately approved bridge patch; no resume from vanilla; validate losses/regularization/densification start and actual iteration counts; measured timing only on exclusive GPU', 'status': 'not_started'},
            {'id': 5, 'input': 'scan24 trained C24 output and separate evaluation GT', 'commands': [command(['<isolated_python>', 'mesh_extract.py', '-s', '<HDD_DATA>/DTU/scan24', '-m', '<SCAN24_OUT>', '-r', '2'], 'C24 README'), command(['<isolated_python>', 'evaluate_dtu_mesh.py', '-s', '<HDD_DATA>/DTU/scan24', '-m', '<SCAN24_OUT>', '--DTU', '<HDD_EVAL_GT>/DTU', '--iteration', '30000'], 'C24 README and actual evaluator CLI')], 'expected_artifacts': ['recon.ply', 'recon_culled.ply', 'recon_aligned.ply', 'vis/results.json', 'raw depth/normal/alpha exports with coordinate metadata'], 'gate': 'nonempty valid meshes; exact official calibration and mask; GT confined to evaluation; evaluation subprocess/output checked independently because os.system return is ignored', 'status': 'not_started'},
            {'id': 6, 'input': 'validated pilot, approved complete scene/split roster, resolved TNT/NVS/tetra gaps', 'commands': ['expand approved stage4/5 commands over DTU15 including half/full and20k schedule once fixed', 'TNT6: approved TSDF/tetra extraction and pinned eval_tnt chain', 'Mip360 and Synthetic: approved C24-compatible heldout renderer + metric.py lineage'], 'expected_artifacts': ['per-scene results/splits/manifests', 'Table1-4 comparisons separating author-published numbers and local measurements', 'RGB/depth/normal/mesh qualitative comparisons'], 'gate': 'all required scenes and variants present; no extension mixing or cherry-picking; no H800/A6000 runtime-equivalence claim', 'status': 'not_started'},
        ],
        'static_hazards': ['mesh_extract.py --checkpoint_iterations has nargs=+ but code uses value as scalar path; default latest works; do not advertise explicit20k extraction flag as validated', 'C24 regularization condition >=15000 means14999 purely photometric iterations in1-based loop; final optimizer step skipped; preserve before any user-approved interpretation', 'C24 loaders create points3D.ply/points3d.ply on first use: future data working copy under HDD is required, never write old readonly archives', 'C24 evaluate_dtu_mesh imports CUDA code and performs CUDA culling; evaluation is also GPU work', 'C24 model load expects filter_3D PLY field; vanilla/2DGS checkpoint not a substitute', 'C25 metric.py catches exceptions; require result files/per-view counts, not exit code alone'],
        'environment_plan': {'prefix': '<HDD>/envs/c24_py39', 'baseline': 'C24 README Python3.9 and cu121; historical torch package version unspecified', 'candidate_not_author_lock': {'python': '3.9', 'torch': '2.3.1+cu121', 'torchvision': '0.18.1+cu121'}, 'host_toolchain': 'gcc/g++13.3; CUDA toolkit12.6.85; no compiler/toolkit compatibility build performed', 'open_questions': ['isolate compatible CUDA toolkit/compiler; do not replace system', 'pin transitive dependencies including scipy/sklearn/matplotlib/Pillow/Open3D missing or unpinned in upstream requirements', 'pin LPIPS VGG weights for later NVS evaluator without auto downloads', 'C24 extension module names collide with existing vanilla installs; always build and verify isolated .so provenance'], 'future_cache_roots': ['<HDD>/cache/pip', '<HDD>/cache/conda', '<HDD>/cache/torch_extensions', '<HDD>/tmp'], 'modified_existing_envs': False},
        'budget': {'label': 'engineering_estimates_not_measurements_of_training', 'download_observations_bytes': {'DTU_points': 6966262016, 'DTU_sample': 6905656531, 'TNT_GOF': 8004621817, 'Mip360_part1': 12535427936, 'Mip360_part2': 4488140217}, 'download_source': 'evidence/web/data_access_probes.json plus HF LFS metadata; no archive body fetched', 'HDD_provisional_reservation_GiB': [250, 500], 'reservation_basis': 'known compressed archives plus DTU/Synthetic/GT downloads, unpacked copies, isolated envs, multiple checkpoints and mesh/export buffers; revise after actual manifests', 'minimum_target_scene_count_if_Mip9': 38, 'training_run_estimate_per_parameter_variant': 68, 'run_estimate_assumptions': '38 main30k +15 DTU full30k +15 independent20k; 20k schedule unresolved; tetra reuses TNT train models;2 variants =>136 runs if all independent', 'A6000_training_time_estimate': None, 'reason_no_time_estimate': 'no permitted pilot and no hardware-calibrated throughput; H800 paper times are comparison references only', 'published_H800_times_minutes': {'DTU_half20k': 5.0, 'DTU_half30k': 8.3, 'DTU_full': 20.2, 'TNT30k': 11.5}, 'published_source': references['paper_tables_1_2_3'], 'TSDF_attribute_capacity_estimate_bytes': 1638400000, 'TSDF_estimate_basis': 'C24 mesh_extract.py:50000 blocks *16^3 voxels *2 float32 attrs; payload capacity only, excludes Open3D/hash/mesh/depth/color memory and is not measured peak'},
        'references': references,
    }
    write('REPRODUCTION_PROTOCOL_DRAFT.json', protocol)
    write('STATUS.json', {'schema_version': 1, 'updated_utc': now, 'stage': 1, 'stage1completed': False, 'status': 'audit_written_pending_document_validation', 'stage1_blocked_reasons': [], 'next_stage_blocked_reasons': ['awaiting_user_instruction', 'paper_code_parameter_and_loss_disagreements_D1_D2', 'C24_full_pipeline_gaps_D3', 'scene_resolution_split_20k_uncertainties_D4', 'complete_dataset_GT_not_acquired_verified', 'isolated_environment_not_built', 'both_GPUs_have_existing_jobs_require_future_exclusive_idle_recheck'], 'nextstep': 'awaitinguser', 'nextstepawaitinguser': True, 'scientificdone': False, 'training_started': False, 'gpu_workload_started': False, 'numeric_experiments_run': False, 'packages_installed': False, 'large_datasets_downloaded': False, 'scheduler_created': False, 'agents_delegated': False, 'commit_created': False, 'push_performed': False, 'clone_head': SHA['C24'], 'clone_path': str(REPO), 'validation': 'pending', 'launch_header_is_not_completion_evidence': True})
    print('Wrote SOURCE_MANIFEST, DATA_INVENTORY, REPRODUCTION_PROTOCOL_DRAFT, provisional STATUS')


if __name__ == '__main__':
    main()
