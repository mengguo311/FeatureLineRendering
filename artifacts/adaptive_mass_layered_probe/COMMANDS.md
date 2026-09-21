# Exact execution and TDD commands

Commands ran in /home/u00134/3dgs_line/tier1 through record_command.py. Each entry contains the exact child argv, environment, source hashes, timestamps and protocol hash in TDD.jsonl. Concurrent jobs append on completion, so this index is sorted by allocated sequence. RED means a nonzero child exit was required; failed fixture/harness attempts are retained and explained in the report.

Environment: PYTHONPATH=.:tests; PYTHONDONTWRITEBYTECODE=1; OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1; OMP_WAIT_POLICY=PASSIVE; CUDA_VISIBLE_DEVICES=1.

## 000 RED csr_prefix (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_csr_shortest_native_mass_prefix_ties_and_residual
```

Command SHA256: `0d0b03bd2e2db8ba29aaabdb1d6d1ef4882c9a6877a69d499d693a91e3aa284d`
Log SHA256: `f3af51ecee76a3aae25417e6c1652fb98f87ef398cc75ed4dd16d00e845c2486`
Log: [000_RED_csr_prefix.log](logs/000_RED_csr_prefix.log)
UTC: 2026-09-21T11:22:41.179999+00:00 to 2026-09-21T11:22:41.372835+00:00

## 001 GREEN csr_prefix (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_csr_shortest_native_mass_prefix_ties_and_residual
```

Command SHA256: `0d0b03bd2e2db8ba29aaabdb1d6d1ef4882c9a6877a69d499d693a91e3aa284d`
Log SHA256: `430a5f95388720307ab95186f21d06de248942080c673792aca22f4dd52a1737`
Log: [001_GREEN_csr_prefix.log](logs/001_GREEN_csr_prefix.log)
UTC: 2026-09-21T11:23:25.971859+00:00 to 2026-09-21T11:23:26.557893+00:00

## 002 RED csr_validation (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_reject_bad_target_and_native_transmittance_before_ffi
```

Command SHA256: `8e45468a5b4d255e78a5b30be5860fd766262cf9e08d20daa08db9bea6656653`
Log SHA256: `a5ce2cb13efdeb37c58efed65e7aead095dbe4b555d6e54bfdc5dc9950fde6e1`
Log: [002_RED_csr_validation.log](logs/002_RED_csr_validation.log)
UTC: 2026-09-21T11:23:41.968886+00:00 to 2026-09-21T11:23:42.155905+00:00

## 003 GREEN csr_validation (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_reject_bad_target_and_native_transmittance_before_ffi
```

Command SHA256: `8e45468a5b4d255e78a5b30be5860fd766262cf9e08d20daa08db9bea6656653`
Log SHA256: `24cefc2bc38a1c71e18591075993695fc72546b32ff6b5baab3d98032ce96fb5`
Log: [003_GREEN_csr_validation.log](logs/003_GREEN_csr_validation.log)
UTC: 2026-09-21T11:24:11.087034+00:00 to 2026-09-21T11:24:11.285232+00:00

## 004 RED csr_metrics (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_csr_metrics_gate_and_semantics_detect_corruption
```

Command SHA256: `ab164dc4fdf80bcd1388a09c0771f30336f39169b75319719bd25c3352d737e1`
Log SHA256: `f11161f17cc223c89d1562e0f104bd9e37c2765200192b84182fce353b94bcd9`
Log: [004_RED_csr_metrics.log](logs/004_RED_csr_metrics.log)
UTC: 2026-09-21T11:24:11.385548+00:00 to 2026-09-21T11:24:11.584507+00:00

## 005 GREEN csr_metrics (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_csr_metrics_gate_and_semantics_detect_corruption
```

Command SHA256: `ab164dc4fdf80bcd1388a09c0771f30336f39169b75319719bd25c3352d737e1`
Log SHA256: `a75d5a91a411eeced9e6131248a85982b358c592dc17ed1f73ccacc7565157fc`
Log: [005_GREEN_csr_metrics.log](logs/005_GREEN_csr_metrics.log)
UTC: 2026-09-21T11:25:05.891483+00:00 to 2026-09-21T11:25:06.084287+00:00

## 006 RED gpu_calibration (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_gpu_calibration_full_K_ties_and_native_prefix
```

Command SHA256: `56dc3c83f633ad0fa721a3f2368d68ad7840cfa2ad239dbeebbfab10b832f62c`
Log SHA256: `b551e0afe9136671d47ca073f2ef881d176844239926931907205760b9c4d39e`
Log: [006_RED_gpu_calibration.log](logs/006_RED_gpu_calibration.log)
UTC: 2026-09-21T11:25:30.614552+00:00 to 2026-09-21T11:25:30.808140+00:00

## 007 GREEN gpu_calibration (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_gpu_calibration_full_K_ties_and_native_prefix
```

Command SHA256: `56dc3c83f633ad0fa721a3f2368d68ad7840cfa2ad239dbeebbfab10b832f62c`
Log SHA256: `535089f60a01e7c795f0658943135f64a59f8c77d6e07ff36c37c1d281bc3c81`
Log: [007_GREEN_gpu_calibration.log](logs/007_GREEN_gpu_calibration.log)
UTC: 2026-09-21T11:25:59.094217+00:00 to 2026-09-21T11:26:02.544617+00:00

## 008 RED common_gate (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_smallest_common_cap_and_fail_closed_gate
```

Command SHA256: `35dafd9ff38806cb6bfbfd7de8f184e244ca175aad292386bbf1b7f83b16f650`
Log SHA256: `c22e8906028f8e4781654575b64114f965a9a749d0481bb0623c3649cec50c13`
Log: [008_RED_common_gate.log](logs/008_RED_common_gate.log)
UTC: 2026-09-21T11:26:27.724231+00:00 to 2026-09-21T11:26:27.943299+00:00

## 009 GREEN common_gate (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_smallest_common_cap_and_fail_closed_gate
```

Command SHA256: `35dafd9ff38806cb6bfbfd7de8f184e244ca175aad292386bbf1b7f83b16f650`
Log SHA256: `50123f26e6d30940556cc448291d77c1880d497121f6c91559a6a7bdb8620941`
Log: [009_GREEN_common_gate.log](logs/009_GREEN_common_gate.log)
UTC: 2026-09-21T11:26:28.030651+00:00 to 2026-09-21T11:26:28.272291+00:00

## 010 RED artifacts (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_complete_artifacts_retain_csr_and_decode_deterministically
```

Command SHA256: `481d2aba2ebdcbedc3bad4f3f839fb3b6d9fd48820ed070ae007dd0563eaa922`
Log SHA256: `373d1e400991fbbc13a1d13ecab7fde4098adff35213a7027f01c5d1a799995e`
Log: [010_RED_artifacts.log](logs/010_RED_artifacts.log)
UTC: 2026-09-21T11:27:04.434265+00:00 to 2026-09-21T11:27:04.662621+00:00

## 011 GREEN artifacts (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_complete_artifacts_retain_csr_and_decode_deterministically
```

Command SHA256: `481d2aba2ebdcbedc3bad4f3f839fb3b6d9fd48820ed070ae007dd0563eaa922`
Log SHA256: `dcf1d0e1b6f1bd4e1e6bf6d7c30afbf0b05fed230a6123c3d13ef50ae7e6b288`
Log: [011_GREEN_artifacts.log](logs/011_GREEN_artifacts.log)
UTC: 2026-09-21T11:27:46.085583+00:00 to 2026-09-21T11:27:49.269519+00:00

## 012 RED cli (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_cli_requires_explicit_fresh_output
```

Command SHA256: `5b53f1c59c23e8f76e020f8cecb5ddc738357d66c3ff6961567e7d32c4b4dc1e`
Log SHA256: `74a7d923e9f57fb59546eef273b18eed52a28e390265299c5634171417a8efe6`
Log: [012_RED_cli.log](logs/012_RED_cli.log)
UTC: 2026-09-21T11:28:30.010397+00:00 to 2026-09-21T11:28:30.421608+00:00

## 013 GREEN cli (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass.AdaptiveTests.test_cli_requires_explicit_fresh_output
```

