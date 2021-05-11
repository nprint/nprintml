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


PROGRAM_DESCRIPTION = """\
train models for network traffic analysis

executes a pipeline to:

  1. extract network traffic data via nPrint
  2. aggregate these data under supplied labels
  3. generate models of these labeled data via AutoGluon (AutoML)

general (optional) arguments and arguments specific to the above steps of the pipline follow below.

to execute only one portion of the pipeline -- (e.g. to run only the AutoML step given previously-\
saved or separately-prepared feature data) -- see the "subcommands" which follow (namely "learn").
"""


def execute(argv=None, **parser_kwargs):
    """Execute the nprintml CLI command."""
    args = None

    try:
        parser = build_parser(**parser_kwargs)

        pipeline = Pipeline(parser)

        finalize_parser(parser)

        args = Namespace.build(pipeline)

        parser.parse_args(argv, args)

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
    parser = ArgumentParser(
        description=PROGRAM_DESCRIPTION,
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
             "(defaults to number reported by scheduler: %(default)s)",
    )

    parser.add_argument(
        '-o', '--output',
        default=get_default_directory(),
        dest='outdir',
        metavar='DIR',
        type=pathlib.Path,
        help="output directory path to which to write artifacts and results "
             "(default: %(default)s)",
    )

    parser.add_subparsers(
        title="subcommands",
        help="commands customizing pipeline execution",
        action=ExclusiveStepAction,
        dest='subcommand',
        resolver='__pre_satisfy__',
    )

    parser.set_defaults(
        verbosity=1,
        __parser__=parser,
    )

    return parser


def finalize_parser(parser):
    # cosmetic: ensure "subcommands" group listed at end of --help
    #
    # (required to have been defined for extension by pipeline steps;
    # but section makes most sense to be documented at very end).
    #
    action_groups = parser._action_groups
    subcommands_group = action_groups.pop(2)
    assert subcommands_group.title == 'subcommands'
    action_groups.append(subcommands_group)


class ArgumentParser(argparse.ArgumentParser):

    @property
    def subparsers(self):
        actions = self._subparsers._group_actions

        if not actions:
            return None

        (action,) = actions
        return action


class Namespace(argparse.Namespace):

    meta_file_name = 'meta.toml'

    @classmethod
    def build(cls, pipeline):
        return cls(
            __pre_satisfy__=pipeline.pre_satisfy,
        )

    @property
    def meta_file(self):
        return self.outdir / self.meta_file_name


class ExclusiveStepAction(argparse._SubParsersAction):

    def __init__(self,
                 option_strings,
                 prog,
                 parser_class,
                 dest,      # unlike parent 'dest' required
                 resolver,  # added parameter 'resolver'
                 required=False,
                 help=None,
                 metavar=None):
        # "required" added in Py37
        if sys.version_info >= (3, 7):
            super().__init__(option_strings, prog, parser_class, dest, required, help, metavar)
        elif not required:
            super().__init__(option_strings, prog, parser_class, dest, help, metavar)
        else:
            raise TypeError("keyword 'required' not supported prior to Python v3.7")

        self._name_satisfies_map = {}
        self._resolver = resolver

    def add_parser(self, name, *, satisfies=(), **kwargs):
        self._name_satisfies_map[name] = (satisfies,) if isinstance(satisfies, str) else satisfies
        return super().add_parser(name, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        super().__call__(parser, namespace, values, option_string)

        # the user has invoked an "exclusive step" subcommand -- we'll:
        #
        # 1. inform (the pipeline) of the specially-satisfied
        #    requirements associated with this case (s.t. it may update
        #    itself)
        #
        # 2. based on those steps the pipeline reports ejected:
        #
        #    2a. mark the arguments of ejected steps not required
        #    2b. raise conflict errors for *any* of these arguments
        #        that are supplied
        #
        # in so doing we'll both dynamically customize the pipeline and
        # the CLI based on the invocation of this subcommand.

        # argparse keeps nice track of what it's seen and what it hasn't
        # from within _parse_known_args (and which is ostensibly the
        # caller of this method); however, short of reaching into there,
        # we can do s'thing simple & robust here to check for conflicts.
        #
        # when checking for conflicts, argparse itself treats an
        # argument holding its default value as having not been supplied
        # -- even though these situations merely result in equivalent
        # argumentation (i.e. the user may have supplied the argument
        # with its default). nonetheless, we'll do the same.

        subcommand = getattr(namespace, self.dest)
        satisfied = self._name_satisfies_map[subcommand]
        resolver = getattr(namespace, self._resolver)

        for removed_group in resolver(*satisfied):
            actions = removed_group._group_actions if removed_group else ()
            for action in actions:
                if (
                    action.default is not argparse.SUPPRESS and
                    getattr(namespace, action.dest) is not action.default
                ):
                    action_name = argparse._get_action_name(action)
                    raise argparse.ArgumentError(None, f'argument {subcommand}: '
                                                       f'not allowed with argument {action_name}')

                action.required = False


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
