import itertools
import pathlib

import numpy as np
import pandas as pd

from nprintml.util import storeresults

from . import LabelAggregator, AggregationLengthError, AggregationPathError


NPT_DTYPE = np.dtype('int8')


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

        # We need every sample size to be the same, so we'll find the
        # largest nPrint in all of the files and pad each sample with
        # empty nPrints.
        header = usecols = None
        max_length = file_count = 0

        for (file_count, (file_index, npt_file)) in enumerate(indexed_files, 1):
            if header is None:
                header = np.genfromtxt(npt_file, delimiter=',', max_rows=1, dtype=str)
                usecols = np.arange(1, len(header))  # ignore data index (src_ip)
                skip_header = 1 if isinstance(npt_file, (str, pathlib.Path)) else 0
            else:
                skip_header = 1

            npt = np.genfromtxt(
                npt_file,
                delimiter=',',
                skip_header=skip_header,
                usecols=usecols,
                dtype=NPT_DTYPE,
            )

            npt_dim1 = len(npt.shape) == 1
            npt_length = 1 if npt_dim1 else len(npt)
            max_length = max(max_length, npt_length)

            npt_flat = npt if npt_dim1 else npt.ravel()

            yield list(itertools.chain([file_index], npt_flat))

        print('Loaded', file_count, 'nprints')

        return (header[1:], max_length)

    @classmethod
    def merge_npt(cls, npts_flat):
        """Merge nPrint data from multiple output files."""
        npts = pd.DataFrame(npts_flat, dtype=NPT_DTYPE)

        # true index is generated from input; rather than iterate
        # multiple times, it's initially treated as data.
        # now we can move it in place:
        npts.set_index(0, inplace=True)

        # npt lengths are unknown ahead of time; and, with flatten(), each becomes a row length.
        # luckily, we need not make them equal first -- pandas fills in na or None.
        # constructor doesn't allow specification of this missing sentinel;
        # here we set it:
        npts.fillna(-1, inplace=True)

        # though column names might not be TOO important they may be helpful.
        # here we flatten these as well from the maximum size we might require:
        (header, max_length) = npts_flat.result
        if header is not None:
            npts.columns = cls.flatten_columns(header, max_length)

        print('nPrints padded to maximum size:', max_length)
        print('nPrint features shape:', npts.shape)

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
