import itertools
import pathlib

import numpy as np
import pandas as pd

from nprintml.util import prime_iterator, storeresults

from . import LabelAggregator, AggregationLengthError, AggregationPathError


class PcapLabelAggregator(LabelAggregator):
    """A LabelAggregator that takes a directory of nPrint output files
    and considers each file a single sample, padding to the maximum
    size, to run autoML on the generated samples.

    """
    @classmethod
    def normalize_npt(cls, npt_csv, path_input_base=None):
        if isinstance(npt_csv, str):
            yield from cls.normalize_npt(pathlib.Path(npt_csv))
            return

        if isinstance(npt_csv, pathlib.Path):
            base_path = path_input_base or npt_csv
            file_count = 0
            for (file_count, npt_file) in enumerate(npt_csv.rglob('*'), 1):
                if npt_file.is_file():
                    index = str(npt_file.relative_to(base_path).with_suffix(''))
                    yield (index, npt_file)

            if file_count == 0:
                raise AggregationPathError(
                    f"{cls.__name__} requires at least one nPrint "
                    f"data file but directory is empty: '{npt_csv}'"
                )

            return

        # treat as file object stream
        file_count = 0
        for (file_count, npt_file) in enumerate(npt_csv, 1):
            file_path = pathlib.Path(npt_file.name)
            if path_input_base:
                file_path = file_path.relative_to(path_input_base)
            index = str(file_path.with_suffix(''))
            yield (index, npt_file)

        if file_count == 0:
            raise AggregationLengthError(
                f"{cls.__name__} requires at least one nPrint "
                f"data result but stream was empty: {npt_csv}"
            )

    @staticmethod
    @storeresults
    def flatten_npt(indexed_files):
        print('Loading nPrints')

        # Header should be constant across all files so configure based on first.
        #
        # Must establish what the header is (cols_header: to share) and
        # how long it is / its indices (use_cols: internal).
        try:
            indexed_files = prime_iterator(indexed_files)
        except StopIteration:
            # whoops already empty
            cols_header = use_cols = None
        else:
            (_file_index, npt_file) = indexed_files.first

            header = np.genfromtxt(npt_file, delimiter=',', max_rows=1, dtype=str)

            # ignore data index (src_ip)
            cols_header = header[1:]
            use_cols = np.arange(1, len(header))

            # be kind -- rewind (the first file descriptor)
            try:
                file_seek = npt_file.seek
            except AttributeError:
                # might be str, Path or something else we don't understand
                pass
            else:
                file_seek(0)

        # We need every sample size to be the same, so we'll report the
        # length of the largest nPrint in all of the files, such that
        # each sample may be padded with nPrint-appropriate empty values.
        max_length = file_count = 0

        for (file_count, (file_index, npt_file)) in enumerate(indexed_files, 1):
            npt = np.genfromtxt(
                npt_file,
                delimiter=',',
                skip_header=1,
                usecols=use_cols,
                dtype=int,
            )

            npt_dim1 = len(npt.shape) == 1
            npt_length = 1 if npt_dim1 else len(npt)
            max_length = max(max_length, npt_length)

            npt_flat = npt if npt_dim1 else npt.ravel()

            yield list(itertools.chain([file_index], npt_flat))

        print('Loaded', file_count, 'nprints')

        return (cols_header, max_length)

    @classmethod
    def merge_npt(cls, npts_flat):
        """Merge nPrint data from multiple output files."""
        # note: specification of dtype here is ineffective
        npts = pd.DataFrame(npts_flat)

        # true index is generated from input; rather than iterate
        # multiple times, it's initially treated as data.
        # now we can move it in place:
        npts.set_index(0, inplace=True)

        # both columns and indices were ranges and as such the name of the
        # index is currently set to the integer 0.
        # for clarity and compatibility (e.g. with output to Feather) let's
        # give the index its proper name:
        npts.index.name = 'pcap'

        # npt lengths are unknown ahead of time; and, with flatten(), each becomes a row length.
        # luckily, we need not make them equal first -- pandas fills in na or None.
        # constructor doesn't allow specification of this missing sentinel;
        # here we set it:
        npts.fillna(-1, inplace=True)

        # dtype is *mostly* int8 (byte) --
        # *except* might include relative timestamp
        npts = npts.apply(pd.to_numeric, downcast='integer')

        # though column names might not be TOO important they may be helpful.
        # here we flatten these as well from the maximum size we might require:
        (header, max_length) = npts_flat.result
        if header is not None:
            npts.columns = cls.flatten_columns(header, max_length)

        print('nPrints padded to maximum size:', max_length)
        print('nPrint features',
              'shape:', npts.shape,
              'dtypes:', npts.dtypes.unique(),
              'size (mb):', npts.memory_usage(deep=True).sum() / 1024 / 1024)

        return npts

    def __init__(self, label_csv):
        super().__init__(label_csv)
        self.labels = self.load_label(label_csv)

    def __call__(self, npt_csv, compress=False, sample_size=1, path_input_base=None):
        """Enumerate given stream or directory of nPrint data, load,
        pad to their maximum size, and attach labels.

        `npt_csv` may specify either a path to a directory of nPrint
        results (`str` or `pathlib.Path`) OR a stream of open file-like
        objects (exposing both `read()` and `name`).

        `path_input_base` is suggested when `npt_csv` specifies a stream
        of file objects, to indicate their common base path (even if
        this is virtual), such that they may be matched with the label
        index.

        """
        indexed_files = self.normalize_npt(npt_csv, path_input_base)

        npts_flat = self.flatten_npt(indexed_files)

        npt_frame = self.merge_npt(npts_flat)

        if compress:
            print('Compressing nPrint')
            npt_frame = self.compress_npt(npt_frame)
            print('  compressed nPrint shape:', npt_frame.shape)

        print('Attaching labels to nPrints')
        labels = self.prejoin_label()

        (features, missing_labels, ogns, nns) = self.attach_label(npt_frame, labels)

        print('  labels attached: missing labels for:', missing_labels)
        print('    missing labels caused samples to be dropped:', (ogns - nns))

        return features

    def prejoin_label(self):
        # Enable join on file path index with .npt-derived data --
        # strip any file suffix like .pcap
        index = self.labels.index.str.replace(r'\.pcap$', '', case=False)
        return self.labels.set_axis(index)
