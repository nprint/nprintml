"""Pipeline Step to aggregate nPrint data under labels appropriate for
machine learning: Label

"""
import argparse
import textwrap
import typing

import pandas as pd

from nprintml import pipeline
from nprintml.util import HelpAction

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
    __provides__ = LabelResult
    __requires__ = ('nprint_path',)

    def __init__(self, parser):
        group_parser = parser.add_argument_group(
            "aggregation of data under supplied labels",
        )

        group_parser.add_argument(
            '-L', '--label-file', '--label_file',
            metavar='FILE',
            required=True,
            type=argparse.FileType('r'),
            help="label file (CSV)",
        )
        group_parser.add_argument(
            '-a', '--aggregator',
            choices=aggregators,
            required=True,
            help="label aggregation method",
        )
        group_parser.add_argument(
            '--help-aggregator',
            action=HelpAction,
            help_action=print_aggregators,
            help="describe aggregators and exit",
        )
        group_parser.add_argument(
            '--sample-size', '--sample_size',
            metavar='INTEGER',
            type=int,
            default=1,
        )
        group_parser.add_argument(
            '--compress',
            action='store_true',
            help="drop columns which do not appear to provide any predictive signal",
        )
        group_parser.add_argument(
            '--no-write-features',
            action='store_false',
            default=True,
            dest='write_features',
            help="disable writing of features to disk (enabled by default for inspection & reuse)",
        )

    def __call__(self, args, results):
        aggregator_class = aggregators[args.aggregator]
        aggregator = aggregator_class(results.nprint_path, args.label_file)
        features = aggregator(compress=args.compress, sample_size=args.sample_size)

        if args.write_features:
            outdir = args.outdir / 'feature'
            outdir.mkdir()

            features.to_csv(outdir / 'features.csv.gz')

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
