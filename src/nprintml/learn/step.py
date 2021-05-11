"""Pipeline Step to build models via AutoML: Learn"""
import os
import pathlib
import typing

import argparse_formatter

from nprintml import pipeline
from nprintml.util import format_handlers, FileAccessType, NumericRangeType

from . import AutoML


class LearnResult(typing.NamedTuple):
    """Pipeline Step results for Learn"""
    graphs_path: pathlib.Path
    models_path: pathlib.Path


class Learn(pipeline.Step):
    """Extend given `ArgumentParser` with the AutoML interface and
    build models from labeled `features`.

    Returns a `LearnResult`.

    """
    __provides__ = LearnResult
    __requires__ = ('features',)

    def __init__(self, parser):
        group_parser = parser.add_argument_group(
            "automl",
        )

        group_parser.add_argument(
            '--test-size', '--test_size',
            default=AutoML.TEST_SIZE,
            metavar='FLOAT',
            type=NumericRangeType(float, (0, 1)),
            help="proportion of data split out for testing "
                 "(float between zero and one defaulting to %(default)s)",
        )
        group_parser.add_argument(
            '--metric',
            dest='eval_metric',
            default=AutoML.EVAL_METRIC,
            choices=AutoML.EVAL_METRICS_ALL,
            metavar='{...}',
            help="metric by which predictions will be evaluated (default: %(default)s)\n"
                 "    select from: %(choices)s",
        )
        group_parser.add_argument(
            '-q', '--quality',
            default=AutoML.QUALITY,
            choices=range(len(AutoML.QUALITY_PRESETS)),
            metavar='INTEGER',
            type=int,
            help="model fit quality level (default: %(default)s)\n"
                 "    select from: " +
                 ', '.join(f'{label} ({index})'
                           for (index, label) in enumerate(AutoML.QUALITY_PRESETS)),
        )
        group_parser.add_argument(
            '--limit',
            default=AutoML.TIME_LIMIT,
            dest='time_limit',
            metavar='INTEGER',
            type=int,
            help="maximum time (seconds) over which to train each model "
                 "(default: %(default)s)",
        )

        # below %(prog)s will refer to subcommand -- not what we want
        base_program = 'python -m nprintml' if parser.prog.endswith('.py') else parser.prog

        learn_only_parser = parser.subparsers.add_parser(
            'learn',
            description="run only the AutoML step given previously-saved or "
                        "separately-prepared feature data\n\n"
                        "arguments related to AutoML are optionally inherited from the base "
                        "command (e.g.: --metric):\n\n"
                        f"    {base_program} --metric=f1 learn ./data/features.fhr",
            formatter_class=argparse_formatter.FlexiFormatter,
            help="run only AutoML",
            satisfies=self.__requires__,
        )
        learn_only_parser.add_argument(
            'features_file',
            metavar='FILE',
            type=FileAccessType(os.R_OK),
            help="path to features",
        )
        learn_only_parser.set_defaults(
            __subparser__=learn_only_parser,
        )

        parser.set_defaults(
            features_file=None,
        )

    def __pre__(self, parser, args, results):
        if args.features_file:
            try:
                reader = format_handlers.get_reader(args.features_file)
            except NotImplementedError:
                subparser = args.__subparser__
                subparser.error(f"unsupported file type: {args.features_file}")

            results.features = reader(args.features_file)

    def __call__(self, args, results):
        learn = AutoML(results.features, args.outdir / 'model')

        learn(
            test_size=args.test_size,
            eval_metric=args.eval_metric,
            quality=args.quality,
            time_limit=args.time_limit,
            verbosity=args.verbosity,
        )

        return LearnResult(
            graphs_path=learn.graphs_path,
            models_path=learn.models_path,
        )
