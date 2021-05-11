import pathlib
import sys
import toml
from unittest.mock import patch

from .base import CLITestCase, TEST_DATA, mktestdir, testdir


def no_op_call(args, results):
    return None


no_learn_patch = patch('nprintml.learn.step.Learn.__call__', side_effect=no_op_call)


class TestPcap(CLITestCase):

    @testdir
    def test_pcap_file(self, tempdir):
        temp_path = pathlib.Path(tempdir)

        self.try_execute(
            '--tcp',
            '--ipv4',
            '--aggregator', 'index',
            '--label-file', TEST_DATA / 'single-pcap' / 'labels.txt',
            '--pcap-file', TEST_DATA / 'single-pcap' / 'test.pcap',
            '--output', temp_path,
            '--quiet',  # autogluon's threading makes capturing/suppressing
                        # its stdout a little harder
        )

        npt_dir = temp_path / 'nprint'
        self.assertFalse(npt_dir.exists())

        feature_path = temp_path / 'feature' / 'features.fhr'
        self.assertTrue(feature_path.exists())

        graphs_path = temp_path / 'model' / 'graphs'
        self.assertTrue(any(graphs_path.glob('*.pdf')))

        models_path = temp_path / 'model' / 'models'
        self.assertTrue(any(models_path.rglob('*.pkl')))

        meta_path = temp_path / 'meta.toml'
        self.assertTrue(meta_path.exists())
        self.assertEqual(toml.load(meta_path).get('nprint', {}).get('cmd'),
                         'nprint --pcap_file [input_pcap] --ipv4 --tcp')

    def test_pcap_file_write_features_selection(self):
        for output_format in (
            'csv', 'csv.gz',
            'parquet.brotli', 'parquet.gzip', 'parquet.snappy',
            'feather.lz4',
        ):
            with self.subTest(output_format=output_format), \
                 no_learn_patch as no_learn_mock, \
                 mktestdir() as tempdir:

                temp_path = pathlib.Path(tempdir)

                self.try_execute(
                    '--save-features-format', output_format,
                    '--tcp',
                    '--ipv4',
                    '--aggregator', 'index',
                    '--label-file', TEST_DATA / 'single-pcap' / 'labels.txt',
                    '--pcap-file', TEST_DATA / 'single-pcap' / 'test.pcap',
                    '--output', temp_path,
                    '--quiet',  # autogluon's threading makes capturing/suppressing
                                # its stdout a little harder
                )

                npt_dir = temp_path / 'nprint'
                self.assertFalse(npt_dir.exists())

                feature_path = temp_path / 'feature'
                format_id = output_format[0]  # c, p or f
                feature_path_stream = feature_path.glob(f'features.{format_id}*')
                self.assertEqual(sum(1 for file_ in feature_path_stream), 1)

                # note: no model *artifact* assertions -- learn disabled

                no_learn_mock.assert_called_once()
                (learn_call,) = no_learn_mock.mock_calls
                (_args, results) = learn_call.args if sys.version_info >= (3, 8) else learn_call[1]
                self.assertSequenceEqual(results.features.shape, (4921, 961))

                meta_path = temp_path / 'meta.toml'
                self.assertTrue(meta_path.exists())
                self.assertEqual(toml.load(meta_path).get('nprint', {}).get('cmd'),
                                 'nprint --pcap_file [input_pcap] --ipv4 --tcp')

    @testdir
    def test_pcap_file_no_save_features(self, tempdir):
        temp_path = pathlib.Path(tempdir)

        self.try_execute(
            '--no-save-features',
            '--tcp',
            '--ipv4',
            '--aggregator', 'index',
            '--label-file', TEST_DATA / 'single-pcap' / 'labels.txt',
            '--pcap-file', TEST_DATA / 'single-pcap' / 'test.pcap',
            '--output', temp_path,
            '--quiet',  # autogluon's threading makes capturing/suppressing
                        # its stdout a little harder
        )

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
        self.assertEqual(toml.load(meta_path).get('nprint', {}).get('cmd'),
                         'nprint --pcap_file [input_pcap] --ipv4 --tcp')

    @testdir
    def test_pcap_file_save_npt(self, tempdir):
        temp_path = pathlib.Path(tempdir)

        self.try_execute(
            '--save-nprint',
            '--tcp',
            '--ipv4',
            '--aggregator', 'index',
            '--label-file', TEST_DATA / 'single-pcap' / 'labels.txt',
            '--pcap-file', TEST_DATA / 'single-pcap' / 'test.pcap',
            '--output', temp_path,
            '--quiet',  # autogluon's threading makes capturing/suppressing
                        # its stdout a little harder
        )

        npt_path = temp_path / 'nprint' / 'test.npt'
        self.assertTrue(npt_path.exists())

        feature_path = temp_path / 'feature' / 'features.fhr'
        self.assertTrue(feature_path.exists())

        graphs_path = temp_path / 'model' / 'graphs'
        self.assertTrue(any(graphs_path.glob('*.pdf')))

        models_path = temp_path / 'model' / 'models'
        self.assertTrue(any(models_path.rglob('*.pkl')))

        meta_path = temp_path / 'meta.toml'
        self.assertTrue(meta_path.exists())
        self.assertEqual(toml.load(meta_path).get('nprint', {}).get('cmd'),
                         'nprint --pcap_file [input_pcap] --ipv4 --tcp')

    @testdir
    def test_pcap_directory(self, tempdir):
        temp_path = pathlib.Path(tempdir)

        self.try_execute(
            '--tcp',
            '--ipv4',
            '--aggregator', 'pcap',
            '--label-file', TEST_DATA / 'dir-pcap' / 'labels.txt',
            '--pcap-dir', TEST_DATA / 'dir-pcap' / 'pcaps',
            '--output', temp_path,
            '--quiet',  # autogluon's threading makes capturing/suppressing
                        # its stdout a little harder
        )

        npt_dir = temp_path / 'nprint'
        self.assertFalse(npt_dir.exists())

        feature_path = temp_path / 'feature' / 'features.fhr'
        self.assertTrue(feature_path.exists())

        graphs_path = temp_path / 'model' / 'graphs'
        self.assertTrue(any(graphs_path.glob('*.pdf')))

        models_path = temp_path / 'model' / 'models'
        self.assertTrue(any(models_path.rglob('*.pkl')))

        meta_path = temp_path / 'meta.toml'
        self.assertTrue(meta_path.exists())
        self.assertEqual(toml.load(meta_path).get('nprint', {}).get('cmd'),
                         'nprint --pcap_file [input_pcap] --ipv4 --tcp')

    @testdir
    def test_pcap_directory_save_npt(self, tempdir):
        temp_path = pathlib.Path(tempdir)

        self.try_execute(
            '--save-nprint',
            '--tcp',
            '--ipv4',
            '--aggregator', 'pcap',
            '--label-file', TEST_DATA / 'dir-pcap' / 'labels.txt',
            '--pcap-dir', TEST_DATA / 'dir-pcap' / 'pcaps',
            '--output', temp_path,
            '--quiet',  # autogluon's threading makes capturing/suppressing
                        # its stdout a little harder
        )

        npt_path = temp_path / 'nprint'

        npt_path_encrypted = npt_path / 'encrypted'
        npt_path_unencrypted = npt_path / 'unencrypted'
        self.assertTrue(any(npt_path_encrypted.glob('*.npt')))
        self.assertTrue(any(npt_path_unencrypted.glob('*.npt')))

        npt_count = sum(1 for _npt_file in pathlib.Path(npt_path).rglob('*.npt'))
        self.assertEqual(npt_count, 202)

        feature_path = temp_path / 'feature' / 'features.fhr'
        self.assertTrue(feature_path.exists())

        graphs_path = temp_path / 'model' / 'graphs'
        self.assertTrue(any(graphs_path.glob('*.pdf')))

        models_path = temp_path / 'model' / 'models'
        self.assertTrue(any(models_path.rglob('*.pkl')))

        meta_path = temp_path / 'meta.toml'
        self.assertTrue(meta_path.exists())
        self.assertEqual(toml.load(meta_path).get('nprint', {}).get('cmd'),
                         'nprint --pcap_file [input_pcap] --ipv4 --tcp')

    @testdir
    def test_pcap_directory_label_subset(self, tempdir):
        temp_path = pathlib.Path(tempdir)

        self.try_execute(
            '--save-nprint',
            '--tcp',
            '--ipv4',
            '--aggregator', 'pcap',
            '--label-file', TEST_DATA / 'dir-pcap' / 'labels-abridged.txt',
            '--pcap-dir', TEST_DATA / 'dir-pcap' / 'pcaps',
            '--output', temp_path,
            '--quiet',  # autogluon's threading makes capturing/suppressing
                        # its stdout a little harder
        )

        npt_path = temp_path / 'nprint'

        npt_path_encrypted = npt_path / 'encrypted'
        npt_path_unencrypted = npt_path / 'unencrypted'
        self.assertTrue(any(npt_path_encrypted.glob('*.npt')))
        self.assertTrue(any(npt_path_unencrypted.glob('*.npt')))

        npt_count = sum(1 for _npt_file in pathlib.Path(npt_path).rglob('*.npt'))
        self.assertEqual(npt_count, 100)

        feature_path = temp_path / 'feature' / 'features.fhr'
        self.assertTrue(feature_path.exists())

        graphs_path = temp_path / 'model' / 'graphs'
        self.assertTrue(any(graphs_path.glob('*.pdf')))

        models_path = temp_path / 'model' / 'models'
        self.assertTrue(any(models_path.rglob('*.pkl')))

        meta_path = temp_path / 'meta.toml'
        self.assertTrue(meta_path.exists())
        self.assertEqual(toml.load(meta_path).get('nprint', {}).get('cmd'),
                         'nprint --pcap_file [input_pcap] --ipv4 --tcp')