Command SHA256: `5b53f1c59c23e8f76e020f8cecb5ddc738357d66c3ff6961567e7d32c4b4dc1e`
Log SHA256: `6332a739fe9dffedf5bc96f7329d10b5983ef25b606b5dc6bf25907f131c47a9`
Log: [013_GREEN_cli.log](logs/013_GREEN_cli.log)
UTC: 2026-09-21T11:28:30.548716+00:00 to 2026-09-21T11:28:31.208265+00:00

## 014 CHECK targeted (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass test_topk_layered_evidence test_topk_layered_verification
```

Command SHA256: `23d019e1bc255c3aea6efe427d943787f2c93e61dae4fea6995b8249575d9741`
Log SHA256: `6e2d20f124bf80d6986d7cce6f52180cacfdce79be436cc35bc181794cdffe31`
Log: [014_CHECK_targeted.log](logs/014_CHECK_targeted.log)
UTC: 2026-09-21T11:28:37.262370+00:00 to 2026-09-21T11:28:46.151578+00:00

## 015 CHECK compile_native (exit 0)

```bash
g++ -O3 -std=c++17 -shared -fPIC -fopenmp src/adaptive_mass_native.cpp -o out/adaptive_mass_layered_probe/setup/adaptive_mass_native.so
```

Command SHA256: `4489f117f9cb0165825cd3d5e5aa8d4b5928dcb512e0c5508fe82987060ac4d2`
Log SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
Log: [015_CHECK_compile_native.log](logs/015_CHECK_compile_native.log)
UTC: 2026-09-21T11:28:46.236460+00:00 to 2026-09-21T11:28:46.566061+00:00

## 016 RUN g0_run (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/run.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache scripts/render_adaptive_mass_probe.py --output out/adaptive_mass_layered_probe/run
```

Command SHA256: `e62710d52bce6b2ab63324400871004ff924f23a69562eaa57b783bf018fd7b5`
Log SHA256: `6befdcb2aa6e01d9eef76074fcda0cef789c728065aaa76baa53c6d23f190c9b`
Log: [016_RUN_g0_run.log](logs/016_RUN_g0_run.log)
UTC: 2026-09-21T11:28:53.022387+00:00 to 2026-09-21T11:37:33.102750+00:00

## 017 RED saved_semantics (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_verification.AdaptiveVerificationTests.test_saved_csr_semantics_detect_tail_and_diagnostic_corruption
```

Command SHA256: `973f66dd6fd65653f4b4c26bd72be74e8455b96a09eb7e218ef471a129707541`
Log SHA256: `df416fb4794b761d780c67a1e746350e0cc4b0752659a4739d97293d33c0ee82`
Log: [017_RED_saved_semantics.log](logs/017_RED_saved_semantics.log)
UTC: 2026-09-21T11:29:56.780563+00:00 to 2026-09-21T11:29:56.985258+00:00

## 018 GREEN saved_semantics (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_verification.AdaptiveVerificationTests.test_saved_csr_semantics_detect_tail_and_diagnostic_corruption
```

Command SHA256: `973f66dd6fd65653f4b4c26bd72be74e8455b96a09eb7e218ef471a129707541`
Log SHA256: `25731833f9409651c24426b70de0f6929e729bd36ae02e81a30e9ce0a804794f`
Log: [018_GREEN_saved_semantics.log](logs/018_GREEN_saved_semantics.log)
UTC: 2026-09-21T11:29:57.074275+00:00 to 2026-09-21T11:29:57.343764+00:00

## 019 RED comparison (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_verification.AdaptiveVerificationTests.test_comparison_requires_equal_inventory_bytes_and_png_decode
```

Command SHA256: `06bf5560e69ea5b6fd11a97b8322af7e6920f633607176c219c4796d02df6f32`
Log SHA256: `e3dc8344db4efea0314b45b5d98b6e8bfd59f320ae173edf0e60752c1bd1b037`
Log: [019_RED_comparison.log](logs/019_RED_comparison.log)
UTC: 2026-09-21T11:30:33.078731+00:00 to 2026-09-21T11:30:33.286484+00:00

## 020 GREEN comparison (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_verification.AdaptiveVerificationTests.test_comparison_requires_equal_inventory_bytes_and_png_decode
```

Command SHA256: `06bf5560e69ea5b6fd11a97b8322af7e6920f633607176c219c4796d02df6f32`
Log SHA256: `439b00f50e409b8ea6ff578f1c945904d9aa00f5e4759fcb4e71d9f1615c4084`
Log: [020_GREEN_comparison.log](logs/020_GREEN_comparison.log)
UTC: 2026-09-21T11:30:59.791740+00:00 to 2026-09-21T11:30:59.978038+00:00

## 021 RED verifier_cli (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_verification.AdaptiveVerificationTests.test_verifier_cli_exposes_isolated_root
```

Command SHA256: `70fe459a53b1f24ab567f86d37ed00dbe93d13f8a014c5aa75bd1dd0b5d303ec`
Log SHA256: `2bc8aa3e722837a0213c3e73e6e7b774a0b407657facecc3baa3feac1bef4ee6`
Log: [021_RED_verifier_cli.log](logs/021_RED_verifier_cli.log)
UTC: 2026-09-21T11:31:17.912860+00:00 to 2026-09-21T11:31:17.968311+00:00

## 022 RED verifier_cli (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_verification.AdaptiveVerificationTests.test_verifier_cli_exposes_isolated_root
```

Command SHA256: `70fe459a53b1f24ab567f86d37ed00dbe93d13f8a014c5aa75bd1dd0b5d303ec`
Log SHA256: `a16a26af0c3e0c0e2850eb7f570ab8c20238828386f46f8803d43932491f2185`
Log: [022_RED_verifier_cli.log](logs/022_RED_verifier_cli.log)
UTC: 2026-09-21T11:31:33.730569+00:00 to 2026-09-21T11:31:34.023242+00:00

## 023 GREEN verifier_cli (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_verification.AdaptiveVerificationTests.test_verifier_cli_exposes_isolated_root
```

Command SHA256: `70fe459a53b1f24ab567f86d37ed00dbe93d13f8a014c5aa75bd1dd0b5d303ec`
Log SHA256: `c3225ddfde34e105f30ecab99c3fa9e9c4702c24725636c2ec9827e8bc397d11`
Log: [023_GREEN_verifier_cli.log](logs/023_GREEN_verifier_cli.log)
UTC: 2026-09-21T11:32:30.626302+00:00 to 2026-09-21T11:32:30.934827+00:00

## 024 CHECK verification_unit (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_verification
```

Command SHA256: `b7d6425f4e9c8439ebaf343f80b83c8e5ec1ab6d353d1b8aa559a891e17dad65`
Log SHA256: `a7ff967ec9363100f0e7454ec68a9ed35378e0845d26666e7a6ba81d9314a5fd`
Log: [024_CHECK_verification_unit.log](logs/024_CHECK_verification_unit.log)
UTC: 2026-09-21T11:34:18.792554+00:00 to 2026-09-21T11:34:19.160856+00:00

## 025 CHECK saved_preflight (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -c 'from pathlib import Path; from scripts.verify_adaptive_mass_probe import verify_npz; p=Path("out/adaptive_mass_layered_probe/run/lego_90_128.npz"); r=verify_npz(p,.9,128); print(r["checks"]); assert r["passed"]'
```

Command SHA256: `cf085a66735ddb3043e4147ea29c142df1be84bdd5282d0981e718670d53f45b`
Log SHA256: `39d01adc75fefc74fd5dafa87ef98523f6c64cc0b94e0689d258c054f63addbb`
Log: [025_CHECK_saved_preflight.log](logs/025_CHECK_saved_preflight.log)
UTC: 2026-09-21T11:34:34.196871+00:00 to 2026-09-21T11:34:37.056398+00:00

## 026 CHECK full_suite_g0 (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/full_suite_g0.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache -m unittest discover -s tests -v
```

