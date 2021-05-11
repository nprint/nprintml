import pathlib
import toml

from .base import CLITestCase, TEST_DATA, mktestdir


class TestOnlyLearn(CLITestCase):

    def test_flag_conflict(self):
        """conflict error (but not requirement error)"""
        for conflict_flag in (
            # some labeling flags
            ('--aggregator', 'index'),
            ('--compress',),
            # some net flags
            ('--label-file', TEST_DATA / 'single-pcap' / 'labels.txt'),
            ('--pcap-file', TEST_DATA / 'single-pcap' / 'test.pcap'),
            ('--save-nprint',),
            # some nprint-proxy flags
            ('--write-index', '1'),
            ('--write_index', '1'),
        ):
            with self.subTest(conflict_flag=conflict_flag), \
                 self.assertRaisesRegex(self.CommandError,
                                        "error: argument learn: not allowed "
                                        f"with argument [^ ]*{conflict_flag[0]}"), \
                 mktestdir() as tempdir:

                self.try_execute(
                    '--output', tempdir,
                    '--quiet',  # autogluon's threading makes capturing/suppressing
                                # its stdout a little harder

                    *conflict_flag,

                    'learn',
                    TEST_DATA / 'single-pcap' / 'features.csv.gz',

                    stderr=True,
                )

    def test_learn(self):
        """learn-only from existing features file"""
        for features_file in (
            'features.csv.gz',
            'features.fhr',
            'features.parq',
        ):
            with self.subTest(features_file=features_file), \
                 mktestdir() as tempdir:

                self.try_execute(
                    '--output', tempdir,
                    '--quiet',  # autogluon's threading makes capturing/suppressing
                                # its stdout a little harder
                    'learn',
                    TEST_DATA / 'single-pcap' / features_file,
                )

                temp_path = pathlib.Path(tempdir)

                npt_dir = temp_path / 'nprint'
                self.assertFalse(npt_dir.exists())

                feature_path = temp_path / 'feature'
                self.assertFalse(feature_path.exists())

                graphs_path = temp_path / 'model' / 'graphs'
                self.assertTrue(any(graphs_path.glob('*.pdf')))

                models_path = temp_path / 'model' / 'models'
                self.assertTrue(any(models_path.rglob('*.pkl')))

                meta_path = temp_path / 'meta.toml'
                self.assertTrue(meta_path.exists())

                timing = toml.load(meta_path).get('timing', {})
                self.assertSetEqual(set(timing), {'learn', 'total'})
