"""Pipeline Step to extract networking traffic via nPrint: Net"""
import argparse
import collections
import itertools
import os
import pathlib
import re
import sys
import textwrap
import time
import typing

import nprintml
from nprintml import pipeline
from nprintml.util import HelpAction

from .execute import CommandError, nprint, nPrintProcess


class NetResult(typing.NamedTuple):
    """Pipeline Step results for Net"""
    nprint_path: pathlib.Path


class Net(pipeline.Step):
    """Extend given `ArgumentParser` with nPrint interface and invoke
    `nprint` command to initiate nprintML pipeline.

    Returns a `NetResult`.

    """
    __provides__ = NetResult
    __requires__ = ('labels',)

    def __init__(self, parser):
        self.args = None

        self.group_parser = parser.add_argument_group(
            "extraction of features from network traffic via nPrint",

            "(full information can be found at https://nprint.github.io/nprint/)"
        )

        self.group_parser.add_argument(
            '-4', '--ipv4',
            action='store_true',
            help="include ipv4 headers",
        )
        self.group_parser.add_argument(
            '-6', '--ipv6',
            action='store_true',
            help="include ipv6 headers",
        )
        self.group_parser.add_argument(
            '-A', '--absolute-timestamps', '--absolute_timestamps',
            action='store_true',
            help="include absolute timestamp field",
        )
        self.group_parser.add_argument(
            '-c', '--count',
            metavar='INTEGER',
            type=int,
            help="number of packets to parse (if not all)",
        )
        self.group_parser.add_argument(
            '-C', '--csv-file', '--csv_file',
            type=FileAccessType(os.R_OK),
            metavar='FILE',
            help="csv (hex packets) infile",
        )
        self.group_parser.add_argument(
            '-d', '--device',
            help="device to capture from if live capture",
        )
        self.group_parser.add_argument(
            '-e', '--eth',
            action='store_true',
            help="include eth headers",
        )
        self.group_parser.add_argument(
            '-f', '--filter',
            help="filter for libpcap",
        )
        self.group_parser.add_argument(
            '-i', '--icmp',
            action='store_true',
            help="include icmp headers",
        )
        self.group_parser.add_argument(
            '-I', '--ip-file', '--ip_file',
            metavar='FILE',
            type=FileAccessType(os.R_OK),
            help="file of IP addresses to filter with (1 per line), "
                 "can be combined with num_packets for num_packets per ip",
        )
        self.group_parser.add_argument(
            '-N', '--nprint-file', '--nPrint_file',
            metavar='FILE',
            type=FileAccessType(os.R_OK),
            help="nPrint infile",
        )
        self.group_parser.add_argument(
            '-O', '--write-index', '--write_index',
            choices=range(5),
            metavar='INTEGER',
            type=int,
            help=textwrap.dedent("""\
                output file index (first column)
                select from:
                    0: source IP (default)
                    1: destination IP
                    2: source port
                    3: destination port
                    4: flow (5-tuple)"""),
        )
        self.group_parser.add_argument(
            '-p', '--payload',
            metavar='INTEGER',
            type=int,
            help="include n bytes of payload",
        )
        self.group_parser.add_argument(
            '-P', '--pcap-file', '--pcap_file',
            default=(),
            metavar='FILE',
            nargs='*',
            type=FileAccessType(os.R_OK),
            help="pcap infile",
        )
        self.group_parser.add_argument(
            '--pcap-dir', '--pcap_dir',
            default=(),
            metavar='DIR',
            nargs='*',
            type=DirectoryAccessType(ext='.pcap'),
            help="directory containing pcap infile(s) with file extension '.pcap'",
        )
        self.group_parser.add_argument(
            '-R', '--relative-timestamps', '--relative_timestamps',
            action='store_true',
            help="include relative timestamp field",
        )
        self.group_parser.add_argument(
            '-t', '--tcp',
            action='store_true',
            help="include tcp headers",
        )
        self.group_parser.add_argument(
            '-u', '--udp',
            action='store_true',
            help="include udp headers",
        )
        self.group_parser.add_argument(
            '-x', '--nprint-filter', '--nprint_filter',
            metavar='STRING',
            help="regex to filter bits out of nPrint output "
                 "(for details see --help-nprint-filter)",
        )
        self.group_parser.add_argument(
            '--help-nprint-filter', '--nprint-filter-help', '--nprint_filter_help',
            action=HelpAction,
            help_action=lambda *_parser_args: nprint('--nprint_filter_help'),
            help="describe regex possibilities and exit",
        )

    def get_output_directory(self):
        return self.args.outdir / 'nprint'

    def make_output_directory(self):
        outdir = self.get_output_directory()
        outdir.mkdir()
        return outdir

    @staticmethod
    def make_output_path(outdir, pcap_output):
        npt_path = (outdir / pcap_output).with_suffix('.npt')

        if npt_path.exists():
            raise FileExistsError(None, 'nPrint output path collision', str(npt_path))

        npt_path.parent.mkdir(parents=True, exist_ok=True)
        return npt_path

    def generate_files(self):
        if self.args.pcap_file or self.args.pcap_dir:
            # stream pair of pcap path & "basis" for reconstructing tree
            for pcap_file in self.args.pcap_file:
                yield (pathlib.Path(pcap_file), None)

            for pcap_dir in self.args.pcap_dir:
                for pcap_file in pcap_dir.rglob('*.pcap'):
                    yield (pcap_file, pcap_dir)

            return

        yield (None, None)

    def generate_argv(self, pcap_file=None, npt_file=None):
        """Construct arguments for `nprint` command."""
        # generate shared/global arguments
        if self.args.verbosity >= 3:
            yield '--verbose'

        # support arbitrary pcap infile(s)
        if pcap_file:
            yield from ('--pcap_file', pcap_file)

        # add group (nPrint-specific) arguments
        for action in self.group_parser._group_actions:
            if action.dest in ('pcap_file', 'pcap_dir'):
                continue

            try:
                value = getattr(self.args, action.dest)
            except AttributeError:
                if action.default == argparse.SUPPRESS:
                    continue

                raise

            key = action.option_strings[-1]

            if value is not action.default:
                yield key

                if not isinstance(value, bool):
                    yield str(value)

        # add output path
        outdir = self.get_output_directory()
        outpath = npt_file or outdir / 'netcap.npt'
        yield from ('--write_file', str(outpath))

    def output_nprint_config(self):
        args = ' '.join(list(self.generate_argv())[:-2])
        nprint_cmd = f'nprint {args} -P [input_pcap]\n'
        outfile = self.args.outdir / 'nprint.cfg'
        with open(outfile, 'w') as f:
            f.write(nprint_cmd)

    def filter_files(self, pcap_files, outdir, labels=None):
        skipped_files = collections.deque(maxlen=4)
        skipped_count = 0

        for (pcap_file, dir_basis) in pcap_files:
            if pcap_file:
                pcap_output = pcap_file.relative_to(dir_basis) if dir_basis else pcap_file.name

                if labels is not None and str(pcap_output) not in labels.index:
                    skipped_files.append(pcap_output)
                    skipped_count += 1
                    continue

                npt_file = self.make_output_path(outdir, pcap_output)

                yield (pcap_file, npt_file)
            else:
                yield (None, None)

        if skipped_count > 0 and self.args.verbosity >= 1:
            print('Skipped', skipped_count, 'PCAP file(s) missing from labels file:')

            for skipped_file in skipped_files:
                print(f'\t{skipped_file}')

            if skipped_count > len(skipped_files):
                print('\t...')

    def generate_procs(self, file_stream):
        for (pcap_file, npt_file) in file_stream:
            yield nPrintProcess(
                *self.generate_argv(pcap_file, npt_file),
            )

    @staticmethod
    def pool_procs(proc_stream, size, wait=None):
        sleep_time = os.sched_rr_get_interval(0) if wait is None else wait / 1_000

        pool = list(itertools.islice(proc_stream, size))

        while any(pool):
            if sleep_time != 0:
                time.sleep(sleep_time)

            for (index, proc) in enumerate(pool):
                if proc and proc.poll() is not None:
                    if proc.returncode != 0:
                        raise CommandError

                    pool[index] = next(proc_stream, None)

    def __pre__(self, parser, args, results):
        try:
            warn_version_mismatch()
        except nprint.NoCommand:
            parser.error("nprint command could not be found on PATH "
                         "(to install see nprint-install)")

        self.args = args

    def __call__(self, args, results):
        self.output_nprint_config()

        outdir = self.make_output_directory()
        
        pcap_files = self.generate_files()

        file_stream = self.filter_files(pcap_files, outdir, results.labels)

        processes = self.generate_procs(file_stream)

        self.pool_procs(processes, size=args.concurrency)

        return NetResult(outdir)