Command SHA256: `c67193a24d7754e39c1b3fbec0a8b8e97124625b0ac72ec3adabe0c4bc4ebe93`
Log SHA256: `2b37a2b6db14b442b92c3406de2a2d97521bada98978eaa441e2c76f44f418fe`
Log: [026_CHECK_full_suite_g0.log](logs/026_CHECK_full_suite_g0.log)
UTC: 2026-09-21T11:37:58.789103+00:00 to 2026-09-21T11:38:50.512483+00:00

## 027 RED layer_compression (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layers.LayerTests.test_relative_gap_layers_conserve_provenance_and_overflow
```

Command SHA256: `3748acf2a04d4955e267dca865b9df88b83f188182357e954c4a2f681540ffe3`
Log SHA256: `45230b54db6b4119dcfc6820dbf497fe406bb46a0074f2e8c767a1ca619feaf9`
Log: [027_RED_layer_compression.log](logs/027_RED_layer_compression.log)
UTC: 2026-09-21T11:38:25.958248+00:00 to 2026-09-21T11:38:26.076826+00:00

## 028 GREEN layer_compression (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layers.LayerTests.test_relative_gap_layers_conserve_provenance_and_overflow
```

Command SHA256: `3748acf2a04d4955e267dca865b9df88b83f188182357e954c4a2f681540ffe3`
Log SHA256: `a41e08b8782ccff561fc04da1c4aa92b79d00989913c15ae6639e0c2e9b7e03c`
Log: [028_GREEN_layer_compression.log](logs/028_GREEN_layer_compression.log)
UTC: 2026-09-21T11:38:57.618935+00:00 to 2026-09-21T11:38:57.782531+00:00

## 029 RED distribution_pairs (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_exact_weighted_depth_transport_and_ID_overlap
```

Command SHA256: `cde20632227d0d57e5861c3daf36213b347d8ac120e4e8966afddf8b84cb0cdf`
Log SHA256: `d2b5313906a0a46752eca1d37caf95bd5dd12386fca35d0f862577845a0a807c`
Log: [029_RED_distribution_pairs.log](logs/029_RED_distribution_pairs.log)
UTC: 2026-09-21T11:41:04.600921+00:00 to 2026-09-21T11:41:04.757216+00:00

## 030 GREEN distribution_pairs (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_exact_weighted_depth_transport_and_ID_overlap
```

Command SHA256: `cde20632227d0d57e5861c3daf36213b347d8ac120e4e8966afddf8b84cb0cdf`
Log SHA256: `80d9ec7a27b37409140d7ffb329282e172813cd9db229a586efbf7309a8dbdfb`
Log: [030_GREEN_distribution_pairs.log](logs/030_GREEN_distribution_pairs.log)
UTC: 2026-09-21T11:41:56.476859+00:00 to 2026-09-21T11:41:57.312743+00:00

## 031 RED matched_hessian (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_matched_layer_hessian_never_averages_front_and_back
```

Command SHA256: `2fb973a4415db1a8ca493925898f49d5e3761337112ca5414200f690104e4c4a`
Log SHA256: `8050989b1e11317d1b440cf46372519a5c16334774a0d232a3b35832be0d23ff`
Log: [031_RED_matched_hessian.log](logs/031_RED_matched_hessian.log)
UTC: 2026-09-21T11:42:42.071001+00:00 to 2026-09-21T11:42:42.289895+00:00

## 032 GREEN matched_hessian (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_matched_layer_hessian_never_averages_front_and_back
```

Command SHA256: `2fb973a4415db1a8ca493925898f49d5e3761337112ca5414200f690104e4c4a`
Log SHA256: `b1f8cc880a0d75b56752dc315397f48a7d25f669cc8b2f8718987235d7c76308`
Log: [032_GREEN_matched_hessian.log](logs/032_GREEN_matched_hessian.log)
UTC: 2026-09-21T11:43:15.890486+00:00 to 2026-09-21T11:43:16.816554+00:00

## 033 RED geometry_required (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_ID_turnover_alone_cannot_activate_any_line_channel
```

Command SHA256: `dfd088780ad66418ca65419c8c7ea49ea3fff899f777ed1945d78faf4c233145`
Log SHA256: `d474a21f728f41dbb596d2aca4af8492357e763a17a9d961f792e69659d90fe9`
Log: [033_RED_geometry_required.log](logs/033_RED_geometry_required.log)
UTC: 2026-09-21T11:44:14.347013+00:00 to 2026-09-21T11:44:14.566434+00:00

## 034 GREEN geometry_required (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_ID_turnover_alone_cannot_activate_any_line_channel
```

Command SHA256: `dfd088780ad66418ca65419c8c7ea49ea3fff899f777ed1945d78faf4c233145`
Log SHA256: `4615d37c625f865e7c7ad35c90438d82ff0e4df61a85beb53e9cca0370e1eccc`
Log: [034_GREEN_geometry_required.log](logs/034_GREEN_geometry_required.log)
UTC: 2026-09-21T11:45:30.959706+00:00 to 2026-09-21T11:45:32.031980+00:00

## 035 RED controls (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_controls_preserve_mass_and_shuffle_slots_not_global_labels
```

Command SHA256: `dd98db92b4ce9b0567089cc4f2d73b003608115f8690cded1583cedda7b1b04d`
Log SHA256: `18bcb89bc1a013a69b6f123c26220bdbe5d44dd67cf06691a7c96438a2882578`
Log: [035_RED_controls.log](logs/035_RED_controls.log)
UTC: 2026-09-21T11:46:56.041618+00:00 to 2026-09-21T11:46:56.245893+00:00

## 036 GREEN controls (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_controls_preserve_mass_and_shuffle_slots_not_global_labels
```

Command SHA256: `dd98db92b4ce9b0567089cc4f2d73b003608115f8690cded1583cedda7b1b04d`
Log SHA256: `f753dde9c8ab678a1c25d6cdd07e2e495634df08c867ba7ba99600a813486bc6`
Log: [036_GREEN_controls.log](logs/036_GREEN_controls.log)
UTC: 2026-09-21T11:46:56.333365+00:00 to 2026-09-21T11:46:56.539558+00:00

## 037 RED oriented_hysteresis (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_oriented_hysteresis_recovers_weak_span_and_rejects_wrong_class
```

Command SHA256: `33730d020d5fb59213d45c005af6ed1518b719c050cfd0c39cf23fd1c6dd2e08`
Log SHA256: `c0db4485a3ade55ff0c08f75849860de88fb18bded42f880e816d46d4b1fb364`
Log: [037_RED_oriented_hysteresis.log](logs/037_RED_oriented_hysteresis.log)
UTC: 2026-09-21T11:48:16.616452+00:00 to 2026-09-21T11:48:16.824503+00:00

## 038 GREEN oriented_hysteresis (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_oriented_hysteresis_recovers_weak_span_and_rejects_wrong_class
```

Command SHA256: `33730d020d5fb59213d45c005af6ed1518b719c050cfd0c39cf23fd1c6dd2e08`
Log SHA256: `66747a060340b5b6a505896f3d5622ec27849ca112daef61944557cf563bd824`
Log: [038_GREEN_oriented_hysteresis.log](logs/038_GREEN_oriented_hysteresis.log)
UTC: 2026-09-21T11:48:16.922898+00:00 to 2026-09-21T11:48:17.988802+00:00

## 039 RED frozen_bands (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_frozen_percentiles_keep_soft_response_and_raw_band_grids
```

Command SHA256: `13cd55a4ffcda7575d7e88d2a6648a736d28795f54f6e06e2a88dd84900f087f`
Log SHA256: `44abf9e54fd562174121b69df5b5c310ee087e8318e1163946fb65a1e8a8390c`
Log: [039_RED_frozen_bands.log](logs/039_RED_frozen_bands.log)
UTC: 2026-09-21T11:50:03.999076+00:00 to 2026-09-21T11:50:04.238884+00:00

## 040 GREEN frozen_bands (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_frozen_percentiles_keep_soft_response_and_raw_band_grids
```

