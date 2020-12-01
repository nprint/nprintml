import pathlib

import pandas as pd

from . import LabelAggregator


class PcapLabelAggregator(LabelAggregator):
    """A LabelAggregator that takes a directory of nPrint output files
    and considers each file a single sample, padding to the maximum
    size, to run autoML on the generated samples.

    """
    def __init__(self, npt_csv, label_csv):
        if isinstance(npt_csv, str):
            npt_csv = pathlib.Path(npt_csv)

        if not isinstance(npt_csv, pathlib.Path):
            raise TypeError(
                f"{self.__class__.__name__} expects a path to a directory of nPrint "
                f"data file(s) not {npt_csv.__class__.__name__}: '{npt_csv}'"
            )

        if not any(npt_csv.iterdir()):
            raise FileNotFoundError(
                f"{self.__class__.__name__} requires at least one nPrint "
                f"data file but directory is empty: '{npt_csv}'"
            )

        super().__init__(npt_csv, label_csv)

    def __call__(self, compress=False, sample_size=1):
        """Enumerate given directory of nPrint data, load, pad to their
        maximum size, and attach labels.

        """
        npts = self.merge_npt()

        if compress:
            print('Compressing nPrint')
            npts = self.compress_npt(npts)
            print('  compressed nPrint shape:', npts.shape)

        print('Attaching labels to nPrints')
        labels = self.load_label(self.label_csv)

        (npt_df, missing_labels, ogns, nns) = self.attach_label(npts, labels)

        print('  labels attached: missing labels for:', missing_labels)
        print('    missing labels caused samples to be dropped:', (ogns - nns))

        return npt_df

    def load_label(self, labels_csv):
        labels = super().load_label(labels_csv)

        # Enable join on file path index with .npt-derived data --
        # strip any file suffix like .pcap (or .npt)
        #
        # (Unlike with former, which strictly loaded .pcap files, mapped these to .npt files, and
        # constructed its index from actual file paths, here we are loading file path values from
        # user-specified CSV data. As such, we won't assume too much about what suffix the user
        # supplied -- if any -- though .pcap is suggested.)
        #
        # Use regular expression rather than path method in case no extension specified, etc.,
        # (as intent is to strip it after all -- extension not meaningful):
        labels.index = labels.index.str.replace(r'\.(pcap|npt)$', '', case=False)

        return labels

    def merge_npt(self):
        """Merge nPrint data from multiple output files."""
        print('Loading nPrints')

        npts0 = []
        npt_paths = []
        largest_npt = None
        file_count = 0
        npt_files = (npt_file for npt_file in self.npt_csv.rglob('*') if npt_file.is_file())

        for (file_count, npt_file) in enumerate(npt_files, 1):
            npt = self.load_npt(npt_file)

            if largest_npt is None or npt.shape[0] > largest_npt.shape[0]:
                largest_npt = npt

            npts0.append(npt)
            npt_paths.append(str(npt_file.relative_to(self.npt_csv).with_suffix('')))

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
