"""nprintML command-line interface entry-point"""
import argparse
import itertools
import multiprocessing
import os
import pathlib
import re
import sys
import time
import toml

import argparse_formatter

import nprintml
from nprintml.pipeline import Pipeline
from nprintml.util import NumericRangeType

# ensure default steps of pipeline auto-load
import nprintml.net.step
import nprintml.label.step
import nprintml.learn.step


ANIMALS = ('aardvark', 'bison', 'canary', 'dalmation', 'emu', 'falcon', 'gnu',
           'hamster', 'impala', 'jellyfish', 'kiwi', 'lemur', 'manatee',
           'nutria', 'okapi', 'porcupine', 'quetzal', 'roadrunner', 'seal',
           'turtle', 'unicorn', 'vole', 'wombat', 'xerus', 'yak', 'zebra')


def execute(argv=None, **parser_kwargs):
    """Execute the nprintml CLI command."""
    args = None

    try:
        parser = build_parser(**parser_kwargs)

        pipeline = Pipeline(parser)

        args = parser.parse_args(argv, Namespace())

        check_output_directory(args)

        for (step, results) in pipeline(parser, args, meta={}):
            print(step, results, sep=' → ')

        with args.meta_file.open('w') as meta_file:
            dump_meta(pipeline.results, meta_file)

        print('done →', pipeline.results)
    except KeyboardInterrupt:
        print('interrupted ✕')
    except Exception as exc:
        if args is not None and args.traceback:
            raise

        print(f'error:{exc_repr(exc)} ✕')
        sys.exit(1)


def build_parser(**parser_kwargs):
    """Construct base parser & arguments for nprintml.

    Link back to parser is set on any resulting parsed argument
    `Namespace` as `__parser__`.

    """
    parser = argparse.ArgumentParser(
        description='train models for network traffic analysis',
        formatter_class=argparse_formatter.FlexiFormatter,
        **parser_kwargs,
    )

    version = f'nprintML {nprintml.__version__} | nPrint {nprintml.__nprint_version__}'
    # support published command aliases
    prog = pathlib.Path(sys.argv[0])
    if prog.name != 'nprintml' and prog.suffix != '.py':
        version = f'%(prog)s {nprintml.__version__} | {version}'

    parser.add_argument(
        '--version',
        action='version',
        help="show program version and exit",
        version=version,
    )

    parser.add_argument(
        '-Q', '--quiet',
        dest='verbosity',
        action='store_const',
        const=0,
        help="minimal output verbosity",
    )
    parser.add_argument(
        '-V', '--verbose',
        dest='verbosity',
        action='store_const',
        const=2,
        help="increased output verbosity",
    )
    parser.add_argument(
        '-VV', '--very-verbose',
        dest='verbosity',
        action='store_const',
        const=3,
        help="high output verbosity (e.g. print human readable packets with nPrints)",
    )
    parser.add_argument(
        '-VVV', '--debug',
        dest='verbosity',
        action='store_const',
        const=4,
        help="highest output verbosity",
    )

    parser.add_argument(
        '--tb', '--traceback',
        action='store_true',
        dest='traceback',
        help="print exception tracebacks",
    )

    try:
        # glibc-only
        sched_getaffinity = os.sched_getaffinity
    except AttributeError:
        # Note: this *may* be inaccurate in some shared environs
        cpu_available_count = multiprocessing.cpu_count()
    else:
        cpu_available_count = len(sched_getaffinity(0))

    parser.add_argument(
        '--concurrency',
        default=cpu_available_count,
        metavar='INTEGER',
        type=NumericRangeType(int, (0, None)),
        help="maximum number of concurrent processes to apply to data preparation "
             f"(defaults to number reported by scheduler: {cpu_available_count})",
    )

    output_default = get_default_directory()
    parser.add_argument(
        '-o', '--output',
        default=output_default,
        dest='outdir',
        metavar='DIR',
        type=pathlib.Path,
        help="output directory path to which to write artifacts and results "
             f"(default: {output_default})",
    )

    parser.set_defaults(
        verbosity=1,
        __parser__=parser,
    )

    return parser


class Namespace(argparse.Namespace):

    meta_file_name = 'meta.toml'

    @property
    def meta_file(self):
        return self.outdir / self.meta_file_name


def exc_repr(exc):
    """Construct representation of given exception appropriate for
    printed output.

    """
    exc_repr = ''

    if exc.__class__.__module__ != 'builtins':
        exc_repr += f'{exc.__class__.__module__}.'

    exc_repr += exc.__class__.__name__

    if exc.args:
        exc_repr += ': ' + ', '.join(map(str, exc.args))

    return exc_repr


def pairwise(iterable):
    """s -> (s0, s1), (s1, s2), (s2, s3), ..., (sn, None)"""
    (a, b) = itertools.tee(iterable)
    next(b, None)
    return itertools.zip_longest(a, b)


def get_default_directory(base_name='nprintml', words=ANIMALS):
    """Construct user-friendly default output directory path."""
    path = pathlib.Path(base_name)

    if path.exists():
        word_options = '|'.join(words)
        run_pattern = re.compile(rf'run-({word_options})-', re.I)
        run_matches = (run_pattern.match(run_path.name) for run_path in path.glob('run-*'))
        words_used = sorted(
            (run_match.group(1).lower() for run_match in run_matches if run_match),
            reverse=True,
        )

        if words_used:
            last_word = words_used[0]
            for (word0, word1) in pairwise(words):
                if word0 == last_word:
                    next_word = word1 or words[0]
                    break
        else:
            next_word = words[0]
    else:
        next_word = words[0]

    return path / f'run-{next_word}-{int(time.time())}-{os.getpid()}'


def check_output_directory(args):
    """Ensure output directory exists and is empty."""
    if args.outdir.exists():
        if args.outdir.is_dir():
            if any(args.outdir.iterdir()):
                args.__parser__.error(f'output directory non-empty: {args.outdir}')
        else:
            args.__parser__.error(f'output path exists and is not a directory: {args.outdir}')
    else:
        args.outdir.mkdir(parents=True)


def dump_meta(results, meta_file):
    step_timing = (
        (step.__name__, tuple(timing))
        for (step, timing) in results.__timing_steps__.items()
    )
    meta_timing = dict(step_timing, total=tuple(results.__timing__))

    meta = dict(results.meta, timing=meta_timing)

    toml.dump(meta, meta_file)