Command SHA256: `13cd55a4ffcda7575d7e88d2a6648a736d28795f54f6e06e2a88dd84900f087f`
Log SHA256: `3a3320dae5d63a1968cb74e28d81b5ab67f453028dd70714477bf275b90f2570`
Log: [040_GREEN_frozen_bands.log](logs/040_GREEN_frozen_bands.log)
UTC: 2026-09-21T11:50:04.324747+00:00 to 2026-09-21T11:50:05.439882+00:00

## 041 RED g1_view (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1.G1Tests.test_native_view_saves_every_control_layers_and_separate_soft_channels
```

Command SHA256: `6f8eb4a4b606a249e740aa0dbd1eeb7cd321ff4f2243a2524f0bf051692db808`
Log SHA256: `43620e3bfff85a83f947f215a7ad5963ee52400437482f7e13adda0458b25d6d`
Log: [041_RED_g1_view.log](logs/041_RED_g1_view.log)
UTC: 2026-09-21T11:53:16.556031+00:00 to 2026-09-21T11:53:16.706679+00:00

## 042 GREEN g1_view (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1.G1Tests.test_native_view_saves_every_control_layers_and_separate_soft_channels
```

Command SHA256: `6f8eb4a4b606a249e740aa0dbd1eeb7cd321ff4f2243a2524f0bf051692db808`
Log SHA256: `13f47dc2d9c052ac979c73debd4134ed5f71c9c14a9fb2362f4417ec19743ad9`
Log: [042_GREEN_g1_view.log](logs/042_GREEN_g1_view.log)
UTC: 2026-09-21T11:54:40.357201+00:00 to 2026-09-21T11:54:44.705549+00:00

## 043 RED fixed_sensitivity (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1.G1Tests.test_fixed_k_sensitivity_cannot_stop_at_a_native_mass_target
```

Command SHA256: `cbcd164abd9a25c85c7eaaf5cbeb69cdd8cd3e693b090f46a40775e284654351`
Log SHA256: `33b4d4b100d00abd0bbad259fa3801e190e38d408dc8b0b8b593687a4888bc56`
Log: [043_RED_fixed_sensitivity.log](logs/043_RED_fixed_sensitivity.log)
UTC: 2026-09-21T11:56:13.173202+00:00 to 2026-09-21T11:56:13.955522+00:00

## 044 GREEN fixed_sensitivity (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1.G1Tests.test_fixed_k_sensitivity_cannot_stop_at_a_native_mass_target
```

Command SHA256: `cbcd164abd9a25c85c7eaaf5cbeb69cdd8cd3e693b090f46a40775e284654351`
Log SHA256: `0ca300743e45930fa81276a997dcf480631a9ca3dd3085ad4936162dedd1987a`
Log: [044_GREEN_fixed_sensitivity.log](logs/044_GREEN_fixed_sensitivity.log)
UTC: 2026-09-21T11:56:14.106998+00:00 to 2026-09-21T11:56:15.451815+00:00

## 045 RED g1_sheets (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1.G1Tests.test_complete_sheets_decode_without_changing_scientific_arrays
```

Command SHA256: `7ea9fabf3579da23f17e0a3748dd467178fe951db89c35125e1d3f8226b60a06`
Log SHA256: `380cb48ae9f3d44c0dfa087eaf8d5b8a64ef8014c7425087b4abf506345936ae`
Log: [045_RED_g1_sheets.log](logs/045_RED_g1_sheets.log)
UTC: 2026-09-21T11:57:03.321735+00:00 to 2026-09-21T11:57:04.120479+00:00

## 046 GREEN g1_sheets (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1.G1Tests.test_complete_sheets_decode_without_changing_scientific_arrays
```

Command SHA256: `7ea9fabf3579da23f17e0a3748dd467178fe951db89c35125e1d3f8226b60a06`
Log SHA256: `99d4aaa16ef24ab6a3ca47e5e2597e2036b6009f987a0b16efb53d1f65d6436a`
Log: [046_GREEN_g1_sheets.log](logs/046_GREEN_g1_sheets.log)
UTC: 2026-09-21T11:57:04.263642+00:00 to 2026-09-21T11:57:18.967250+00:00

## 047 RED g1_cli (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1.G1Tests.test_g1_cli_requires_new_output_and_exposes_gate_input
```

Command SHA256: `9874319a8f3fedd86683796c8df75d5ac2455c50ee6e1dea594d857d06621152`
Log SHA256: `98ff0b57be7c03e7cd3b36b701a65da789950cf56a27ba70b0bf33f9a748bc39`
Log: [047_RED_g1_cli.log](logs/047_RED_g1_cli.log)
UTC: 2026-09-21T11:58:50.087899+00:00 to 2026-09-21T11:58:51.724568+00:00

## 048 GREEN g1_cli (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1.G1Tests.test_g1_cli_requires_new_output_and_exposes_gate_input
```

Command SHA256: `9874319a8f3fedd86683796c8df75d5ac2455c50ee6e1dea594d857d06621152`
Log SHA256: `9d7de256990dcd9fb285c5669bfce6dd1abbdab35a87626952bce616a8b31b07`
Log: [048_GREEN_g1_cli.log](logs/048_GREEN_g1_cli.log)
UTC: 2026-09-21T11:58:51.909506+00:00 to 2026-09-21T11:58:57.626846+00:00

## 049 CHECK targeted_g1 (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_mass test_adaptive_layers test_adaptive_evidence test_adaptive_g1 test_adaptive_verification test_topk_layered_evidence test_topk_layered_verification
```

Command SHA256: `c34804d43efa116701f8efb41c8f0c3a9f2511390543e1a3a65481b2d580c267`
Log SHA256: `2ce238268b27f14a4d59ab4ca2956d473ea92ab23c69c50d44125b7319de7660`
Log: [049_CHECK_targeted_g1.log](logs/049_CHECK_targeted_g1.log)
UTC: 2026-09-21T11:59:13.999115+00:00 to 2026-09-21T12:00:04.232550+00:00

## 050 CHECK compile_evidence (exit 0)

```bash
g++ -O3 -std=c++17 -shared -fPIC -fopenmp src/adaptive_evidence_native.cpp -o out/adaptive_mass_layered_probe/setup/adaptive_evidence_native.so
```

Command SHA256: `104e461afdfed5125162eb0ea65044f70604ab3382df50438a6a1f471f56f138`
Log SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
Log: [050_CHECK_compile_evidence.log](logs/050_CHECK_compile_evidence.log)
UTC: 2026-09-21T12:00:24.832203+00:00 to 2026-09-21T12:00:26.893917+00:00

## 051 RUN g1_run (exit -2)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/g1_run.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache scripts/render_adaptive_g1.py --output out/adaptive_mass_layered_probe/g1_run
```

Command SHA256: `747adb610835329df88cb45267ae14dfb58207fba25390c67f3ed96c72ff4e0d`
Log SHA256: `b2fe070b65626831fc1e2008305e8f7e4497e3fe10682c3659ddfbff0d8346a3`
Log: [051_RUN_g1_run.log](logs/051_RUN_g1_run.log)
UTC: 2026-09-21T12:00:40.684428+00:00 to 2026-09-21T12:10:09.956098+00:00

## 052 RED g1_layer_audit (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_layer_verifier_rejects_wrong_assignment_and_lost_overflow
```

Command SHA256: `e3c76ab1db235f6576496b9bbf07d77bcf5070dc1eb112587614bb75388a762d`
Log SHA256: `4f0fa84fa5092d405bdd23017459681257c4703d67551ef9ff9509069f451969`
Log: [052_RED_g1_layer_audit.log](logs/052_RED_g1_layer_audit.log)
UTC: 2026-09-21T12:02:53.131130+00:00 to 2026-09-21T12:02:53.404933+00:00

## 053 GREEN g1_layer_audit (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_layer_verifier_rejects_wrong_assignment_and_lost_overflow
```