def warn_version_mismatch():
    """Warn if nPrint intended version doesn't match what's on PATH."""
    version_result = nprint('--version', stdout=nprint.PIPE)
    version_output = version_result.stdout.decode()
    version_match = re.match(r'nprint ([.\d]+)', version_output)
    if version_match:
        version_installed = version_match.group(1)
        if version_installed != nprintml.__nprint_version__:
            command_path = version_result.args[0]
            print(
                "[warn]",
                f"nprint expected version for nprintML ({nprintml.__nprint_version__}) "
                f"does not match version on PATH ({version_installed} at {command_path})",
                file=sys.stderr,
            )
    else:
        print(
            "[warn]",
            f"failed to parse version of nprint installed ({version_output})",
            file=sys.stderr,
        )


class FileAccessType:
    """Argument type to test a supplied filesystem path for specified
    access.

    Access level is indicated by bit mask.

    `argparse.FileType` may be preferred when the path should be opened
    in-process. `FileAccessType` allows for greater flexibility -- such
    as passing the path on to a subprocess -- while still validating
    access to the path upfront.

    """
    modes = {
        os.X_OK: 'execute',
        os.W_OK: 'write',
        os.R_OK: 'read',
        os.R_OK | os.X_OK: 'read-execute',
        os.R_OK | os.W_OK: 'read-write',
        os.R_OK | os.W_OK | os.X_OK: 'read-write-execute',
    }

    def __init__(self, access):
        self.access = access

        if access not in self.modes:
            raise ValueError("bad mask", access)

    @property
    def mode(self):
        return self.modes[self.access]

    def __call__(self, path):
        if os.path.isfile(path) and os.access(path, self.access):
            return path

        raise argparse.ArgumentTypeError(f"can't access '{path}' ({self.mode})")


