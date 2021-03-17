import pathlib

import pandas as pd

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

    def __init__(self, label_csv):
        super().__init__(label_csv)
        self.labels = self.load_label(label_csv)

    def __call__(self, npt_csv, path_input_base=None, compress=False, sample_size=1):
        """Enumerate given stream or directory of nPrint data, load,
        pad to their maximum size, and attach labels.

        `npt_csv` may specify either a path to a directory of nPrint
        results (`str` or `pathlib.Path`) OR a stream of open file-like
        objects (exposing both `read()` and `name`).

        `path_input_base` is recommended when `npt_csv` specifies a
        stream of file objects, to indicate their common base path (even
        if this is virtual), such that they may be matched with the
        label index.

        """
        indexed_files = self.normalize_npt(npt_csv, path_input_base)

        npts = self.merge_npt(indexed_files)

        if compress:
            print('Compressing nPrint')
            npts = self.compress_npt(npts)
            print('  compressed nPrint shape:', npts.shape)

        print('Attaching labels to nPrints')
        labels = self.prejoin_label()

        (npt_df, missing_labels, ogns, nns) = self.attach_label(npts, labels)

        print('  labels attached: missing labels for:', missing_labels)
        print('    missing labels caused samples to be dropped:', (ogns - nns))

        return npt_df

    def prejoin_label(self):
        # Enable join on file path index with .npt-derived data --
        # strip any file suffix like .pcap
        index = self.labels.index.str.replace(r'\.pcap$', '', case=False)
        return self.labels.set_axis(index)

    def merge_npt(self, indexed_files):
        """Merge nPrint data from multiple output files."""
        print('Loading nPrints')

        npts0 = []
        npt_paths = []
        largest_npt = None
        file_count = 0

        for (file_count, (index, npt_file)) in enumerate(indexed_files, 1):
            npt = self.load_npt(npt_file)

            if largest_npt is None or npt.shape[0] > largest_npt.shape[0]:
                largest_npt = npt

            npts0.append(npt)
            npt_paths.append(index)

        print('Loaded', file_count, 'nprints')

        # We need every sample size to be the same, so we find the
        # largest nPrint in all of the files and pad each sample with
        # empty nPrints.

        row_len = npts0[0].shape[1] if npts0 else 0
        fill_row = [-1] * row_len

        npts1 = []

        for npt in npts0:
            for index in range(npt.shape[0], largest_npt.shape[0]):
                npt.loc[index] = fill_row
            npt_flat = npt.to_numpy().flatten()
            npts1.append(npt_flat)

        if largest_npt is None:
            cols_flat = ()
        else:
            cols_flat = self.flatten_columns(largest_npt.columns, largest_npt.shape[0])

        npts = pd.DataFrame(npts1, index=npt_paths, columns=cols_flat)

        print('nPrints padded to maximum size:',
              largest_npt if largest_npt is None else largest_npt.shape[0])
        print('nPrint shape:', npts.shape)

        return npts