Command SHA256: `e3c76ab1db235f6576496b9bbf07d77bcf5070dc1eb112587614bb75388a762d`
Log SHA256: `555fdd5be4dcee38e43dd8f35067b10799a5e3ef8166c9b99da99fe7dc66675d`
Log: [053_GREEN_g1_layer_audit.log](logs/053_GREEN_g1_layer_audit.log)
UTC: 2026-09-21T12:02:53.537374+00:00 to 2026-09-21T12:02:53.882750+00:00

## 054 RED g1_band_audit (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_band_verifier_rejects_below_threshold_ink_and_changed_soft_field
```

Command SHA256: `d3110363ec0e8b43db0cb5e0112aacc905aa6e4cdce9d114a73ec5454840ffa2`
Log SHA256: `9203b07f0986699609d286bf6d4615b33bc21533aa08971f31a8ee703898f312`
Log: [054_RED_g1_band_audit.log](logs/054_RED_g1_band_audit.log)
UTC: 2026-09-21T12:05:13.403557+00:00 to 2026-09-21T12:05:13.785717+00:00

## 055 GREEN g1_band_audit (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_band_verifier_rejects_below_threshold_ink_and_changed_soft_field
```

Command SHA256: `d3110363ec0e8b43db0cb5e0112aacc905aa6e4cdce9d114a73ec5454840ffa2`
Log SHA256: `8cceb49309da0be622acb084fa07cb6b39c11584abf9a3e365f1ac74d042d96d`
Log: [055_GREEN_g1_band_audit.log](logs/055_GREEN_g1_band_audit.log)
UTC: 2026-09-21T12:05:13.928338+00:00 to 2026-09-21T12:05:14.296686+00:00

## 056 GREEN g1_band_audit (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_band_verifier_rejects_below_threshold_ink_and_changed_soft_field
```

Command SHA256: `d3110363ec0e8b43db0cb5e0112aacc905aa6e4cdce9d114a73ec5454840ffa2`
Log SHA256: `f753dde9c8ab678a1c25d6cdd07e2e495634df08c867ba7ba99600a813486bc6`
Log: [056_GREEN_g1_band_audit.log](logs/056_GREEN_g1_band_audit.log)
UTC: 2026-09-21T12:05:44.974107+00:00 to 2026-09-21T12:05:45.327649+00:00

## 057 RED g1_verifier_cli (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_g1_verifier_cli_exposes_reached_stage_audit
```

Command SHA256: `43215159db6d331c96a2a0e51ad0147ee2a8ee8439b57b27460c1e4fdf28cf53`
Log SHA256: `e1edef04171c513a39b471529fd56ad48a2e49c19ec4613e11d3be434f46b340`
Log: [057_RED_g1_verifier_cli.log](logs/057_RED_g1_verifier_cli.log)
UTC: 2026-09-21T12:06:42.646387+00:00 to 2026-09-21T12:06:43.456605+00:00

## 058 GREEN g1_verifier_cli (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_g1_verifier_cli_exposes_reached_stage_audit
```

Command SHA256: `43215159db6d331c96a2a0e51ad0147ee2a8ee8439b57b27460c1e4fdf28cf53`
Log SHA256: `e41d6cb9cfdfe5660fe2e4ab996d23f50a57d22da37467b9be02471fb751cb68`
Log: [058_GREEN_g1_verifier_cli.log](logs/058_GREEN_g1_verifier_cli.log)
UTC: 2026-09-21T12:08:52.001205+00:00 to 2026-09-21T12:08:52.980592+00:00

## 059 RED layer_match_tie (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_equal_distance_neighbor_layer_match_keeps_frontmost_tie
```

Command SHA256: `f2fa72e60748a6b3d285b36d6ab895aa6441f06c0a6a63691e0380984bad7db7`
Log SHA256: `4967c87ed431dce9d54d9d8eebf17c72da00e79df7be31a5b602cfa04a3cde62`
Log: [059_RED_layer_match_tie.log](logs/059_RED_layer_match_tie.log)
UTC: 2026-09-21T12:09:57.493805+00:00 to 2026-09-21T12:09:58.970516+00:00

## 060 GREEN layer_match_tie (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_equal_distance_neighbor_layer_match_keeps_frontmost_tie
```

Command SHA256: `f2fa72e60748a6b3d285b36d6ab895aa6441f06c0a6a63691e0380984bad7db7`
Log SHA256: `c3a62b9a3b1447d1ca2495a6ab7183f8972f2492fa5fdeb3cb9cc754629e45a3`
Log: [060_GREEN_layer_match_tie.log](logs/060_GREEN_layer_match_tie.log)
UTC: 2026-09-21T12:11:34.880404+00:00 to 2026-09-21T12:11:35.899737+00:00

## 061 RED layer_match_tie (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_equal_distance_neighbor_layer_match_keeps_frontmost_tie
```

Command SHA256: `f2fa72e60748a6b3d285b36d6ab895aa6441f06c0a6a63691e0380984bad7db7`
Log SHA256: `3552066eed91d0ee11cf830207b47f35f88a8c1736d5ee3c50365e6912589d2f`
Log: [061_RED_layer_match_tie.log](logs/061_RED_layer_match_tie.log)
UTC: 2026-09-21T12:13:05.053352+00:00 to 2026-09-21T12:13:06.060656+00:00

## 062 GREEN layer_match_tie (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_equal_distance_neighbor_layer_match_keeps_frontmost_tie
```

Command SHA256: `f2fa72e60748a6b3d285b36d6ab895aa6441f06c0a6a63691e0380984bad7db7`
Log SHA256: `e9d98c63f82130da54510120a6f498defaf34932ccba130b4eb657d453601053`
Log: [062_GREEN_layer_match_tie.log](logs/062_GREEN_layer_match_tie.log)
UTC: 2026-09-21T12:13:06.150801+00:00 to 2026-09-21T12:13:07.133178+00:00

## 063 RED batched_hessians (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_batched_scales_preserve_separate_native_hessians_bitwise
```

Command SHA256: `3c5d9e586d5c42a985614786da136a03b6440c1e4671118b5d79558e6ca1c3a6`
Log SHA256: `6f861b18355d98d7f354d19a790da0f8f94ae79eed0ec1138f6735b05d708620`
Log: [063_RED_batched_hessians.log](logs/063_RED_batched_hessians.log)
UTC: 2026-09-21T12:14:34.505392+00:00 to 2026-09-21T12:14:34.723687+00:00

## 064 GREEN batched_hessians (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence.EvidenceTests.test_batched_scales_preserve_separate_native_hessians_bitwise
```

Command SHA256: `3c5d9e586d5c42a985614786da136a03b6440c1e4671118b5d79558e6ca1c3a6`
Log SHA256: `50e7c74f34998fcae5881e4baa1b36c0e84600d64459942579a1165d08f8eaff`
Log: [064_GREEN_batched_hessians.log](logs/064_GREEN_batched_hessians.log)
UTC: 2026-09-21T12:14:34.817770+00:00 to 2026-09-21T12:14:36.054260+00:00

## 065 CHECK compile_evidence_fixed (exit 0)

```bash
g++ -O3 -std=c++17 -shared -fPIC -fopenmp src/adaptive_evidence_native.cpp -o out/adaptive_mass_layered_probe/setup/adaptive_evidence_native.so
```

Command SHA256: `104e461afdfed5125162eb0ea65044f70604ab3382df50438a6a1f471f56f138`
Log SHA256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
Log: [065_CHECK_compile_evidence_fixed.log](logs/065_CHECK_compile_evidence_fixed.log)
UTC: 2026-09-21T12:15:04.298493+00:00 to 2026-09-21T12:15:05.292527+00:00

## 066 CHECK real_hessian_parity (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -c 'import numpy as np,time,json,hashlib; from pathlib import Path; from src.adaptive_evidence import matched_hessian,matched_hessians; p=Path("out/adaptive_mass_layered_probe/attempt_01_layer_tie/g1_run/raw/lego_1_full.npz"); f=np.load(p); keys=["retained_depth","retained_mass","local_scale","retained_index","layer_seedable"]; layers={k:f["layers."+k] for k in keys}; f.close(); lib=Path("out/adaptive_mass_layered_probe/setup/adaptive_evidence_native.so"); start=time.perf_counter(); reference=[matched_hessian(layers,s,lib) for s in [1.5,2.5,4.]]; separate=time.perf_counter()-start; start=time.perf_counter(); batched=matched_hessians(layers,lib); batch=time.perf_counter()-start; result=dict(separate_seconds=separate,batched_seconds=batch,equal=[np.array_equal(a,b) for a,b in zip(reference,batched)],hashes=[hashlib.sha256(a.tobytes()).hexdigest() for a in batched]); Path("artifacts/adaptive_mass_layered_probe/HESSIAN_PARITY.json").write_text(json.dumps(result,indent=2)+"\n"); print(result); assert all(result["equal"])'
```

