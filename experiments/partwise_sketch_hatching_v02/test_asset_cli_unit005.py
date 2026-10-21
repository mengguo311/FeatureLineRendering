"""Input/output and width-only contracts; no renderer is invoked by tests."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import asset_cli as cli


class AssetCLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = cli.UNIT / 'test_scratch'
        cls.scratch.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix='asset_contract_', dir=cls.scratch)
        cls.folder = Path(cls.temporary.name)
        previous = cli.UNIT.parent / 'unit_004'
        status = json.loads((previous / 'STATUS.json').read_text())
        cls.manifest = dict(schema=cli.SCHEMA, name='unit004_diagnostic_preview418',
            provenance=dict(geometry='authored GT', directions='manual'),
            verdict_metadata={key: status[key] for key in
                              ('scientific_verdict', 'claim_status', 'blockers')})
        cls.manifest['verdict_metadata']['source_unit'] = 'unit_004'
        for key, path in (('mesh', previous / 'inputs/lamp_mesh.npz'),
                          ('strokes', previous / 'inputs/selected.npz'),
                          ('config', previous / 'CONFIG.json')):
            cls.manifest[key] = dict(path=str(path), sha256=cli.sha(path))
        cls.asset = cls.folder / 'asset.json'
        cls.asset.write_text(json.dumps(cls.manifest))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def arguments(self, *extra):
        return cli.parser().parse_args(['edit', '--asset', str(self.asset),
            '--output', str(self.folder / 'unused_output'), '--part', 'shade',
            '--width', '1.5', *extra])

    def test_explicit_inputs_and_valid_hash_are_required(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.parser().parse_args(['preview', '--output', str(self.folder / 'x')])
        with self.assertRaises(FileNotFoundError):
            cli.read_asset(self.folder / 'missing.json')
        for change in ('hash', 'schema', 'verdict', 'missing_strokes'):
            manifest = copy.deepcopy(self.manifest)
            if change == 'hash':
                manifest['strokes']['sha256'] = '0' * 64
            elif change == 'schema':
                manifest['schema'] = 'unknown'
            elif change == 'verdict':
                del manifest['verdict_metadata']['scientific_verdict']
            else:
                del manifest['strokes']
            path = self.folder / f'bad_{change}.json'
            path.write_text(json.dumps(manifest))
            with self.subTest(change=change), self.assertRaises(ValueError):
                cli.read_asset(path)

    def test_invalid_width_and_unauthorized_output_fail_before_loading(self):
        for width in ('0', '-1', 'nan', 'inf', '65'):
            args = self.arguments('--width', width)
            with self.subTest(width=width), mock.patch.object(cli, 'load_asset') as load:
                with self.assertRaises(ValueError):
                    cli.preflight(args)
                load.assert_not_called()
                self.assertFalse(args.output.exists())
        for output in (cli.UNIT, cli.UNIT.parent / 'unit_004' / 'forbidden', self.folder):
            args = self.arguments('--output', str(output))
            with self.subTest(output=str(output)), mock.patch.object(cli, 'load_asset') as load:
                with self.assertRaises((ValueError, FileExistsError)):
                    cli.preflight(args)
                load.assert_not_called()

    def test_actual_preview_paths_and_only_target_config_change(self):
        with mock.patch.object(cli, 'render', side_effect=AssertionError('tests must not render')):
            manifest, paths, mesh, strokes, config = cli.load_asset(self.asset)
            old = copy.deepcopy(config)
            edited = cli.apply_width_edit(config, 1, 1.5)
        self.assertEqual(len(strokes), 418)
        self.assertEqual({p: sum(s['part'] == p for s in strokes) for p in (1, 2, 3)},
                         {1: 260, 2: 8, 3: 150})
        self.assertEqual(paths['strokes'], Path(self.manifest['strokes']['path']))
        self.assertEqual(config, old)
        self.assertEqual(edited['widths_by_part'], {'1': 1.5, '2': 1., '3': 1.})
        edited['widths_by_part']['1'] = 1.
        self.assertEqual(edited, config)
        self.assertEqual(manifest['verdict_metadata'], self.manifest['verdict_metadata'])
        self.assertEqual(manifest['verdict_metadata']['claim_status']['frozen_density_contract'], 'NO_GO')

    def test_relative_inputs_and_replay_use_explicit_bundle(self):
        relative = copy.deepcopy(self.manifest)
        # These symlinks are test inputs inside the authorized unit; all targets
        # remain historical read-only inputs. No copies or producer calls occur.
        for key in ('mesh', 'strokes', 'config'):
            link = self.folder / f'input_{key}'
            if not link.exists():
                link.symlink_to(self.manifest[key]['path'])
            relative[key]['path'] = link.name
        path = self.folder / 'relative.json'
        path.write_text(json.dumps(relative))
        self.assertEqual(cli.read_asset(path)[1], cli.read_asset(self.asset)[1])
        args = cli.parser().parse_args(['replay', '--bundle', str(self.folder),
                                      '--output', str(self.folder / 'replay')])
        with mock.patch.object(cli, 'load_asset', return_value=(None, None, None, [], {})) as load:
            cli.preflight(args)
        load.assert_called_once_with(self.folder / 'asset.json')


if __name__ == '__main__':
    unittest.main(verbosity=2)
