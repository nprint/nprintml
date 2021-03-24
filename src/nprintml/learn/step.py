"""Pipeline Step to build models via AutoML: Learn"""
import pathlib
import typing

from nprintml import pipeline
from nprintml.util import NumericRangeType

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
                 f"(float between zero and one defaulting to {AutoML.TEST_SIZE})",
        )
        group_parser.add_argument(
            '--metric',
            dest='eval_metric',
            default=AutoML.EVAL_METRIC,
            choices=AutoML.EVAL_METRICS_ALL,
            metavar='{...}',
            help=f"metric by which predictions will be evaluated (default: {AutoML.EVAL_METRIC})\n"
                 "select from:\n    " +
                 ', '.join(AutoML.EVAL_METRICS_ALL),
        )
        group_parser.add_argument(
            '-q', '--quality',
            default=AutoML.QUALITY,
            choices=range(len(AutoML.QUALITY_PRESETS)),
            metavar='INTEGER',
            type=int,
            help=f"model fit quality level (default: {AutoML.QUALITY})\n"
                 "select from:\n    " +
                 '\n    '.join(f'{index}: {label}'
                               for (index, label) in enumerate(AutoML.QUALITY_PRESETS)),
        )
        group_parser.add_argument(
            '--limit',
            default=AutoML.TIME_LIMIT,
            dest='time_limit',
            metavar='INTEGER',
            type=int,
            help="maximum time (seconds) over which to train each model "
                 f"(default: {AutoML.TIME_LIMIT})",
        )

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