Command SHA256: `5059558e376a68c4945ede2e89337fc37918e92ea6f7345d5065eeeb0a8334d0`
Log SHA256: `0a0abd834e09e3cb0cd0f714b6462ea527c894d78a542806602ad09008a46520`
Log: [066_CHECK_real_hessian_parity.log](logs/066_CHECK_real_hessian_parity.log)
UTC: 2026-09-21T12:15:23.163951+00:00 to 2026-09-21T12:15:28.689326+00:00

## 067 CHECK targeted_g1_fixed (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_evidence test_adaptive_g1 test_adaptive_g1_verification
```

Command SHA256: `8c4dc0f7c5e2622c836b637ae6bc7a7568ee8be612fe25d20bab81f1c8e5c412`
Log SHA256: `41fc086e2a62733bd3e35f1da867b9e34f8494f7986d27047a2deae9dc85221f`
Log: [067_CHECK_targeted_g1_fixed.log](logs/067_CHECK_targeted_g1_fixed.log)
UTC: 2026-09-21T12:18:18.363750+00:00 to 2026-09-21T12:18:44.007762+00:00

## 068 RUN g1_run_fixed (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/g1_run.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache scripts/render_adaptive_g1.py --output out/adaptive_mass_layered_probe/g1_run
```

Command SHA256: `747adb610835329df88cb45267ae14dfb58207fba25390c67f3ed96c72ff4e0d`
Log SHA256: `f861c9581a51f4bce66e4d8b6bbe89288cf3120ce8c0d4f8105dacf6eca80d63`
Log: [068_RUN_g1_run_fixed.log](logs/068_RUN_g1_run_fixed.log)
UTC: 2026-09-21T12:19:00.868002+00:00 to 2026-09-21T13:29:23.523734+00:00

## 069 CHECK full_suite_current (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/full_suite_current.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache -m unittest discover -s tests -v
```

Command SHA256: `601bcbe5a3d8118d7f7be33f039f9d2d9407a18dd93511bb0432a64765ab3d3d`
Log SHA256: `ace089d012d2d2e3140cebb3bb59162582ebddbe86fa6f6eb3b8530eb5d3dcc8`
Log: [069_CHECK_full_suite_current.log](logs/069_CHECK_full_suite_current.log)
UTC: 2026-09-21T12:24:31.632928+00:00 to 2026-09-21T12:26:30.708631+00:00

## 070 RED diagnostic_layout (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layout -v
```

Command SHA256: `fd2b763f4076b8a51ba9e5cf3d3eabdb5b199620fcbb0b73b33a367f03d1ea89`
Log SHA256: `b781dbfc8bec985e71cdf738fa48a9fab167aded136f57f638429b91194910e9`
Log: [070_RED_diagnostic_layout.log](logs/070_RED_diagnostic_layout.log)
UTC: 2026-09-21T12:30:54.274368+00:00 to 2026-09-21T12:30:54.613147+00:00

## 071 GREEN diagnostic_layout (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layout -v
```

Command SHA256: `fd2b763f4076b8a51ba9e5cf3d3eabdb5b199620fcbb0b73b33a367f03d1ea89`
Log SHA256: `dadadb815b43f56aecb3ef8c56b940b18ef6c5eaadc0681e30fe782d39fff068`
Log: [071_GREEN_diagnostic_layout.log](logs/071_GREEN_diagnostic_layout.log)
UTC: 2026-09-21T12:31:12.550796+00:00 to 2026-09-21T12:31:12.951908+00:00

## 072 RED mechanism_maps (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layout.LayoutTests.test_mechanism_maps_include_residuals_and_all_four_layers -v
```

Command SHA256: `c7befff06022279bb0e3de63e1c9b908e55fc632111c4418390f54ecbc296736`
Log SHA256: `c847ebfb21f4251adfae59937b8fdd4cb369ad6f05b14aa0b4d04f39386eaa35`
Log: [072_RED_mechanism_maps.log](logs/072_RED_mechanism_maps.log)
UTC: 2026-09-21T12:31:36.478522+00:00 to 2026-09-21T12:31:36.829777+00:00

## 073 GREEN mechanism_maps (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layout -v
```

Command SHA256: `fd2b763f4076b8a51ba9e5cf3d3eabdb5b199620fcbb0b73b33a367f03d1ea89`
Log SHA256: `3ae2ba4e7e416a88f315a44548bb86a3cabfa23b90ded79350ee8a936b86e0a6`
Log: [073_GREEN_mechanism_maps.log](logs/073_GREEN_mechanism_maps.log)
UTC: 2026-09-21T12:31:59.416801+00:00 to 2026-09-21T12:31:59.696177+00:00

## 074 RED layout_cli (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layout.LayoutTests.test_layout_cli_requires_existing_run -v
```

Command SHA256: `33498d4c98b3075c0c610c79f62a734d83859a634aae8fdc18df032fb4fe7561`
Log SHA256: `6d1462325badd005e96328f95264ef58ea0624b31aea96488557bee739457bda`
Log: [074_RED_layout_cli.log](logs/074_RED_layout_cli.log)
UTC: 2026-09-21T12:32:29.250535+00:00 to 2026-09-21T12:32:29.669653+00:00

## 075 GREEN layout_cli (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layout -v
```

Command SHA256: `fd2b763f4076b8a51ba9e5cf3d3eabdb5b199620fcbb0b73b33a367f03d1ea89`
Log SHA256: `d16016ff8c5f86b0adb84e28e17a894df47dd59b0d6cfe8d428aa6054df443d0`
Log: [075_GREEN_layout_cli.log](logs/075_GREEN_layout_cli.log)
UTC: 2026-09-21T12:33:15.571894+00:00 to 2026-09-21T12:33:16.066394+00:00

## 076 RUN g0_rerun (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/rerun.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache scripts/render_adaptive_mass_probe.py --output out/adaptive_mass_layered_probe/rerun
```

Command SHA256: `f7f0f85eb3f5fed74751e945a67b03c24c25ba38d7d1b8343e71f97e1be3ce65`
Log SHA256: `6befdcb2aa6e01d9eef76074fcda0cef789c728065aaa76baa53c6d23f190c9b`
Log: [076_RUN_g0_rerun.log](logs/076_RUN_g0_rerun.log)
UTC: 2026-09-21T12:33:46.542015+00:00 to 2026-09-21T12:43:52.683844+00:00

## 077 RED layout_audit (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_layout_verifier_rejects_changed_science_bytes -v
```

Command SHA256: `f35941efe62da7881b2622e7fab80726af1a7873ea21e6625e46e34d696de99a`
Log SHA256: `dbe59e1d0e6f47165ccb933bc0df580e88e5361fcefb7f44eab93c0ab30cb433`
Log: [077_RED_layout_audit.log](logs/077_RED_layout_audit.log)
UTC: 2026-09-21T12:34:04.576186+00:00 to 2026-09-21T12:34:04.873171+00:00

## 078 GREEN layout_audit (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification -v
```

