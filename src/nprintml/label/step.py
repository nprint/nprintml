"""Pipeline Step to aggregate nPrint data under labels appropriate for
machine learning: Label

"""
import argparse
import textwrap
import typing

import pandas as pd

from nprintml import pipeline
from nprintml.util import format_handlers, HelpAction

from .aggregator import registry as aggregators


class LabelResult(typing.NamedTuple):
    """Pipeline Step results for Label"""
    features: pd.DataFrame


class Label(pipeline.Step):
    """Extend given `ArgumentParser` with the label-aggregation
    interface and invoke the requested `LabelAggregator` to extract
    features from nPrint data for the subsequent pipeline step of
    machine learning.

    Returns a `LabelResult`.

    """
    __pre_provides__ = ('labels',)
    __provides__ = LabelResult
    __requires__ = ('nprint_stream',)

    feature_file_formats = (
        'csv', 'csv.gz',
        'parquet.brotli', 'parquet.gzip', 'parquet.snappy',
        'feather.lz4', 'feather.zstd',
    )
    feature_file_formats_default = 'feather.zstd'

    def __init__(self, parser):
        self.group_parser = parser.add_argument_group(
            "aggregation of data under supplied labels",
        )

        self.group_parser.add_argument(
            '-L', '--label-file', '--label_file',
            metavar='FILE',
            required=True,
            type=argparse.FileType('r'),
            help="label file (CSV)",
        )
        self.group_parser.add_argument(
            '-a', '--aggregator',
            choices=aggregators,
            required=True,
            help="label aggregation method",
        )
        self.group_parser.add_argument(
            '--help-aggregator',
            action=HelpAction,
            help_action=print_aggregators,
            help="describe aggregators and exit",
        )
        self.group_parser.add_argument(
            '--sample-size', '--sample_size',
            metavar='INTEGER',
            type=int,
            default=1,
        )
        self.group_parser.add_argument(
            '--compress',
            action='store_true',
            help="drop columns which do not appear to provide any predictive signal",
        )
        self.group_parser.add_argument(
            '--no-save-features',
            action='store_false',
            dest='save_features',
            help="disable writing of features to disk "
                 "(writing enabled by default for inspection & reuse)",
        )
        self.group_parser.add_argument(
            '--save-features-format',
            choices=self.feature_file_formats,
            default=self.feature_file_formats_default,
            help="file format in which to save features on disk (default: %(default)s)",
        )

        self.aggregator = None

    def __pre__(self, parser, args, results):
        aggregator_class = aggregators[args.aggregator]
        self.aggregator = aggregator_class(args.label_file)

        results.labels = self.aggregator.labels

    def __call__(self, args, results):
        features = self.aggregator(
            results.nprint_stream,
            compress=args.compress,
            sample_size=args.sample_size,
        )

        if args.save_features:
            writer = format_handlers.get_writer(args.save_features_format)

            outdir = args.outdir / 'feature'
            outdir.mkdir()

            writer(features, outdir)

        return LabelResult(features)


def print_aggregators(parser, _namespace, _values, _option_string):
    """Document the aggregators by printing their doc strings."""
    print(f"{parser.prog}: labeling data aggregators")

    for (aggregator_name, aggregator_class) in aggregators.items():
        print('\n', aggregator_name, ':', sep='')

        # documentation
        doc = aggregator_class.__doc__ or aggregator_class.__init__.__doc__

        # fix indentation
        #
        # first line may not be indented at all
        if doc[0] in (' ', '\n'):
            doc = textwrap.dedent(doc)
        else:
            line_end = doc.find('\n') + 1
            if line_end > 1:
                doc = doc[:line_end] + textwrap.dedent(doc[line_end:])

        print(textwrap.indent(doc.strip(), '  '))
