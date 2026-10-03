"""Meaningful fixtures: a zero-scene scientific claim must never validate."""
import copy
import json
import tempfile
from pathlib import Path
import verify_blocker as verifier
import unittest
from verify_blocker import assess


class BlockerTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {
            'status': 'BLOCKED_NO_USABLE_NEW_SCENES',
            'requested_scene_order': ['hotdog', 'materials', 'mic', 'ship'],
            'selected_scenes': [],
            'scenes': {s: {'checkpoint_candidates': [], 'missing': ['vanilla_checkpoint']}
                       for s in ['hotdog', 'materials', 'mic', 'ship']},
        }
        self.manifest = {'F': [1,14,27,41,53,67,79,93], 'C': [7,21,33,47,59,73,86,99],
                         'selected_scenes': [], 'scenes': {}, 'expected_production_frames': 0,
                         'blocked_missing_scenes': ['hotdog', 'materials', 'mic', 'ship']}
        self.sources = {'scientific_sources_unchanged': True, 'locked_recipe_hash_valid': True,
                        'locked_parameter_hash_valid': True, 'locked_lock_hash_valid': True}

    def test_zero_scene_is_blocker_not_scientific_pass(self):
        r = assess(self.inventory, self.manifest, [], self.sources)
        self.assertEqual(r['status'], 'BLOCKER_CONFIRMED')
        self.assertFalse(r['science_executed'])
        self.assertIsNone(r['scientific_verdict'])
        self.assertEqual(r['completed_frames'], 0)

    def test_eligible_checkpoint_contradicts_zero_inventory(self):
        self.inventory['scenes']['ship']['checkpoint_candidates'] = [{'eligible': True}]
        with self.assertRaisesRegex(ValueError, 'eligible'):
            assess(self.inventory, self.manifest, [], self.sources)

    def test_missing_scene_inventory_is_rejected(self):
        del self.inventory['scenes']['mic']
        with self.assertRaisesRegex(ValueError, 'inventory scene'):
            assess(self.inventory, self.manifest, [], self.sources)

    def test_phantom_selected_scene_is_rejected(self):
        self.manifest['selected_scenes'] = ['ship']
        with self.assertRaisesRegex(ValueError, 'selected'):
            assess(self.inventory, self.manifest, [], self.sources)

    def test_zero_manifest_cannot_hide_output_or_seal(self):
        for name in ['frames/ship/F1/RGB.png', 'raw/ship/F1.npz', 'media/ship/arc.mp4',
                     'frames/ship/F1/SEAL.json']:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'production'):
                assess(self.inventory, self.manifest, [name], self.sources)

    def test_modified_scientific_source_is_rejected(self):
        self.sources['scientific_sources_unchanged'] = False
        with self.assertRaisesRegex(ValueError, 'source'):
            assess(self.inventory, self.manifest, [], self.sources)

    def test_wrong_camera_split_is_rejected(self):
        self.manifest['C'] = [7, 21, 34, 47, 59, 73, 86, 99]
        with self.assertRaisesRegex(ValueError, 'camera'):
            assess(self.inventory, self.manifest, [], self.sources)

    def test_lock_hash_corruption_is_rejected(self):
        self.sources['locked_parameter_hash_valid'] = False
        with self.assertRaisesRegex(ValueError, 'parameter'):
            assess(self.inventory, self.manifest, [], self.sources)


class EvidenceLinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent, prefix='fixture_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inventory = self.root / 'INVENTORY.json'
        self.inventory.write_text('{}')
        self.original = self.root / 'ORIGINAL_LOCK.json'
        self.original.write_text('{"frozen": true}')
        self.inherited = self.root / 'INHERITED_LOCK.json'
        self.inherited.write_bytes(self.original.read_bytes())
        self.manifest = {'inventory': {'path': str(self.inventory), 'sha256': verifier.sha(self.inventory)},
                         'inherited_lock': {'path': str(self.inherited), 'sha256': verifier.sha(self.original)}}

    def test_inventory_manifest_digest_change_is_rejected(self):
        self.manifest['inventory']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'inventory.*hash'):
            verifier.audit_manifest_links(self.manifest, self.inventory, self.original, verifier.sha(self.original))

    def test_inherited_lock_copy_change_is_rejected(self):
        self.inherited.write_text('{"frozen": false}')
        self.manifest['inherited_lock']['sha256'] = verifier.sha(self.inherited)
        with self.assertRaisesRegex(ValueError, 'inherited.*lock'):
            verifier.audit_manifest_links(self.manifest, self.inventory, self.original, verifier.sha(self.original))

    def test_unlisted_candidate_is_rejected_without_content_read(self):
        search = {'root': str(self.root), 'max_directory_depth': 2,
                  'pruned_directory_names': ['test', 'mesh'], 'pruned_directory_prefixes': [],
                  'follow_symlinks': False, 'exists': True, 'matched_files': []}
        candidate = self.root / 'hotdog' / 'point_cloud.ply'
        candidate.parent.mkdir()
        candidate.write_bytes(b'not even a valid PLY; enumeration must reject before any decode')
        with self.assertRaisesRegex(ValueError, 'UNDETERMINED.*unregistered'):
            verifier.audit_search_snapshot(search)

    def test_canonical_checkpoint_appearing_is_rejected(self):
        candidate = self.root / 'point_cloud.ply'
        candidate.write_bytes(b'candidate filename only')
        scene = {'canonical_expected_checkpoint_path': str(candidate),
                 'canonical_expected_checkpoint_exists': False}
        with self.assertRaisesRegex(ValueError, 'canonical.*checkpoint'):
            verifier.audit_canonical_missing({'hotdog': scene})


if __name__ == '__main__':
    unittest.main(verbosity=2)