Command SHA256: `fedf522e897475e94ca8d2042ad1c23c7d00cda2f63db52d773304d71437ef92`
Log SHA256: `bccac13b8ec21a7fed85e9ce6c1d8da7471041c53fc3e1676f978738732353a7`
Log: [078_GREEN_layout_audit.log](logs/078_GREEN_layout_audit.log)
UTC: 2026-09-21T12:34:23.989062+00:00 to 2026-09-21T12:34:24.930436+00:00

## 079 CHECK full_suite_final (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/full_suite_final.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
```

Command SHA256: `e943a034874519831fe1cbe59b55e555010da516bec6035330736c3bc660f248`
Log SHA256: `6d02f7c4b7327e7831ec57911c40aacc2cf35ee42f5e5df637b72cdab5bba097`
Log: [079_CHECK_full_suite_final.log](logs/079_CHECK_full_suite_final.log)
UTC: 2026-09-21T12:34:54.386254+00:00 to 2026-09-21T12:36:51.087106+00:00

## 080 RUN g1_rerun (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/g1_rerun.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache scripts/render_adaptive_g1.py --output out/adaptive_mass_layered_probe/g1_rerun
```

Command SHA256: `1c4c565c33928055b70bfddbb53133ab9a265e46f4b5388e8a723ce7ccefca18`
Log SHA256: `f861c9581a51f4bce66e4d8b6bbe89288cf3120ce8c0d4f8105dacf6eca80d63`
Log: [080_RUN_g1_rerun.log](logs/080_RUN_g1_rerun.log)
UTC: 2026-09-21T12:36:44.955146+00:00 to 2026-09-21T13:45:33.341795+00:00

## 081 CHECK full_suite_access (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -
```

Command SHA256: `ed958570f227be4885705ee9fe140f426290452933b4fa86f03318b6edaf9b00`
Log SHA256: `2a63748886ad794713a4987594a4012edf939189472f36e4139af45b1fcb0d85`
Log: [081_CHECK_full_suite_access.log](logs/081_CHECK_full_suite_access.log)
UTC: 2026-09-21T12:37:35.102770+00:00 to 2026-09-21T12:37:43.813144+00:00

## 082 CHECK g1_early_determinism (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/check_first_view_rerun.py
```

Command SHA256: `7d6d109ae8ab4cfb197a91127b8c4dbe948802582614c3a9c077aed930dfbeb4`
Log SHA256: `be9b9115ebf5183ad6412a27559267b39b0035adcdaa6c47b1cc04edd13058fc`
Log: [082_CHECK_g1_early_determinism.log](logs/082_CHECK_g1_early_determinism.log)
UTC: 2026-09-21T12:43:28.818148+00:00 to 2026-09-21T12:43:37.839641+00:00

## 083 CHECK g0_full_verification (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/verify_adaptive_mass_probe.py
```

Command SHA256: `f2a227199d7615293b2e769fa36e31a74d7e554ee533f50ab936ec582ba48b84`
Log SHA256: `ac28e9b3afcda1c355778e9d14e00e619e1e6667f4edfcca6c8117901e63e765`
Log: [083_CHECK_g0_full_verification.log](logs/083_CHECK_g0_full_verification.log)
UTC: 2026-09-21T12:45:22.179035+00:00 to 2026-09-21T12:48:43.334516+00:00

## 084 RED frozen_camera_audit (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification.G1VerificationTests.test_camera_audit_rejects_valid_matrix_from_wrong_frozen_view -v
```

Command SHA256: `93a591bb978f99fed5fda867c88b4423330e79083d9de35864fc00f6d63f4c1f`
Log SHA256: `5053a185fb48189dbc6e447dd084b1cb8a9c70ddd1597093188382d4ba106f9f`
Log: [084_RED_frozen_camera_audit.log](logs/084_RED_frozen_camera_audit.log)
UTC: 2026-09-21T13:04:32.734619+00:00 to 2026-09-21T13:04:33.065343+00:00

## 085 GREEN frozen_camera_audit (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_g1_verification -v
```

Command SHA256: `fedf522e897475e94ca8d2042ad1c23c7d00cda2f63db52d773304d71437ef92`
Log SHA256: `fb873d6270dcc7b7056ee33e4fbccafda24d231b9b5e0251f8180260f762f200`
Log: [085_GREEN_frozen_camera_audit.log](logs/085_GREEN_frozen_camera_audit.log)
UTC: 2026-09-21T13:04:45.935766+00:00 to 2026-09-21T13:04:47.079384+00:00

## 086 CHECK full_suite_cameras (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/full_suite_cameras.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
```

Command SHA256: `04231ecdf699b57eb73aa41ad740fcf35fb741a86dd6e2b321a781a61118c167`
Log SHA256: `bff0d7c4201f56ea7ea0c2c714f0be4e350ea9217ea25edd7b6d7370fdf82f25`
Log: [086_CHECK_full_suite_cameras.log](logs/086_CHECK_full_suite_cameras.log)
UTC: 2026-09-21T13:04:59.445948+00:00 to 2026-09-21T13:06:56.708558+00:00

## 087 CHECK full_suite_access_final (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/audit_full_suite.py
```

Command SHA256: `92cf76df2610920ceb31cdce9744f2edb60aaba3df465312fb5a2a6fee958015`
Log SHA256: `962f9a7416e9c892d7b6aab63efe7110ee876335082f193623746e49b2348222`
Log: [087_CHECK_full_suite_access_final.log](logs/087_CHECK_full_suite_access_final.log)
UTC: 2026-09-21T13:07:15.113049+00:00 to 2026-09-21T13:07:27.215822+00:00

## 088 RED layout_startup_audit (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layout.LayoutTests.test_layout_confinement_audits_startup_directory_metadata -v
```

Command SHA256: `487685670cd8ca0dc3283db8b2dff6ea6bc2ca20128ab088d06738caaabafcfa`
Log SHA256: `e02b96f947dce417dedd6ada06a5346dbfd212f1a382b12717435a07ab2e8130`
Log: [088_RED_layout_startup_audit.log](logs/088_RED_layout_startup_audit.log)
UTC: 2026-09-21T13:12:27.074258+00:00 to 2026-09-21T13:12:28.864447+00:00

## 089 GREEN layout_startup_audit (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest test_adaptive_layout -v
```

Command SHA256: `fd2b763f4076b8a51ba9e5cf3d3eabdb5b199620fcbb0b73b33a367f03d1ea89`
Log SHA256: `7ab547afa764cbb88870b1aa2ae64e421362c8804813c9bd87e09a0038c292f7`
Log: [089_GREEN_layout_startup_audit.log](logs/089_GREEN_layout_startup_audit.log)
UTC: 2026-09-21T13:12:49.623150+00:00 to 2026-09-21T13:12:52.199469+00:00

## 090 CHECK full_suite_layout (exit 1)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/full_suite_layout.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
```

Command SHA256: `ae7caf034d71fe0c910700473527bb5c3aff53c898bc4a3f2ad8628f846372b6`
Log SHA256: `95a782d2b4ce6449ab69e75212427e169a1a959619a2932410de6a82beeab77c`
Log: [090_CHECK_full_suite_layout.log](logs/090_CHECK_full_suite_layout.log)
UTC: 2026-09-21T13:13:05.180184+00:00 to 2026-09-21T13:14:58.390108+00:00

## 091 CHECK full_suite_all_integration (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
```

Command SHA256: `fb96efa4df8fca1053326b361cb96624ddebc96574b799b4539f87404fdc1d01`
Log SHA256: `0be04391159ca3cd63bda188146586e40fe3cf21dd348fc24f5c008b5bae32ea`
Log: [091_CHECK_full_suite_all_integration.log](logs/091_CHECK_full_suite_all_integration.log)
UTC: 2026-09-21T13:15:39.461672+00:00 to 2026-09-21T13:16:39.398876+00:00

## 092 CHECK full_suite_access_traced (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/full_suite_access_traced.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -m unittest discover -s tests -v
```