class DirectoryAccessType:
    """Argument type to test a supplied filesystem directory path."""

    def __init__(self, *, ext='', exists=None, empty=False, non_empty=False):
        if ext:
            non_empty = True

        if non_empty:
            exists = True

        if empty and non_empty:
            raise TypeError("directory cannot be both empty and non-empty")

        self.ext = ext
        self.exists = exists
        self.empty = empty
        self.non_empty = non_empty

    def __call__(self, value):
        path = pathlib.Path(value)

        if self.exists is not None:
            if self.exists:
                if not path.is_dir():
                    raise argparse.ArgumentTypeError(f"no such directory '{value}'")
            else:
                if path.exists():
                    raise argparse.ArgumentTypeError(f"path already exists '{value}'")

                if not os.access(path.parent, os.W_OK):
                    raise argparse.ArgumentTypeError(f"path not write-accessible '{value}'")

        if self.empty and any(path.glob('*')):
            raise argparse.ArgumentTypeError(f"directory is not empty '{value}'")

        if self.non_empty:
            count = 0
            for (count, child) in enumerate(path.rglob('*' + self.ext), 1):
                if not os.access(child, os.R_OK):
                    raise argparse.ArgumentTypeError(f"path(s) not read-accessible '{child}'")

            if count == 0:
                raise argparse.ArgumentTypeError("directory has no contents " +
                                                 (f"({self.ext}) " if self.ext else "") +
                                                 f"'{value}'")

        return path
