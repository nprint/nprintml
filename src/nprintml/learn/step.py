"""Pipeline Step to build models via AutoML: Learn"""
import argparse
import pathlib
import typing

from nprintml import pipeline

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
            default=AutoML.TIME_LIMITS,
            dest='time_limits',
            metavar='INTEGER',
            type=int,
            help="maximum time (seconds) over which to train each model "
                 f"(default: {AutoML.TIME_LIMITS})",
        )
        group_parser.add_argument(
            '--threads',
            dest='n_threads',
            metavar='INTEGER',
            type=NumericRangeType(int, (0, None)),
            help="number of CPU threads to dedicate to training (default: same as --concurrency)",
        )

    def __call__(self, args, results):
        learn = AutoML(results.features, args.outdir / 'model')

        learn(
            test_size=args.test_size,
            eval_metric=args.eval_metric,
            quality=args.quality,
            time_limits=args.time_limits,
            n_threads=(args.n_threads or args.concurrency),
            verbosity=args.verbosity,
        )

        return LearnResult(
            graphs_path=learn.graphs_path,
            models_path=learn.models_path,
        )


class NumericRangeType:
    """Argument type validating that given value is of configured
    numeric type and bounds.

    Bounds may be specified as either `list` or `tuple`, the convention
    indicating whether bounds are "inclusive" or "non-inclusive",
    respectively.

    Either the lower or upper bound may be specified as `None`,
    indicating no bound.

    For example:

        parser.add_argument(
            '--test-size',
            default=0.3,
            metavar='FLOAT',
            type=NumericRangeType(float, (0, 1)),
        )

    The above argument, `--test-size`, will cast its input to `float`,
    (or print an error for non-float input). Moreover, a "not in range"
    error will be printed for inputs equal to zero or equal to or
    greater than one.

        parser.add_argument(
            '--threads',
            default=1,
            metavar='INTEGER',
            type=NumericRangeType(int, (0, None)),
        )

    In the above example, inputs are instead enforced as `int`; and,
    there is _only_ a lower bound -- inputs must only be greater than
    zero.

        parser.add_argument(
            '-q', '--quality',
            default=0,
            metavar='INTEGER',
            type=NumericRangeType(int, [0, 4]),
        )

    Arguments may also be given inclusive bounds, as above -- inputs to
    this example must be greater than or equal to zero, and less than or
    equal to four.

    """
    bounds_message = "upper and lower bounds must be list or tuple of two elements"

    def __init__(self, numeric_type, bounds):
        self.numeric_type = numeric_type

        try:
            (self.lower_bound, self.upper_bound) = bounds
        except ValueError as exc:
            raise ValueError(f"{self.bounds_message} not: {bounds!r}") from exc
        except TypeError as exc:
            raise TypeError(
                f"{self.bounds_message} not {bounds.__class__.__name__}: {bounds!r}"
            ) from exc

        if isinstance(bounds, tuple):
            self.inclusive = False
        elif isinstance(bounds, list):
            self.inclusive = True
        else:
            raise TypeError(f"{self.bounds_message} not {bounds.__class__.__name__}: {bounds!r}")

    def __call__(self, value):
        try:
            number = self.numeric_type(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not {self.numeric_type.__name__}: {value!r}")

        if self.inclusive:
            if (
                (self.lower_bound is not None and number < self.lower_bound) or
                (self.upper_bound is not None and number > self.upper_bound)
            ):
                raise argparse.ArgumentTypeError(
                    f"not in range [{self.lower_bound}, {self.upper_bound}]: {number!r}"
                )
        else:
            if (
                (self.lower_bound is not None and number <= self.lower_bound) or
                (self.upper_bound is not None and number >= self.upper_bound)
            ):
                raise argparse.ArgumentTypeError(
                    f"not in range ({self.lower_bound}, {self.upper_bound}): {number!r}"
                )

        return number