Command SHA256: `c77b1657a89d9b9b1cb9dc4923565ab3c59d6da56de7bd0caa4214fbf9ca7e8c`
Log SHA256: `937509d5ea8f72fbb6e946e37b4c9a66bdd4b67c3df79dc473766aca38d0edc6`
Log: [092_CHECK_full_suite_access_traced.log](logs/092_CHECK_full_suite_access_traced.log)
UTC: 2026-09-21T13:17:23.781220+00:00 to 2026-09-21T13:18:56.998616+00:00

## 093 CHECK g1_layer_summary (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/summarize_g1_layers.py
```

Command SHA256: `b75b89526d1b669dd50db40ffc578ed475c9751809d20cb1b65554f8e24c0360`
Log SHA256: `83c71eabdd9493d17d930749cf4d6c7944aad5b29d73d8addff8f7eaacdda39f`
Log: [093_CHECK_g1_layer_summary.log](logs/093_CHECK_g1_layer_summary.log)
UTC: 2026-09-21T13:19:57.060766+00:00 to 2026-09-21T13:19:58.670661+00:00

## 094 CHECK full_suite_access_complete (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/audit_full_suite.py
```

Command SHA256: `92cf76df2610920ceb31cdce9744f2edb60aaba3df465312fb5a2a6fee958015`
Log SHA256: `24d0379ded6ed5fe5a184af5ec4304ec8223ef4444cdb78ee8c1bf24773e633f`
Log: [094_CHECK_full_suite_access_complete.log](logs/094_CHECK_full_suite_access_complete.log)
UTC: 2026-09-21T13:20:21.151651+00:00 to 2026-09-21T13:20:35.850917+00:00

## 095 RUN g1_run_layout (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/g1_run_layout.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache scripts/render_adaptive_g1_diagnostics.py --run out/adaptive_mass_layered_probe/g1_run
```

Command SHA256: `fb75f9aea421d53eb602610fc4e7302ee2ca440f4632babf2356fd8fdfbb38eb`
Log SHA256: `b242dea20932c6573d1102b52e3438773a53fac580469cdfa0617862c5e99a93`
Log: [095_RUN_g1_run_layout.log](logs/095_RUN_g1_run_layout.log)
UTC: 2026-09-21T13:29:50.005112+00:00 to 2026-09-21T13:34:13.027844+00:00

## 096 CHECK g1_control_metrics (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/summarize_g1_controls.py
```

Command SHA256: `3920027e6d8faea3590a5e39b00566738f3c08b736e75041e7b6283bc1a19406`
Log SHA256: `d030e224a8c935230dd4c4f99047d9cd8ad745bfecae79a733eafd1123e0f1ab`
Log: [096_CHECK_g1_control_metrics.log](logs/096_CHECK_g1_control_metrics.log)
UTC: 2026-09-21T13:44:23.199297+00:00 to 2026-09-21T13:44:23.295270+00:00

## 097 RUN g1_rerun_layout (exit 0)

```bash
strace -f -yy -e trace=open,openat,openat2,creat -o out/adaptive_mass_layered_probe/setup/g1_rerun_layout.strace /home/u00134/bin/miniconda3/envs/vfsdgs/bin/python -X pycache_prefix=/home/u00134/3dgs_line/tier1/out/adaptive_mass_layered_probe/setup/unused_cache scripts/render_adaptive_g1_diagnostics.py --run out/adaptive_mass_layered_probe/g1_rerun
```

Command SHA256: `d2870e43e75b0c4e972b48e46b2aa37617c9fac592dc1e44e07f3da300fc1f47`
Log SHA256: `b242dea20932c6573d1102b52e3438773a53fac580469cdfa0617862c5e99a93`
Log: [097_RUN_g1_rerun_layout.log](logs/097_RUN_g1_rerun_layout.log)
UTC: 2026-09-21T13:46:31.695991+00:00 to 2026-09-21T13:50:33.592627+00:00

## 098 CHECK g1_final_verification (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python scripts/verify_adaptive_g1.py
```

Command SHA256: `a92fdf59e028ff93bbadfd87a62bd2bf7866fbc35ef06e470b71f743f801d309`
Log SHA256: `d2d574ef93b1e463cfbede18f67424385fa9c496bc694a49761fa9935cb004ed`
Log: [098_CHECK_g1_final_verification.log](logs/098_CHECK_g1_final_verification.log)
UTC: 2026-09-21T13:53:05.612007+00:00 to 2026-09-21T14:40:37.484644+00:00

## 099 CHECK final_integrity (exit 1)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/final_integrity.py
```

Command SHA256: `71155853e6e468d66af285c20b9bca3af3f22f7d3b8c629c8eee88716cd552d6`
Log SHA256: `9a7e55336b9d94c7182be9eb5afba1883b2bc592eea97daaa2102ffc78d6d605`
Log: [099_CHECK_final_integrity.log](logs/099_CHECK_final_integrity.log)
UTC: 2026-09-21T13:53:06.809675+00:00 to 2026-09-21T13:53:40.898115+00:00

## 100 CHECK test_summary (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/summarize_tests.py
```

Command SHA256: `6b79b70ce8f01c2648b82be450f0a70a0860425cf569b32b66f0e8e39f57cda7`
Log SHA256: `2b82f74fa48ffb36b6cf6fd56310f061aa304a979422ed3101548dc0b01384b7`
Log: [100_CHECK_test_summary.log](logs/100_CHECK_test_summary.log)
UTC: 2026-09-21T14:05:48.503533+00:00 to 2026-09-21T14:05:48.550623+00:00

## 101 CHECK final_integrity (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/final_integrity.py
```

Command SHA256: `71155853e6e468d66af285c20b9bca3af3f22f7d3b8c629c8eee88716cd552d6`
Log SHA256: `3912ee9b349659989cbe840122711b5f3fd0a26f39dce95d58d02755b781a929`
Log: [101_CHECK_final_integrity.log](logs/101_CHECK_final_integrity.log)
UTC: 2026-09-21T14:08:50.154076+00:00 to 2026-09-21T14:09:16.471685+00:00

## 102 CHECK figure_index (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/render_figure_index.py
```

Command SHA256: `d168433e2827621dcb3246470b9ac6eaee157dfe471301ba5fbb31d00f59f3b6`
Log SHA256: `0e93d7e7d9a32b61ff47e8ec43258a146551a927225e971646217fbb80946a93`
Log: [102_CHECK_figure_index.log](logs/102_CHECK_figure_index.log)
UTC: 2026-09-21T14:11:46.947384+00:00 to 2026-09-21T14:11:49.789240+00:00

## 103 CHECK finalize_report (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/finalize_report.py
```

Command SHA256: `8e47b069d34e47258c7c1498f3c3a36a075cd0cac6a1011a529900b599970a26`
Log SHA256: `9e95b5a5d5b966e59c0415c8108049a6d664ca62c5c87faacf7492264dd25671`
Log: [103_CHECK_finalize_report.log](logs/103_CHECK_finalize_report.log)
UTC: 2026-09-21T14:41:03.485171+00:00 to 2026-09-21T14:41:03.942193+00:00

## 104 CHECK report_accuracy (exit 0)

```bash
/home/u00134/bin/miniconda3/envs/vfsdgs/bin/python artifacts/adaptive_mass_layered_probe/finalize_report.py
```

Command SHA256: `8e47b069d34e47258c7c1498f3c3a36a075cd0cac6a1011a529900b599970a26`
Log SHA256: `9e95b5a5d5b966e59c0415c8108049a6d664ca62c5c87faacf7492264dd25671`
Log: [104_CHECK_report_accuracy.log](logs/104_CHECK_report_accuracy.log)
UTC: 2026-09-21T14:42:04.278218+00:00 to 2026-09-21T14:42:04.775905+00:00
