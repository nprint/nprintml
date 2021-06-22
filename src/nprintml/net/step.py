"""Pipeline Step to extract networking traffic via nPrint: Net"""
import argparse
import collections
import concurrent.futures
import itertools
import os
import pathlib
import re
import sys
import textwrap
import typing

import nprintml
from nprintml import pipeline
from nprintml.util import (
    DirectoryAccessType,
    FileAccessType,
    HelpAction,
    NamedBytesIO,
    prime_iterator,
)

from . import execute


NPRINT_QUEUE_MAX = 10 ** 6


class NetResult(typing.NamedTuple):
    """Pipeline Step results for Net"""
    nprint_stream: typing.Generator[NamedBytesIO, None, None]


class Net(pipeline.Step):
    """Extend given `ArgumentParser` with nPrint interface and invoke
    `nprint` command to initiate nprintML pipeline.

    Returns a `NetResult`.

    """
    __provides__ = NetResult
    __requires__ = ('labels',)

    def __init__(self, parser):
        self.args = None  # set by __pre__

        self.group_parser = parser.add_argument_group(
            "extraction of features from network traffic via nPrint",

            "(full information can be found at https://nprint.github.io/nprint/)"
        )

        # record of subset of arguments NOT passed to nprint
        self.own_arguments = set()

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
            choices=range(6),
            metavar='INTEGER',
            type=int,
            help=textwrap.dedent("""\
                output file index (first column)
                select from:
                    0: source IP (default)
                    1: destination IP
                    2: source port
                    3: destination port
                    4: flow (5-tuple)
                    5: wlan tx mac"""),
        )
        self.group_parser.add_argument(
            '-p', '--payload',
            metavar='INTEGER',
            type=int,
            help="include n bytes of payload",
        )
        self.group_parser.add_argument(
            '-P', '--pcap-file', '--pcap_file',
            action='append',
            default=[],
            metavar='FILE',
            type=FileAccessType(os.R_OK),
            help="pcap infile",
        )
        self.own_arguments.add('pcap_file')
        self.group_parser.add_argument(
            '--pcap-dir', '--pcap_dir',
            action='append',
            default=[],
            metavar='DIR',
            type=DirectoryAccessType(ext='.pcap'),
            help="directory containing pcap infile(s) with file extension '.pcap'",
        )
        self.own_arguments.add('pcap_dir')
        self.group_parser.add_argument(
            '-r', '--radiotap',
            action='store_true',
            help="include radiotap headers",
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
            '-w', '--wlan',
            action='store_true',
            help="include wlan headers",
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
            help_action=lambda *_parser_args: execute.nprint('--nprint_filter_help'),
            help="describe regex possibilities and exit",
        )

        self.group_parser.add_argument(
            '--save-nprint',
            action='store_true',
            help="save nPrint output(s) to disk (default: not saved)",
        )
        self.own_arguments.add('save_nprint')

    output_tag = 'nprint'
    default_output_name = 'netcap.npt'

    @property
    def output_directory(self):
        return self.args.outdir / self.output_tag

    def ensure_output_directory(self):
        if self.args.save_nprint:
            self.output_directory.mkdir()

    @classmethod
    def get_output_name(cls, pcap_output):
        if pcap_output is None:
            return cls.default_output_name

        # pcap_output expects str and re is fast
        return cls.get_output_name.pattern.sub('.npt', pcap_output)

    get_output_name.__func__.pattern = re.compile(r'\.pcap$', re.I)

    def make_output_path(self, npt_file):
        npt_path = self.output_directory / npt_file

        if npt_path.exists():
            raise FileExistsError(None, 'nPrint output path collision', str(npt_path))

        npt_path.parent.mkdir(parents=True, exist_ok=True)

        return npt_path

    def generate_pcaps(self):
        if self.args.pcap_file or self.args.pcap_dir:
            # stream pair of pcap path & short ref path for reconstructing tree
            for pcap_file in self.args.pcap_file:
                pcap_path = pathlib.Path(pcap_file)
                yield (pcap_path, pcap_path.name)

            for pcap_dir in self.args.pcap_dir:
                for pcap_path in pcap_dir.rglob('*.pcap'):
                    pcap_file = pcap_path.relative_to(pcap_dir)
                    yield (pcap_path, str(pcap_file))

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
            if action.dest in self.own_arguments:
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
        if npt_file:
            yield from ('--write_file', npt_file)

    def write_meta(self, target):
        args = ' '.join(self.generate_argv('[input_pcap]'))
        target[self.output_tag] = {'cmd': f'nprint {args}'}

    def filtermap_pcaps(self, pcap_files, labels=None):
        skipped_files = collections.deque(maxlen=4)
        skipped_count = 0

        for (pcap_path, pcap_file) in pcap_files:
            if pcap_path:
                if labels is not None and pcap_file not in labels.index:
                    skipped_files.append(pcap_file)
                    skipped_count += 1
                    continue

                npt_file = self.get_output_name(pcap_file)

                yield (pcap_path, npt_file)
            else:
                npt_file = self.get_output_name(None)

                yield (None, npt_file)

        if skipped_count > 0 and self.args.verbosity >= 1:
            print('Skipped', skipped_count, 'PCAP file(s) missing from labels file:')

            for skipped_file in skipped_files:
                print(f'\t{skipped_file}')

            if skipped_count > len(skipped_files):
                print('\t...')

    def execute_nprint(self, pcap_file, npt_file):
        result = execute.nprint(
            *self.generate_argv(pcap_file),
            stdout=execute.nprint.PIPE,
        )

        if self.args.save_nprint:
            out_path = self.make_output_path(npt_file)
            out_path.write_bytes(result.stdout)

        return NamedBytesIO(result.stdout, name=npt_file)

    def generate_npts(self, file_stream, timing):
        # Spawn thread pool of same size as number of concurrent
        # subprocesses we would like to maintain.
        with timing, concurrent.futures.ThreadPoolExecutor(
            max_workers=self.args.concurrency,
            thread_name_prefix=__name__,
        ) as executor:
            # Enqueue/schedule at most NPRINT_QUEUE_MAX nprint calls
            # (not all up front, in case this is VERY large, to spare RAM).
            futures = {
                executor.submit(self.execute_nprint, *args)
                for args in itertools.islice(file_stream, NPRINT_QUEUE_MAX)
            }

            if self.args.verbosity >= 3:
                print('Enqueued', len(futures), 'nPrint task(s)',
                      'to be processed by at most', self.args.concurrency, 'worker(s)')

            all_done = False
            failure_count = 0

            while futures:
                # Wait only long enough for at least one call to complete.
                (completed, futures) = concurrent.futures.wait(
                    futures,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )

                added_count = 0

                for future in completed:
                    # Top off the queue with at most one remaining call
                    # for each completed call.
                    for (added_count, args) in enumerate(itertools.islice(file_stream, 1),
                                                         added_count + 1):
                        futures.add(executor.submit(self.execute_nprint, *args))

                    if not all_done and added_count == 0 and not futures:
                        all_done = True

                        if self.args.verbosity >= 3:
                            print('nPrint tasks complete:', timing.time_elapsed)

                    # Share the result.
                    try:
                        yield future.result()
                    except execute.nprint.CommandError:
                        failure_count += 1

                if added_count and self.args.verbosity >= 3:
                    print('Enqueued', added_count, 'more nPrint task(s)')

            if failure_count > 0:
                print('nPrint task(s) failed:', failure_count)

    def __pre__(self, parser, args, results):
        try:
            warn_version_mismatch()
        except execute.nprint.NoCommand:
            parser.error("nprint command could not be found on PATH "
                         "(to install see nprint-install)")

        self.args = args

    def __call__(self, args, results):
        self.write_meta(results.meta)

        self.ensure_output_directory()

        pcap_files = self.generate_pcaps()

        file_stream = self.filtermap_pcaps(pcap_files, results.labels)

        # Time stream specially as it continues even after step formally completed:
        stream_timing = results.__timing_steps__[self.generate_npts] = pipeline.Timing()

        npt_stream = self.generate_npts(file_stream, stream_timing)

        # Initialize results generator eagerly; (it will handle own buffer):
        active_stream = prime_iterator(npt_stream)

        return NetResult(
            nprint_stream=active_stream,
        )


def warn_version_mismatch():
    """Warn if nPrint intended version doesn't match what's on PATH."""
    version_result = execute.nprint('--version', stdout=execute.nprint.PIPE)
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
