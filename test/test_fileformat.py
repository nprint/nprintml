import unittest

import pandas as pd

from nprintml.util import format_handlers

from .base import mktestdir


class TestFileFormat(unittest.TestCase):

    def test_io(self):
        for write_format in (
            'csv.gz',
            'feather.zstd',
            'parquet.snappy',
        ):
            with self.subTest(write_format=write_format), \
                 mktestdir() as tempdir:

                features = pd.DataFrame(
                    {
                        'colA': [0] * 4,
                        'colB': [1] * 4,
                        'colC': [0] * 4,
                    },
                    index=['a', 'a', 'b', 'c'],
                )

                writer = format_handlers.get_writer(write_format)
                outpath = writer(features, tempdir)

                reader = format_handlers.get_reader(outpath)
                result = reader(outpath)

                pd.testing.assert_frame_equal(
                    result,
                    features,
                    check_exact=True,   # values should be identical
                    check_names=False,  # don't worry about the index "name"
                )
